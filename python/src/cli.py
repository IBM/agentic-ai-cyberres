#!/usr/bin/env python3
#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
BeeAI Interactive Validation CLI

Interactive command-line interface for validating infrastructure resources.
Credentials are loaded from config/secrets.json — no passwords in prompts.

Usage:
    python cli.py

Prompt examples (no credentials needed in prompt):
    "Validate VM at 192.168.1.100"
    "Check Oracle database at db.example.com"
    "Validate MongoDB at mongo-server:27017"
    "Validate VM prod-vm-01"                    # use credential ID
    "Validate VM at 192.168.1.100 and email report to user@example.com"

Credential resolution order:
    1. config/secrets.json  (by credential ID or hostname lookup)
    2. Environment variables (SSH_USER, SSH_PASSWORD, etc.)
    3. Prompt fallback (with security warning)
"""

import asyncio
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# ── Bootstrap logging FIRST, before any other imports ────────────────────────
# This ensures all subsequent imports log to the right place.
sys.path.insert(0, str(Path(__file__).parent))

from agent_logging.agent_logger import setup_logging, AgentTracker, WorkflowProgressDisplay

log_file = setup_logging(
    log_dir="logs",
    log_level="DEBUG",
    console_level="WARNING",  # Only show warnings and errors on console
    log_file_prefix="validation-agent",
    suppress_noisy_loggers=True,
    transform_logs=True,  # Transform technical logs to agent narratives
    agent_name="Agent",
)

import logging
logger = logging.getLogger(__name__)

# ── OpenTelemetry Instrumentation (via dedicated module) ──────────────────────
from agents.telemetry import (
    initialize_telemetry,
    flush_telemetry,
    shutdown_telemetry,
    trace_operation,
    is_telemetry_enabled,
)

telemetry_enabled = os.getenv("ENABLE_TELEMETRY", "true").lower() == "true"
if telemetry_enabled:
    # Phoenix base URL (UI is at this URL)
    phoenix_base = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006")
    # OTLP endpoint must include /v1/traces path
    phoenix_endpoint = phoenix_base.rstrip('/') + '/v1/traces'
    enable_console = os.getenv("TELEMETRY_CONSOLE", "false").lower() == "true"
    
    success = initialize_telemetry(
        service_name="validation-service",
        phoenix_endpoint=phoenix_endpoint,
        enable_console_export=enable_console,
    )
    
    if not success:
        logger.warning(
            "Telemetry initialization failed, continuing without traces",
            extra={"agent": "System"}
        )
else:
    logger.info(
        "Telemetry disabled (set ENABLE_TELEMETRY=true to enable)",
        extra={"agent": "System"}
    )
logger.info(f"BeeAI Interactive CLI starting — log file: {log_file}", extra={"agent": "System"})

# ── Application imports ───────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; env vars may already be set

from agents.orchestrator import ValidationOrchestrator
from models import (
    ValidationRequest,
    ValidationReport,
    VMResourceInfo,
    FleetManifest,
    FleetReport,
    FleetTargetResult,
    FleetTargetStatus,
)
from email_service import EmailService
from credentials import CredentialResolver, CredentialNotFoundError
from fleet_orchestrator import FleetOrchestrator


# ── Fleet Progress Display ────────────────────────────────────────────────────

class FleetProgressDisplay:
    """
    Live per-target status table for fleet validation runs.

    Printed once at the start, then each target row is updated in-place
    using ANSI cursor-up sequences so the table stays on screen.

    Example output::

        ┌─────────────────────────────────────────────────────────────┐
        │  🚀 Fleet: Production Fleet  (4 targets, max_parallel=3)    │
        ├──────────────────────────┬────────────┬───────┬─────────────┤
        │  Target                  │  Status    │ Score │  Time       │
        ├──────────────────────────┼────────────┼───────┼─────────────┤
        │  prod-web-01             │ ✅ done    │  92   │  18.3s      │
        │  prod-db-01              │ 🔄 running │   —   │   —         │
        │  prod-cache-01           │ ⏳ pending │   —   │   —         │
        │  prod-app-01             │ ⏳ pending │   —   │   —         │
        └──────────────────────────┴────────────┴───────┴─────────────┘
    """

    _COL_TARGET = 26
    _COL_STATUS = 12
    _COL_SCORE  = 7
    _COL_TIME   = 10

    def __init__(self, manifest: FleetManifest):
        self._manifest = manifest
        self._results: list[FleetTargetResult] = []
        self._printed = False

    def attach(self, results: list[FleetTargetResult]) -> None:
        """Attach the live results list (mutated by FleetOrchestrator workers)."""
        self._results = results

    def render(self, *, final: bool = False) -> None:
        """Print (or re-print) the status table."""
        W = self._COL_TARGET
        S = self._COL_STATUS
        SC = self._COL_SCORE
        T = self._COL_TIME

        lines: list[str] = []
        name = self._manifest.name
        n = len(self._manifest.enabled_targets)
        mp = self._manifest.max_parallel
        lines.append(f"\n  🚀 Fleet: {name}  ({n} target(s), max_parallel={mp})")
        lines.append(f"  {'─'*W}  {'─'*S}  {'─'*SC}  {'─'*T}")
        lines.append(f"  {'Target':<{W}}  {'Status':<{S}}  {'Score':>{SC}}  {'Time':>{T}}")
        lines.append(f"  {'─'*W}  {'─'*S}  {'─'*SC}  {'─'*T}")

        for r in self._results:
            label = r.target.display_name[:W]
            status_str = r.display_status[:S]
            score_str  = str(r.score) if r.score is not None else "—"
            time_str   = f"{r.execution_time_seconds:.1f}s" if r.execution_time_seconds else "—"
            lines.append(
                f"  {label:<{W}}  {status_str:<{S}}  {score_str:>{SC}}  {time_str:>{T}}"
            )

        lines.append(f"  {'─'*W}  {'─'*S}  {'─'*SC}  {'─'*T}")

        if final:
            done    = sum(1 for r in self._results if r.status == FleetTargetStatus.DONE)
            failed  = sum(1 for r in self._results if r.status == FleetTargetStatus.FAILED)
            skipped = sum(1 for r in self._results if r.status == FleetTargetStatus.SKIPPED)
            scores  = [r.score for r in self._results if r.score is not None]
            avg_str = f"{sum(scores)/len(scores):.0f}/100" if scores else "n/a"
            lines.append(
                f"\n  ✅ {done} passed  ❌ {failed} failed  ⏭  {skipped} skipped  "
                f"avg score {avg_str}"
            )

        print("\n".join(lines))


class InteractiveCLI:
    """
    Interactive CLI for BeeAI validation workflow.

    Key improvements over previous version:
    - Credentials loaded from config/secrets.json (no passwords in prompts)
    - Enhanced logging: agent activity visible on console, full detail in log file
    - Credential ID support: reference credentials by name in prompts
    - Fleet mode: validate multiple VMs/resources in one command
    """

    def __init__(self):
        self.orchestrator: ValidationOrchestrator | None = None
        self.initialized = False
        self.email_service: EmailService | None = None
        self.credential_resolver = CredentialResolver(
            secrets_file="config/secrets.json",
            fallback_to_env=True,
        )
        self.tracker = AgentTracker("Orchestrator")
        self._initialize_email_service()

    def _initialize_email_service(self):
        """Initialize email service from environment variables."""
        smtp_server   = os.getenv("SMTP_SERVER", "smtp.sendgrid.net")
        smtp_port     = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_address  = os.getenv("FROM_EMAIL", "validation@cyberres.com")

        if smtp_username and smtp_password:
            try:
                self.email_service = EmailService(
                    smtp_server=smtp_server,
                    smtp_port=smtp_port,
                    from_address=from_address,
                    smtp_username=smtp_username,
                    smtp_password=smtp_password,
                    use_tls=True,
                )
                logger.info("Email service initialised", extra={"agent": "System"})
            except Exception as e:
                logger.warning(f"Email service init failed: {e}", extra={"agent": "System"})
        else:
            logger.info(
                "Email service not configured (SMTP_USERNAME/SMTP_PASSWORD not set)",
                extra={"agent": "System"},
            )

    async def initialize(self):
        """Initialize the BeeAI orchestrator."""
        if self.initialized:
            return

        print("\n" + "═" * 65)
        print("  🤖  BeeAI Infrastructure Validation Agent")
        print("═" * 65)
        print(f"\n  📝 Logs → {log_file}")
        print(f"  🔑 Credentials → config/secrets.json")
        print()

        self.tracker.start("Initialising BeeAI orchestrator")

        try:
            with self.tracker.phase("initialization", "Loading LLM and MCP tools"):
                self.orchestrator = ValidationOrchestrator(
                    mcp_server_path="../cyberres-mcp",
                    llm_model="ollama:llama3.2",
                    enable_discovery=True,
                    enable_ai_evaluation=True,
                )
                await self.orchestrator.initialize()

            self.initialized = True
            self.tracker.finish("Ready to validate infrastructure")

            # Show available credentials
            available = self.credential_resolver.list_available_credentials()
            if available:
                print(f"\n  🔑 Available credentials ({len(available)}):")
                for cred in available:
                    hosts_str = ", ".join(cred["hosts"][:2])
                    if len(cred["hosts"]) > 2:
                        hosts_str += f" +{len(cred['hosts'])-2} more"
                    print(f"     • {cred['credential_id']} [{cred['type']}] → {hosts_str}")
            else:
                print(
                    "\n  ⚠️  No credentials found in config/secrets.json\n"
                    "     Add your credentials to config/secrets.json\n"
                    "     (see config/secrets.json for the format)"
                )

        except Exception as e:
            self.tracker.error(f"Initialisation failed: {e}", exc=e)
            raise

    # ── Prompt parsing ────────────────────────────────────────────────────────

    def parse_prompt(self, prompt: str) -> tuple:
        """
        Parse natural language prompt into a plain dict of parsed info + email.

        secrets.json only stores SSH credentials (host + username + password).
        The agent discovers everything else (what's running, ports, services).

        Returns:
            (parsed_info dict, email_address or None)
            parsed_info keys: host, credential_id, ssh_port, auto_discover
        """
        # Extract email address (remove it from host/cred parsing)
        email_match = re.search(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', prompt
        )
        email_address = email_match.group(0) if email_match else None

        # Strip email from prompt so it doesn't confuse host extraction
        clean_prompt = re.sub(
            r'\s*(?:and\s+)?(?:email|send)\s+(?:report\s+)?(?:to\s+)?\S+@\S+', '',
            prompt, flags=re.IGNORECASE
        ).strip()

        # Extract host and optional credential ID
        host, credential_id = self._extract_host_and_credential_id(clean_prompt)
        port_match = re.search(r'port\s+(\d+)', clean_prompt, re.IGNORECASE)

        return {
            "host": host or "localhost",
            "credential_id": credential_id,
            "ssh_port": int(port_match.group(1)) if port_match else 22,
            "auto_discover": True,
        }, email_address

    def _extract_host_and_credential_id(self, prompt: str) -> tuple:
        """
        Extract host and optional credential ID from prompt.

        Resolution priority:
        1. If a credential ID is found AND the credential has a specific host
           list, use the credential's first host (the credential is the source
           of truth for which machine to connect to).
        2. If a credential ID is found but has no specific host (wildcard "*"),
           fall back to the IP/hostname in the prompt.
        3. If no credential ID, use the IP/hostname from the prompt.

        Returns:
            (host, credential_id)  — either may be None
        """
        # ── Step 1: Extract credential ID ────────────────────────────────────
        # Patterns handled (in order of specificity):
        #   "use credential vm-prod-01"   → "vm-prod-01"
        #   "use cred vm-prod-01"         → "vm-prod-01"
        #   "credential vm-prod-01"       → "vm-prod-01"
        #   "cred vm-prod-01"             → "vm-prod-01"
        credential_id = None

        # Pattern 1: "use credential <id>" or "use cred <id>"
        m = re.search(
            r'\buse\s+(?:credential|cred)\s+([a-zA-Z0-9_.-]+)',
            prompt, re.IGNORECASE
        )
        if m:
            credential_id = m.group(1)

        # Pattern 2: "credential <id>" or "cred <id>" (without leading "use")
        if not credential_id:
            m = re.search(
                r'\b(?:credential|cred)\s+([a-zA-Z0-9_.-]+)',
                prompt, re.IGNORECASE
            )
            if m:
                credential_id = m.group(1)

        # ── Step 2: If credential ID found, look up its host ─────────────────
        # The credential is the authoritative source for which host to connect
        # to.  If the user also typed an IP in the prompt, we warn about the
        # mismatch but use the credential's host.
        if credential_id:
            available = self.credential_resolver.list_available_credentials()
            for cred in available:
                if cred["credential_id"].lower() == credential_id.lower():
                    hosts = cred.get("hosts", [])
                    cred_host = hosts[0] if hosts and hosts[0] != "*" else None
                    if cred_host:
                        # Check if the user also typed a different IP
                        ip_match = re.search(
                            r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', prompt
                        )
                        if ip_match and ip_match.group(1) != cred_host:
                            logger.warning(
                                f"Prompt contains IP {ip_match.group(1)} but "
                                f"credential '{credential_id}' maps to "
                                f"{cred_host}. Using credential host: {cred_host}"
                            )
                        return cred_host, credential_id
                    # Credential found but no specific host (wildcard) — fall
                    # through to extract host from prompt
                    break

        # ── Step 3: Extract host from prompt (no credential or wildcard) ──────
        # Extract IP address
        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', prompt)
        if ip_match:
            return ip_match.group(1), credential_id

        # Extract hostname after "at" or "host"
        host_match = re.search(r'(?:at|host)\s+([^\s,]+)', prompt, re.IGNORECASE)
        if host_match:
            return host_match.group(1), credential_id

        # Check if a known credential ID is mentioned directly in the prompt
        available = self.credential_resolver.list_available_credentials()
        for cred in available:
            cred_id = cred["credential_id"]
            if cred_id.lower() in prompt.lower():
                hosts = cred.get("hosts", [])
                host = hosts[0] if hosts and hosts[0] != "*" else None
                return host, cred_id

        return None, credential_id

    # ── Credential resolution + model construction ────────────────────────────

    async def _resolve_and_build_request(self, info: dict) -> ValidationRequest:
        """
        Resolve SSH credentials from secrets.json, then build a VMResourceInfo.

        secrets.json only stores SSH access credentials (host + username + password).
        The agent discovers everything else — what's running on the host, which
        ports are open, which services (Oracle, MongoDB, etc.) are present.

        Args:
            info: Plain dict from parse_prompt()

        Returns:
            Fully populated ValidationRequest with VMResourceInfo
        """
        host = info["host"]
        credential_id = info.get("credential_id")

        cred_tracker = AgentTracker("CredentialResolver", resource=host)

        # ── Resolve SSH credentials from secrets.json ─────────────────────────
        creds = {}
        try:
            with cred_tracker.phase("credentials", "Resolving SSH credentials from secrets.json"):
                creds = await self.credential_resolver.resolve(
                    resource_type="vm",   # always SSH-based; agent discovers the rest
                    credential_id=credential_id,
                    hostname=host,
                )
            cred_tracker.decision(
                f"SSH credentials resolved for {host} "
                f"[id={creds.get('credential_id', 'env-fallback')}]"
            )
        except CredentialNotFoundError:
            cred_tracker.warning(
                f"No credentials found for {host}.\n"
                "  Add SSH credentials to config/secrets.json or set SSH_USER/SSH_PASSWORD env vars."
            )
        except Exception as e:
            cred_tracker.error(f"Credential resolution error: {e}", exc=e)

        # ── Extract SSH fields ────────────────────────────────────────────────
        ssh = creds.get("ssh", {})
        ssh_user = ssh.get("username", "")
        ssh_password = ssh.get("password")
        ssh_key_path = ssh.get("key_path")
        ssh_port = ssh.get("port", info.get("ssh_port", 22))

        if not ssh_user:
            raise CredentialNotFoundError(
                f"SSH username not found for {host}. "
                "Add credentials to config/secrets.json:\n"
                f'  "{host}": {{ "ssh": {{ "username": "root", "password": "..." }} }}'
            )

        # ── Build VMResourceInfo — agent discovers what's running ─────────────
        resource = VMResourceInfo(
            host=host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            ssh_port=ssh_port,
        )

        cred_tracker.decision(
            f"Built VMResourceInfo for {host} — agent will discover workloads via SSH"
        )

        return ValidationRequest(
            resource_info=resource,
            auto_discover=info.get("auto_discover", True),
        )

    # ── Validation execution ──────────────────────────────────────────────────

    async def execute_validation(self, prompt: str):
        """
        Execute validation based on user prompt with explicit tracing.

        Args:
            prompt: Natural language validation prompt
        """
        print(f"\n{'─'*65}")
        print(f"  💬 {prompt}")
        print(f"{'─'*65}")

        exec_tracker = AgentTracker("Orchestrator")

        # Main validation workflow span with input/output capture
        with trace_operation(
            "validation_workflow",
            span_kind="INTERNAL",
            input_data={
                "prompt": prompt[:200],  # First 200 chars
                "timestamp": datetime.now().isoformat(),
            },
            attributes={
                "workflow.type": "validation",
                "workflow.version": "1.0",
            }
        ) as workflow_root_span:
            try:
                # Step 1: Parse prompt — extract host and credential ID
                with trace_operation(
                    "parse_prompt",
                    span_kind="INTERNAL",
                    input_data={"prompt": prompt},
                    attributes={"step": "1_parse"}
                ) as parse_span:
                    if parse_span:
                        parse_span.add_event("parsing_started", {"timestamp": datetime.now().isoformat()})
                    
                    exec_tracker.decision("Parsing prompt to identify target host")
                    info, email_address = self.parse_prompt(prompt)
                    
                    # Capture parse output
                    if parse_span:
                        parse_span.add_event("parsing_completed", {
                            "host_found": info['host'],
                            "has_email": bool(email_address)
                        })
                        parse_span.set_attribute("host", info['host'])
                        if info.get("credential_id"):
                            parse_span.set_attribute("credential_id", info.get("credential_id"))
                        if email_address:
                            parse_span.set_attribute("email", email_address)

                print(f"\n  ✅ Understood:")
                print(f"     Target : {info['host']}")
                if info.get("credential_id"):
                    print(f"     Cred ID: {info['credential_id']}")
                if email_address:
                    print(f"     Email  : {email_address}")
                print(f"     Mode   : Agent-driven discovery (SSH → detect workloads)")

                # Step 2: Resolve credentials + build Pydantic model
                with trace_operation(
                    "resolve_credentials",
                    span_kind="INTERNAL",
                    input_data={"host": info['host'], "credential_id": info.get("credential_id")},
                    attributes={"step": "2_credentials"}
                ) as cred_span:
                    if cred_span:
                        cred_span.add_event("credential_resolution_started", {
                            "host": info['host']
                        })
                    
                    request = await self._resolve_and_build_request(info)
                    resource = request.resource_info
                    
                    # Capture credential resolution output
                    if cred_span:
                        # VMResourceInfo has ssh_user, ssh_password, ssh_key_path (not ssh_credentials)
                        has_creds = bool(
                            hasattr(resource, 'ssh_user') and resource.ssh_user and
                            (getattr(resource, 'ssh_password', None) or getattr(resource, 'ssh_key_path', None))
                        )
                        cred_span.add_event("credentials_resolved", {
                            "has_credentials": has_creds,
                            "credential_source": str(request.credential_source)
                        })
                        cred_span.set_attribute("host", resource.host)
                        cred_span.set_attribute("has_credentials", has_creds)

                # Show workflow progress
                progress = WorkflowProgressDisplay(resource.host)
                progress.start_workflow()

                # Execute workflow with explicit phase tracing
                start_time = __import__("time").time()
                progress.update_phase("discovery",  "running", "Scanning workloads...")
                
                if self.orchestrator is None:
                    raise RuntimeError("Orchestrator not initialised")
                
                # Wrap the entire workflow execution with rich input/output
                with trace_operation(
                    "execute_workflow",
                    span_kind="INTERNAL",
                    input_data={
                        "host": resource.host,
                        "auto_discover": request.auto_discover,
                        "credential_source": request.credential_source,
                    },
                    attributes={
                        "step": "3_execute",
                        "resource.type": str(resource.resource_type),
                        "workflow.auto_discover": str(request.auto_discover),
                    }
                ) as workflow_span:
                    if workflow_span:
                        workflow_span.add_event("workflow_execution_started", {
                            "host": resource.host,
                            "auto_discover": request.auto_discover
                        })
                    
                    result = await self.orchestrator.execute_workflow(request)
                    elapsed = __import__("time").time() - start_time
                    
                    # Add workflow results to span with structured output
                    if workflow_span:
                        workflow_span.add_event("workflow_execution_completed", {
                            "status": result.workflow_status,
                            "score": result.validation_result.score,
                            "elapsed_seconds": round(elapsed, 2)
                        })
                        
                        workflow_span.set_attribute("workflow_status", result.workflow_status)
                        workflow_span.set_attribute("score", result.validation_result.score)
                        workflow_span.set_attribute("elapsed_seconds", elapsed)
                        workflow_span.set_attribute("passed_checks", result.validation_result.passed_checks)
                        workflow_span.set_attribute("failed_checks", result.validation_result.failed_checks)
                        workflow_span.set_attribute("warning_checks", result.validation_result.warning_checks)
                        
                        # Add phase completion events
                        for phase, timing in result.phase_timings.items():
                            workflow_span.add_event(f"phase_{phase}_completed", {
                                "duration_seconds": round(timing, 2),
                                "has_errors": phase in result.errors
                            })
                        
                        # Set structured attributes for Phoenix UI
                        workflow_span.set_attribute("workflow_status", result.workflow_status)
                        workflow_span.set_attribute("validation_score", result.validation_result.score)
                        workflow_span.set_attribute("passed_checks", result.validation_result.passed_checks)
                        workflow_span.set_attribute("failed_checks", result.validation_result.failed_checks)
                        workflow_span.set_attribute("warning_checks", result.validation_result.warning_checks)
                        workflow_span.set_attribute("elapsed_seconds", round(elapsed, 2))
                
                # Set final workflow attributes
                if workflow_root_span:
                    workflow_root_span.set_attribute("status", result.workflow_status)
                    workflow_root_span.set_attribute("score", result.validation_result.score)
                    total_checks = (
                        result.validation_result.passed_checks +
                        result.validation_result.failed_checks +
                        result.validation_result.warning_checks
                    )
                    workflow_root_span.set_attribute("total_checks", total_checks)
                    workflow_root_span.set_attribute("elapsed_seconds", round(elapsed, 2))

                # Update progress display
                for phase, timing in result.phase_timings.items():
                    status = "done" if phase not in result.errors else "done"
                    progress.update_phase(phase, status, f"{timing:.1f}s")

                progress.finish_workflow(
                    status=result.workflow_status,
                    score=result.validation_result.score,
                    elapsed=elapsed,
                )

                # Display detailed results
                self._display_results(result)

                # Send email report if requested
                if email_address:
                    with trace_operation(
                        "send_email_report",
                        span_kind="CLIENT",
                        input_data={"email": email_address, "score": result.validation_result.score},
                        attributes={"step": "4_email", "email.recipient": email_address}
                    ) as email_span:
                        await self._send_email_report(result, request, email_address)
                        if email_span:
                            email_span.set_attribute("status", "sent")
                            email_span.set_attribute("recipient", email_address)

                # Flush traces to Phoenix immediately after validation
                if is_telemetry_enabled():
                    logger.debug("Flushing traces to Phoenix...", extra={"agent": "Telemetry"})
                    flush_telemetry(timeout=10)

            except Exception as e:
                exec_tracker.error(f"Validation failed: {e}", exc=e)
                print(f"\n  ❌ Error: {e}")
                logger.error(f"Validation error", exc_info=True, extra={"agent": "Orchestrator"})
                
                # Flush traces even on error
                if is_telemetry_enabled():
                    flush_telemetry(timeout=10)
                
                raise

    def _display_results(self, result):
        """Display validation results in a clean, readable format."""
        vr = result.validation_result

        print(f"\n{'═'*65}")
        print(f"  📊 Validation Results")
        print(f"{'═'*65}")

        # Score bar
        score = vr.score
        bar_len = 30
        filled = int(bar_len * score / 100)
        if score >= 80:
            bar_colour = "\033[32m"   # green
        elif score >= 50:
            bar_colour = "\033[33m"   # yellow
        else:
            bar_colour = "\033[31m"   # red
        reset = "\033[0m"
        bar = f"{bar_colour}{'█' * filled}{'░' * (bar_len - filled)}{reset}"
        print(f"\n  Score  : {bar} {score}/100")
        print(f"  Status : {result.workflow_status.upper()}")
        print(f"  Time   : {result.execution_time_seconds:.2f}s")

        # Check summary
        print(f"\n  Checks :")
        print(f"    ✅ Passed  : {vr.passed_checks}")
        print(f"    ❌ Failed  : {vr.failed_checks}")
        print(f"    ⚠️  Warnings: {vr.warning_checks}")

        # Individual checks
        if vr.checks:
            print(f"\n  Details:")
            for i, check in enumerate(vr.checks, 1):
                icon = {
                    "passed":  "  ✅",
                    "failed":  "  ❌",
                    "warning": "  ⚠️ ",
                    "error":   "  🔴",
                }.get(check.status.value, "  ℹ️ ")

                print(f"{icon} {check.check_name}")
                if check.message:
                    msg = check.message[:120] + "..." if len(check.message) > 120 else check.message
                    print(f"       {msg}")

                # Full details go to log file only
                logger.debug(
                    f"Check {i}: {check.check_name} = {check.status.value}",
                    extra={"agent": "Orchestrator"}
                )
                if check.details:
                    logger.debug(f"  Details: {check.details}", extra={"agent": "Orchestrator"})

        # Discovery summary
        if result.discovery_result:
            dr = result.discovery_result
            print(f"\n  Discovery:")
            print(f"    Ports      : {len(dr.ports)}")
            print(f"    Processes  : {len(dr.processes)}")
            print(f"    Applications: {len(dr.applications)}")
            if dr.applications:
                for app in dr.applications[:3]:
                    print(f"      • {app.name} ({app.confidence:.0%})")

        # AI Evaluation
        if result.evaluation:
            ev = result.evaluation
            print(f"\n  AI Evaluation:")
            print(f"    Health     : {ev.overall_health.upper()}")
            print(f"    Confidence : {ev.confidence:.0%}")
            if ev.critical_issues:
                print(f"    Issues ({len(ev.critical_issues)}):")
                for issue in ev.critical_issues[:3]:
                    print(f"      ⚠️  {issue}")
            if ev.recommendations:
                print(f"    Recommendations ({len(ev.recommendations)}):")
                for rec in ev.recommendations[:3]:
                    print(f"      💡 {rec}")

        print(f"\n  📝 Full logs: {log_file}")
        print(f"{'═'*65}\n")

    async def _send_email_report(self, result, request, email_address: str):
        """Send validation report via email."""
        if not self.email_service:
            print(f"\n  ⚠️  Email not configured (set SMTP_USERNAME + SMTP_PASSWORD)")
            return

        print(f"\n  📧 Sending report to {email_address}...")
        try:
            report = ValidationReport(
                request=request,
                result=result.validation_result,
                recommendations=result.evaluation.recommendations if result.evaluation else [],
            )
            success = self.email_service.send_validation_report(report, email_address)
            if success:
                print(f"  ✅ Email sent successfully")
                logger.info(f"Email sent to {email_address}", extra={"agent": "Orchestrator"})
            else:
                print(f"  ❌ Failed to send email")
        except Exception as e:
            print(f"  ❌ Email error: {e}")
            logger.error(f"Email send failed: {e}", exc_info=True, extra={"agent": "Orchestrator"})

    # ── Fleet validation ──────────────────────────────────────────────────────

    async def execute_fleet_validation(self, prompt: str) -> None:
        """
        Execute fleet validation from a prompt or fleet.json manifest.

        Supported prompt patterns::

            "validate fleet from fleet.json"
            "validate fleet from config/my-fleet.json"
            "validate fleet 192.168.1.100 192.168.1.101 192.168.1.102"
            "validate 192.168.1.100, 192.168.1.101, 192.168.1.102"

        Args:
            prompt: Natural language fleet prompt.
        """
        print(f"\n{'─'*65}")
        print(f"  💬 {prompt}")
        print(f"{'─'*65}")

        fleet_tracker = AgentTracker("FleetOrchestrator")

        # Note: Telemetry tracing is now automatic via OpenInference BeeAI instrumentation
        
        try:
            manifest = self._parse_fleet_prompt(prompt)
        except Exception as e:
            fleet_tracker.error(f"Failed to parse fleet prompt: {e}", exc=e)
            print(f"\n  ❌ Fleet parse error: {e}")
            return

        fleet_tracker.decision(
            f"Fleet '{manifest.name}': {len(manifest.enabled_targets)} target(s), "
            f"max_parallel={manifest.max_parallel}"
        )

        # Build result placeholders and attach to progress display
        from models import FleetTargetResult, FleetTargetStatus
        results: list[FleetTargetResult] = [
            FleetTargetResult(target=t, status=FleetTargetStatus.PENDING)
            for t in manifest.enabled_targets
        ]
        progress = FleetProgressDisplay(manifest)
        progress.attach(results)
        progress.render()

        # Run fleet - BeeAIInstrumentor automatically traces all operations
        fleet_orch = FleetOrchestrator(self)
        # Monkey-patch _run_one to update display after each target finishes
        _orig_run_one = fleet_orch._run_one

        async def _run_one_with_display(target, result, semaphore, fleet_email):
            await _orig_run_one(target, result, semaphore, fleet_email)
            progress.render()

        fleet_orch._run_one = _run_one_with_display  # type: ignore[method-assign]

        start = __import__("time").time()
        report = await fleet_orch.run_fleet(manifest)
        elapsed = __import__("time").time() - start

        # Final display
        progress.render(final=True)
        self._display_fleet_report(report, elapsed)

    def _parse_fleet_prompt(self, prompt: str) -> FleetManifest:
        """
        Parse a fleet prompt into a FleetManifest.

        Handles three forms:
        1. ``validate fleet from <path>``  — load JSON file
        2. ``validate fleet <ip1> <ip2> …`` — ad-hoc list
        3. Multiple IPs/hostnames anywhere in the prompt — auto-detect

        Args:
            prompt: Raw user prompt.

        Returns:
            Validated FleetManifest.
        """
        import re as _re

        # Form 1: explicit file path
        file_match = _re.search(
            r'(?:from|file|manifest)\s+([\w./\\-]+\.json)',
            prompt, _re.IGNORECASE
        )
        if file_match:
            path = file_match.group(1)
            logger.info(f"Loading fleet manifest from {path}", extra={"agent": "FleetOrchestrator"})
            return FleetOrchestrator.load_manifest(path)

        # Form 2 & 3: extract IPs / hostnames from prompt
        # Match IPv4 addresses
        ips = _re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', prompt)
        # Match hostnames (word chars + dots/hyphens, not pure numbers)
        # Only pick up tokens after "fleet" keyword or comma-separated
        if not ips:
            # Try comma/space separated hostnames after "fleet" keyword
            after_fleet = _re.search(r'fleet\s+(.*)', prompt, _re.IGNORECASE)
            if after_fleet:
                tokens = _re.split(r'[\s,]+', after_fleet.group(1).strip())
                ips = [t for t in tokens if t and not t.lower().startswith('from')]

        if not ips:
            raise ValueError(
                "Could not extract hosts from fleet prompt.\n"
                "Use: 'validate fleet 192.168.1.100 192.168.1.101'\n"
                "  or: 'validate fleet from config/fleet.json'"
            )

        # Extract optional max_parallel hint: "parallel 5" or "concurrency 5"
        par_match = _re.search(r'(?:parallel|concurrency|workers?)\s+(\d+)', prompt, _re.IGNORECASE)
        max_parallel = int(par_match.group(1)) if par_match else 3

        # Extract optional email
        email_match = _re.search(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', prompt
        )
        email = email_match.group(0) if email_match else None

        return FleetOrchestrator.manifest_from_hosts(
            hosts=ips,
            max_parallel=max_parallel,
            fleet_name=f"Ad-hoc Fleet ({len(ips)} hosts)",
            email=email,
        )

    def _display_fleet_report(self, report: FleetReport, elapsed: float) -> None:
        """Print the final fleet summary."""
        print(f"\n{'═'*65}")
        print(f"  📊 Fleet Report: {report.fleet_name}")
        print(f"{'═'*65}")
        print(f"\n  Status  : {report.overall_status.upper()}")
        print(f"  Targets : {report.total_targets}")
        print(f"  ✅ Passed : {report.succeeded}")
        print(f"  ❌ Failed : {report.failed}")
        if report.skipped:
            print(f"  ⏭  Skipped: {report.skipped}")
        if report.average_score is not None:
            print(f"  Avg Score: {report.average_score:.0f}/100")
        print(f"  Time    : {elapsed:.1f}s")

        # Per-target detail for failures
        failures = [r for r in report.results if r.status == FleetTargetStatus.FAILED]
        if failures:
            print(f"\n  Failed targets:")
            for r in failures:
                print(f"    ❌ {r.target.display_name}: {r.error_message or 'unknown error'}")

        print(f"\n  📝 Full logs: {log_file}")
        print(f"{'═'*65}\n")

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def run(self):
        """Run the interactive CLI loop."""
        await self.initialize()

        print(f"\n{'═'*65}")
        print("  💬 Ready! Describe what you want to validate.")
        print(f"{'═'*65}")
        print("\n  Single-target examples:")
        print("    • Validate VM at 192.168.1.100")
        print("    • Check Oracle database at db.example.com")
        print("    • Validate MongoDB at mongo-server:27017")
        print("    • Validate VM at 192.168.1.100 and email report to me@example.com")
        print("    • Use credential vm-prod-01 to validate 192.168.1.100")
        print("\n  Fleet (multi-target) examples:")
        print("    • Validate fleet 192.168.1.100 192.168.1.101 192.168.1.102")
        print("    • Validate fleet from config/fleet.json")
        print("\n  Type 'list credentials' to see available credentials")
        print("  Type 'quit' to exit")
        print(f"\n{'─'*65}")

        logger.info("Interactive mode started", extra={"agent": "System"})

        while True:
            try:
                prompt = input("\n  🤖 > ").strip()

                if not prompt:
                    continue

                if prompt.lower() in ("quit", "exit", "q"):
                    print("\n  👋 Goodbye!")
                    break

                if prompt.lower() in ("list credentials", "credentials", "creds"):
                    self._list_credentials()
                    continue

                if prompt.lower() in ("help", "?"):
                    self._show_help()
                    continue

                # ── Fleet mode detection ──────────────────────────────────────
                # Trigger fleet mode when:
                #   a) prompt contains "fleet" keyword, OR
                #   b) prompt contains 2+ distinct IPv4 addresses
                if self._is_fleet_prompt(prompt):
                    await self.execute_fleet_validation(prompt)
                else:
                    await self.execute_validation(prompt)

            except KeyboardInterrupt:
                print("\n\n  👋 Interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n  ❌ Error: {e}")
                logger.error(f"Interactive loop error: {e}", exc_info=True, extra={"agent": "System"})

        # Cleanup
        if self.orchestrator:
            await self.orchestrator.cleanup()

    def _is_fleet_prompt(self, prompt: str) -> bool:
        """
        Return True if the prompt should trigger fleet mode.

        Fleet mode is triggered when:
        - The word "fleet" appears in the prompt, OR
        - Two or more distinct IPv4 addresses are present.
        """
        import re as _re
        if _re.search(r'\bfleet\b', prompt, _re.IGNORECASE):
            return True
        ips = _re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', prompt)
        return len(set(ips)) >= 2

    def _list_credentials(self):
        """Display available credentials."""
        available = self.credential_resolver.list_available_credentials()
        if not available:
            print("\n  No credentials found in config/secrets.json")
            print("  Edit config/secrets.json to add your infrastructure credentials.")
            return

        print(f"\n  🔑 Available credentials ({len(available)}):")
        print(f"  {'ID':<25} {'Type':<10} {'Hosts':<35} {'Tags'}")
        print(f"  {'─'*25} {'─'*10} {'─'*35} {'─'*20}")
        for cred in available:
            hosts = ", ".join(cred["hosts"][:2])
            if len(cred["hosts"]) > 2:
                hosts += f" +{len(cred['hosts'])-2}"
            tags = ", ".join(cred["tags"][:3])
            print(f"  {cred['credential_id']:<25} {cred['type']:<10} {hosts:<35} {tags}")

    def _show_help(self):
        """Display help text."""
        print("""
  ╔══════════════════════════════════════════════════════════════╗
  ║  Recovery Validation Agent — Help                            ║
  ╠══════════════════════════════════════════════════════════════╣
  ║  COMMANDS                                                    ║
  ║    list credentials  — Show available credentials            ║
  ║    help / ?          — Show this help                        ║
  ║    quit / exit       — Exit the agent                        ║
  ║                                                              ║
  ║  SINGLE-TARGET PROMPTS                                       ║
  ║    Validate VM at <IP>                                       ║
  ║    Check Oracle at <host> [port <N>] [service <name>]        ║
  ║    Validate MongoDB at <host>[:<port>]                       ║
  ║    Use credential <id> to validate <host>                    ║
  ║    ... and email report to <email>                           ║
  ║                                                              ║
  ║  FLEET (MULTI-TARGET) PROMPTS                                ║
  ║    Validate fleet <ip1> <ip2> <ip3>                          ║
  ║    Validate fleet from config/fleet.json                     ║
  ║    Validate fleet <ip1> <ip2> parallel 5                     ║
  ║    (2+ IPs in one prompt also triggers fleet mode)           ║
  ║                                                              ║
  ║  CREDENTIALS                                                 ║
  ║    Add credentials to: config/secrets.json                   ║
  ║    Credentials are looked up by hostname/IP automatically.   ║
  ║    Never put passwords in your prompts.                      ║
  ║                                                              ║
  ║  FLEET MANIFEST                                              ║
  ║    Create config/fleet.json from the example:                ║
  ║      cp config/fleet.example.json config/fleet.json          ║
  ║                                                              ║
  ║  LOGS                                                        ║
  ║    Console: Clean agent activity summary                     ║
  ║    File:    Full structured logs in logs/beeai_*.log         ║
  ╚══════════════════════════════════════════════════════════════╝
""")


async def main():
    """Main entry point."""
    cli = InteractiveCLI()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n  👋 Interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n  ❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure telemetry is properly shut down to flush remaining spans
        if is_telemetry_enabled():
            logger.debug("Shutting down telemetry...", extra={"agent": "System"})
            shutdown_telemetry(timeout=5)

# Made with Bob
