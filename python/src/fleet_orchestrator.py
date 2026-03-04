#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
Fleet Orchestrator — IMP-3: Multi-VM / Multi-Resource Validation

Runs the existing single-resource BeeAI validation workflow concurrently
across a fleet of targets defined in ``config/fleet.json`` (or built
programmatically).

Design principles
-----------------
* **Reuse, don't rewrite** — delegates every per-target run to the existing
  ``BeeAIValidationOrchestrator`` + ``BeeAIInteractiveCLI._resolve_and_build_request()``.
* **Bounded concurrency** — ``asyncio.Semaphore(max_parallel)`` prevents
  overwhelming the LLM / MCP server.
* **Shared MCP connection** — a single ``BeeAIValidationOrchestrator`` instance
  is initialised once and reused for all targets (the MCP server is stateless
  per-call).
* **Fail-safe** — one target failing never aborts the rest; errors are captured
  in ``FleetTargetResult.error_message``.
* **Structured logging** — every target gets its own ``AgentTracker`` so the
  console shows which host is active and the log file has per-host context.

Usage
-----
From ``beeai_interactive.py``::

    fleet = FleetOrchestrator(cli)
    report = await fleet.run_fleet(manifest)

Or standalone::

    manifest = FleetManifest.model_validate_json(Path("config/fleet.json").read_text())
    report   = await FleetOrchestrator.run_standalone(manifest)
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models import (
    FleetManifest,
    FleetReport,
    FleetTarget,
    FleetTargetResult,
    FleetTargetStatus,
    ValidationRequest,
)

logger = logging.getLogger(__name__)

# ── Optional AgentTracker import (graceful degradation) ──────────────────────
try:
    from agent_logging.agent_logger import AgentTracker
    _TRACKER_AVAILABLE = True
except ImportError:
    AgentTracker = None          # type: ignore[assignment,misc]
    _TRACKER_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# FleetOrchestrator
# ─────────────────────────────────────────────────────────────────────────────

