#!/usr/bin/env python3
#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
BeeAI Interactive Validation CLI

Interactive command-line interface for validating infrastructure resources.
Credentials are loaded from config/secrets.json — no passwords in prompts.

Usage:
    python beeai_interactive.py

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
    console_level="INFO",
    log_file_prefix="beeai",
    suppress_noisy_loggers=True,
)

import logging
logger = logging.getLogger(__name__)
logger.info(f"BeeAI Interactive CLI starting — log file: {log_file}", extra={"agent": "System"})

# ── Application imports ───────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; env vars may already be set

from beeai_agents.orchestrator import BeeAIValidationOrchestrator
from models import (
    ValidationRequest,
    ValidationReport,
    VMResourceInfo,
)
from email_service import EmailService
from credentials import CredentialResolver, CredentialNotFoundError


class BeeAIInteractiveCLI:
    """
    Interactive CLI for BeeAI validation workflow.

    Key improvements over previous version:
    - Credentials loaded from config/secrets.json (no passwords in prompts)
    - Enhanced logging: agent activity visible on console, full detail in log file
    - Credential ID support: reference credentials by name in prompts
    """

    def __init__(self):
        self.orchestrator: BeeAIValidationOrchestrator | None = None
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
                self.orchestrator = BeeAIValidationOrchestrator(
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
                '  "<credential-id>": { "hosts": ["<IP>"], "ssh": { "username": "...", "password": "..." } }'
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
        Execute validation based on user prompt.

        Args:
            prompt: Natural language validation prompt
        """
        print(f"\n{'─'*65}")
        print(f"  💬 {prompt}")
        print(f"{'─'*65}")

        exec_tracker = AgentTracker("Orchestrator")

        try:
            # Step 1: Parse prompt — extract host and credential ID
            exec_tracker.decision("Parsing prompt to identify target host")
            info, email_address = self.parse_prompt(prompt)

            print(f"\n  ✅ Understood:")
            print(f"     Target : {info['host']}")
            if info.get("credential_id"):
                print(f"     Cred ID: {info['credential_id']}")
            if email_address:
                print(f"     Email  : {email_address}")
            print(f"     Mode   : Agent-driven discovery (SSH → detect workloads)")

            # Step 2: Resolve credentials + build Pydantic model
            request = await self._resolve_and_build_request(info)
            resource = request.resource_info

            # Show workflow progress
            progress = WorkflowProgressDisplay(resource.host)
            progress.start_workflow()

            # Execute workflow
            start_time = __import__("time").time()
            progress.update_phase("discovery",  "running", "Scanning workloads...")
            if self.orchestrator is None:
                raise RuntimeError("Orchestrator not initialised")
            result = await self.orchestrator.execute_workflow(request)
            elapsed = __import__("time").time() - start_time

            # Update progress display
            for phase, timing in result.phase_timings.items():
                status = "done" if phase in result.errors else "done"
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
                await self._send_email_report(result, request, email_address)

        except Exception as e:
            exec_tracker.error(f"Validation failed: {e}", exc=e)
            print(f"\n  ❌ Error: {e}")
            logger.error(f"Validation error", exc_info=True, extra={"agent": "Orchestrator"})

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
                }.get(check.status.value, "  ❓")

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

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def run(self):
        """Run the interactive CLI loop."""
        await self.initialize()

        print(f"\n{'═'*65}")
        print("  💬 Ready! Describe what you want to validate.")
        print(f"{'═'*65}")
        print("\n  Examples:")
        print("    • Validate VM at 192.168.1.100")
        print("    • Check Oracle database at db.example.com")
        print("    • Validate MongoDB at mongo-server:27017")
        print("    • Validate VM at 192.168.1.100 and email report to me@example.com")
        print("    • Use credential vm-prod-01 to validate 192.168.1.100")
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
  ║  BeeAI Validation Agent — Help                               ║
  ╠══════════════════════════════════════════════════════════════╣
  ║  COMMANDS                                                    ║
  ║    list credentials  — Show available credentials            ║
  ║    help / ?          — Show this help                        ║
  ║    quit / exit       — Exit the agent                        ║
  ║                                                              ║
  ║  VALIDATION PROMPTS                                          ║
  ║    Validate VM at <IP>                                       ║
  ║    Check Oracle at <host> [port <N>] [service <name>]        ║
  ║    Validate MongoDB at <host>[:<port>]                       ║
  ║    Use credential <id> to validate <host>                    ║
  ║    ... and email report to <email>                           ║
  ║                                                              ║
  ║  CREDENTIALS                                                 ║
  ║    Add credentials to: config/secrets.json                   ║
  ║    Credentials are looked up by hostname/IP automatically.   ║
  ║    Never put passwords in your prompts.                      ║
  ║                                                              ║
  ║  LOGS                                                        ║
  ║    Console: Clean agent activity summary                     ║
  ║    File:    Full structured logs in logs/beeai_*.log         ║
  ╚══════════════════════════════════════════════════════════════╝
""")


async def main():
    """Main entry point."""
    cli = BeeAIInteractiveCLI()
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

# Made with Bob