class FleetOrchestrator:
    """
    Runs validation for a fleet of targets concurrently.

    Parameters
    ----------
    cli:
        An initialised ``BeeAIInteractiveCLI`` instance.  The fleet
        orchestrator borrows its ``credential_resolver``, ``orchestrator``
        (BeeAI), and ``email_service``.
    """

    def __init__(self, cli):
        # Avoid a circular import — cli is typed as Any at runtime.
        self._cli = cli

    # ── Public API ────────────────────────────────────────────────────────────

    async def run_fleet(self, manifest: FleetManifest) -> FleetReport:
        """
        Validate all enabled targets in *manifest* and return a ``FleetReport``.

        Targets are run with at most ``manifest.max_parallel`` concurrent
        workers.  Each worker uses the shared ``BeeAIValidationOrchestrator``
        (which is thread-safe for concurrent async calls because every call
        creates its own MCP request context).

        Args:
            manifest: Fleet manifest with targets and concurrency settings.

        Returns:
            FleetReport with per-target results and aggregate statistics.
        """
        targets = manifest.enabled_targets
        if not targets:
            logger.warning("Fleet manifest has no enabled targets — nothing to do")
            return FleetReport(
                fleet_name=manifest.name,
                total_targets=0,
                finished_at=datetime.now(timezone.utc),
            )

        fleet_tracker = None
        if _TRACKER_AVAILABLE and AgentTracker is not None:
            fleet_tracker = AgentTracker("FleetOrchestrator")
            fleet_tracker.start(
                f"Fleet '{manifest.name}': {len(targets)} target(s), "
                f"max_parallel={manifest.max_parallel}"
            )

        report = FleetReport(
            fleet_name=manifest.name,
            total_targets=len(targets),
            started_at=datetime.now(timezone.utc),
        )

        semaphore = asyncio.Semaphore(manifest.max_parallel)
        fleet_start = time.monotonic()

        # Build one result placeholder per target (preserves order)
        results: list[FleetTargetResult] = [
            FleetTargetResult(target=t, status=FleetTargetStatus.PENDING)
            for t in targets
        ]

        # ── Run all targets concurrently (bounded by semaphore) ───────────────
        tasks = [
            self._run_one(
                target=targets[i],
                result=results[i],
                semaphore=semaphore,
                fleet_email=manifest.email_report_to,
            )
            for i in range(len(targets))
        ]
        await asyncio.gather(*tasks, return_exceptions=False)

        # ── Aggregate ─────────────────────────────────────────────────────────
        report.results = results
        report.completed   = sum(1 for r in results if r.status in (FleetTargetStatus.DONE, FleetTargetStatus.FAILED))
        report.succeeded   = sum(1 for r in results if r.status == FleetTargetStatus.DONE)
        report.failed      = sum(1 for r in results if r.status == FleetTargetStatus.FAILED)
        report.skipped     = sum(1 for r in results if r.status == FleetTargetStatus.SKIPPED)
        report.execution_time_seconds = time.monotonic() - fleet_start
        report.finished_at = datetime.now(timezone.utc)

        if fleet_tracker:
            fleet_tracker.finish(report.to_summary())

        logger.info(report.to_summary())
        return report

    # ── Per-target worker ─────────────────────────────────────────────────────

    async def _run_one(
        self,
        target: FleetTarget,
        result: FleetTargetResult,
        semaphore: asyncio.Semaphore,
        fleet_email: Optional[str],
    ) -> None:
        """
        Validate a single target inside the semaphore guard.

        Mutates *result* in-place — no return value needed because
        ``asyncio.gather`` collects None from each worker.
        """
        async with semaphore:
            result.status     = FleetTargetStatus.RUNNING
            result.started_at = datetime.now(timezone.utc)
            t_start           = time.monotonic()

            target_tracker = None
            if _TRACKER_AVAILABLE and AgentTracker is not None:
                target_tracker = AgentTracker("FleetWorker", resource=target.display_name)
                target_tracker.start(f"Validating {target.display_name}")

            try:
                # ── Build prompt info dict (same shape as parse_prompt output) ─
                info = {
                    "host":          target.host,
                    "credential_id": target.credential_id,
                    "ssh_port":      target.ssh_port,
                    "auto_discover": True,
                }

                # ── Resolve credentials + build ValidationRequest ─────────────
                request: ValidationRequest = await self._cli._resolve_and_build_request(info)

                # ── Execute workflow via shared orchestrator ───────────────────
                if self._cli.orchestrator is None:
                    raise RuntimeError("BeeAI orchestrator not initialised")

                wf_result = await self._cli.orchestrator.execute_workflow(request)

                # ── Populate result ───────────────────────────────────────────
                vr = wf_result.validation_result
                result.status           = FleetTargetStatus.DONE
                result.score            = vr.score
                result.workflow_status  = wf_result.workflow_status
                result.passed_checks    = vr.passed_checks
                result.failed_checks    = vr.failed_checks
                result.warning_checks   = vr.warning_checks

                if target_tracker:
                    target_tracker.finish(
                        f"{target.display_name}: score={vr.score}/100 "
                        f"({vr.passed_checks}✅ {vr.failed_checks}❌)"
                    )

                # ── Per-target email (optional) ───────────────────────────────
                email = target.email_report_to or fleet_email
                if email and self._cli.email_service:
                    await self._cli._send_email_report(wf_result, request, email)

            except Exception as exc:
                result.status        = FleetTargetStatus.FAILED
                result.error_message = str(exc)
                logger.error(
                    f"Fleet target {target.display_name} failed: {exc}",
                    exc_info=True,
                    extra={"agent": "FleetOrchestrator", "host": target.host},
                )
                if target_tracker:
                    target_tracker.error(f"{target.display_name} failed: {exc}", exc=exc)

            finally:
                result.execution_time_seconds = time.monotonic() - t_start
                result.finished_at            = datetime.now(timezone.utc)

    # ── Manifest helpers ──────────────────────────────────────────────────────

    @staticmethod
    def load_manifest(path: str | Path = "config/fleet.json") -> FleetManifest:
        """
        Load a fleet manifest from a JSON file.

        Args:
            path: Path to the fleet JSON file (default: ``config/fleet.json``).

        Returns:
            Validated ``FleetManifest`` instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the JSON is invalid or fails Pydantic validation.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Fleet manifest not found: {p}\n"
                "Create one from the example: cp config/fleet.example.json config/fleet.json"
            )
        raw = json.loads(p.read_text(encoding="utf-8"))
        return FleetManifest.model_validate(raw)

    @staticmethod
    def manifest_from_hosts(
        hosts: list[str],
        max_parallel: int = 3,
        fleet_name: str = "Ad-hoc Fleet",
        email: Optional[str] = None,
    ) -> FleetManifest:
        """
        Build a ``FleetManifest`` from a plain list of host strings.

        Credential IDs are resolved automatically by hostname/IP at runtime
        using the host-keyed ``config/secrets.json``.

        Args:
            hosts:        List of IP addresses or hostnames.
            max_parallel: Maximum concurrent validations.
            fleet_name:   Human-readable name for the fleet run.
            email:        Optional email address to send the fleet report to.

        Returns:
            ``FleetManifest`` ready to pass to ``run_fleet()``.
        """
        from models import FleetTarget  # local import to avoid circular at module level
        targets = [FleetTarget(host=h) for h in hosts]
        return FleetManifest(
            name=fleet_name,
            max_parallel=max_parallel,
            email_report_to=email,
            targets=targets,
        )


# ── Standalone helper (for scripting / testing) ───────────────────────────────

async def run_fleet_standalone(
    manifest_path: str | Path = "config/fleet.json",
    mcp_server_path: str = "../cyberres-mcp",
    llm_model: str = "ollama:llama3.2",
) -> FleetReport:
    """
    Run a fleet validation without the interactive CLI.

    Useful for scripting, CI pipelines, or testing.

    Args:
        manifest_path:   Path to fleet.json.
        mcp_server_path: Path to the MCP server directory.
        llm_model:       LLM model identifier.

    Returns:
        ``FleetReport`` with all results.

    Example::

        import asyncio
        from fleet_orchestrator import run_fleet_standalone
        report = asyncio.run(run_fleet_standalone("config/fleet.json"))
        print(report.to_summary())
    """
    # Lazy import to avoid circular dependency when used as a library
    from beeai_interactive import BeeAIInteractiveCLI

    cli = BeeAIInteractiveCLI()
    # Override defaults if provided
    cli.orchestrator = None  # will be created in initialize()
    await cli.initialize()

    manifest = FleetOrchestrator.load_manifest(manifest_path)
    orchestrator = FleetOrchestrator(cli)
    report = await orchestrator.run_fleet(manifest)

    orch = cli.orchestrator
    if orch is not None:
        await orch.cleanup()  # type: ignore[misc]

    return report


# Made with Bob