
#
# Copyright contributors to the agentic-ai-cyberres project
#
from __future__ import annotations

import html as _html
import json
import logging
import os
import re
import stat
import time as _time
from collections import OrderedDict
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations  # type: ignore[import-untyped]

from .settings import SETTINGS
from .plugins import vms_validator, oracle_db, mongo_db, net, workload_discovery

try:
    _server_version = _pkg_version("cyberres-mcp")
except PackageNotFoundError:
    _server_version = "0.0.0"

# In-process run-result store keyed by run_id (1-hour TTL).
# OrderedDict preserves insertion order so front-eviction is O(1).
_run_results: OrderedDict[str, dict] = OrderedDict()


def _store_result(run_id: str, data: dict) -> None:
    _run_results.pop(run_id, None)
    _run_results[run_id] = {**data, "_ts": _time.time()}
    cutoff = _time.time() - 3600
    while _run_results:
        oldest_key = next(iter(_run_results))
        if _run_results[oldest_key].get("_ts", 0) < cutoff:
            _run_results.popitem(last=False)
        else:
            break


def _patch_mcp_duplicate_respond() -> None:
    """Prevent session crashes when a request is cancelled while a sync tool is running.

    Root cause: MCP Inspector sends notifications/cancelled after its 60 s timeout.
    The MCP library calls RequestResponder.respond() with a "cancelled" error
    (setting _completed=True).  The SSH thread finishes shortly after; FastMCP's
    _handle_request then calls respond() with the real result → AssertionError →
    session crash.

    Fix: wrap respond() to silently drop the duplicate.  The client already
    received the cancellation response, so discarding the second is correct.
    """
    from mcp.shared.session import RequestResponder  # type: ignore[import-untyped]

    _original_respond = RequestResponder.respond

    async def _safe_respond(self, response):  # type: ignore[no-untyped-def]
        if self._completed:
            logging.getLogger(_MCP_SERVER_LOGGER).debug(
                "Suppressed duplicate respond() for request %s — already completed",
                getattr(self, "request_id", "?"),
            )
            return
        await _original_respond(self, response)

    RequestResponder.respond = _safe_respond  # type: ignore[method-assign]


_patch_mcp_duplicate_respond()


# ── Module-level logging helpers ─────────────────────────────────────────────

class _RepetitiveMessageFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "trust_unknown_hosts is enabled" not in record.getMessage()


class _SensitiveDataFilter(logging.Filter):
    """Redact passwords, tokens, and URI credentials from log records.

    Only masks values associated with known sensitive keys (password, token,
    secret, key, auth). The broad >=24-char alphanumeric regex was removed
    because it silently masked UUIDs, Oracle SIDs, and hostnames.
    """

    _sensitive_key_re = re.compile(
        r"\b(pass(word)?|token|secret|api_?key|authorization|auth|pwd)\b",
        re.IGNORECASE,
    )
    _uri_creds_re = re.compile(r"(://[^/\s:@]+:)([^@\s]+)(@)")

    def _scrub_str(self, value: str) -> str:
        return self._uri_creds_re.sub(r"\1***\3", value)

    def _scrub_dict(self, d: dict) -> dict:
        safe: dict = {}
        for dk, dv in d.items():
            if self._sensitive_key_re.search(str(dk)):
                safe[dk] = "***"
            elif isinstance(dv, str):
                safe[dk] = self._scrub_str(dv)
            else:
                safe[dk] = dv
        return safe

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._scrub_str(record.msg)
        for k, v in record.__dict__.items():
            if isinstance(v, str):
                record.__dict__[k] = self._scrub_str(v)
            elif isinstance(v, dict):
                record.__dict__[k] = self._scrub_dict(v)
        return True


_MCP_SERVER_LOGGER = "mcp.server"


def _configure_logging(log_level: int) -> None:
    """Configure terminal-visible MCP logs and attach safety filters."""
    root = logging.getLogger()
    root.setLevel(log_level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(handler)
    for handler in root.handlers:
        handler.setLevel(log_level)
        if not any(isinstance(f, _SensitiveDataFilter) for f in handler.filters):
            handler.addFilter(_SensitiveDataFilter())

    for logger_name in (
        _MCP_SERVER_LOGGER,
        "mcp.net",
        "mcp.vm",
        "mcp.oracle",
        "mcp.mongo",
        "mcp.ssh_utils",
        "mcp.workload_discovery",
        "mcp.workload_discovery.aggregator",
        "mcp.workload_discovery.os_detector",
        "mcp.workload_discovery.raw_data_collector",
    ):
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.propagate = True
        if not any(isinstance(f, _SensitiveDataFilter) for f in logger.filters):
            logger.addFilter(_SensitiveDataFilter())

    logging.getLogger("mcp.ssh_utils").addFilter(_RepetitiveMessageFilter())
    if not any(isinstance(f, _SensitiveDataFilter) for f in root.filters):
        root.addFilter(_SensitiveDataFilter())


def _load_secrets(secrets_path: str, logger: logging.Logger) -> dict:
    """Load and return secrets from file; warn on insecure permissions."""
    if not os.path.exists(secrets_path):
        logger.info("No secrets file found", extra={"path": secrets_path})
        return {}
    try:
        file_mode = os.stat(secrets_path).st_mode
        if file_mode & (stat.S_IRGRP | stat.S_IROTH):
            logger.warning(
                "Secrets file is group- or world-readable — restrict to 600",
                extra={"path": secrets_path, "mode": oct(file_mode & 0o777)},
            )
        with open(secrets_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("Loaded secrets file", extra={"path": secrets_path, "keys": list(data.keys())})
        return data
    except Exception as e:
        logger.warning("Failed to load secrets file", extra={"path": secrets_path, "error": str(e)})
        return {}


def _render_report_html(run_id: str, r: dict) -> str:
    """Render a validation run result as an HTML dashboard page."""
    color = {"PASS": "#2ea043", "PARTIAL": "#d29922", "FAIL": "#f85149"}.get(r["status"], "#888")
    safe = {k: _html.escape(str(r.get(k, ""))) for k in ("score", "status", "executive_summary", "technician_report")}
    safe_run_id = _html.escape(str(run_id))
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>"
        "body{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;padding:24px;margin:0}"
        f".badge{{background:{color};color:#fff;padding:4px 14px;border-radius:12px;font-weight:700;font-size:14px}}"
        f".score{{font-size:56px;font-weight:800;color:{color};margin:8px 0}}"
        "h2{color:#e6edf3;margin-bottom:4px}h3{color:#8b949e;margin-top:24px}"
        "pre{background:#161b22;padding:14px;border-radius:8px;overflow:auto;font-size:12px;"
        "white-space:pre-wrap;word-break:break-word;border:1px solid #30363d}"
        "code{color:#79c0ff}"
        "</style></head><body>"
        "<h2>Recovery Validation Report</h2>"
        f"<p>Run ID: <code>{safe_run_id}</code></p>"
        f"<div class='score'>{safe['score']}/100</div>"
        f"<span class='badge'>{safe['status']}</span>"
        "<h3>Executive Summary</h3>"
        f"<pre>{safe['executive_summary']}</pre>"
        "<h3>Technician Details</h3>"
        f"<pre>{safe['technician_report']}</pre>"
        "</body></html>"
    )


def create_app() -> FastMCP:
    """Create and configure a FastMCP instance with tools and resources."""
    _log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    _log_level = getattr(logging, _log_level_name, logging.WARNING)
    logging.basicConfig(level=_log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    _configure_logging(_log_level)
    logger = logging.getLogger(_MCP_SERVER_LOGGER)
    logger.info("MCP server logging configured", extra={"level": _log_level_name})

    # Load secrets file if present and warn on insecure permissions.
    secrets = {}
    secrets_path = os.path.join(os.path.dirname(__file__), SETTINGS.secrets_file)
    try:
        if os.path.exists(secrets_path):
            file_mode = os.stat(secrets_path).st_mode
            if file_mode & (stat.S_IRGRP | stat.S_IROTH):
                logger.warning(
                    "Secrets file is group- or world-readable — restrict to 600",
                    extra={"path": secrets_path, "mode": oct(file_mode & 0o777)},
                )
            with open(secrets_path, "r", encoding="utf-8") as fh:
                secrets = json.load(fh)
            logger.info("Loaded secrets file", extra={"path": secrets_path, "keys": list(secrets.keys())})
        else:
            logger.info("No secrets file found", extra={"path": secrets_path})
    except Exception as e:
        logger.warning("Failed to load secrets file", extra={"path": secrets_path, "error": str(e)})

    app = FastMCP(
        "Recovery_Validation_MCP",
        version=_server_version,
        instructions=(
            "Validates recovered infrastructure resources including Linux VMs, "
            "Oracle databases, and MongoDB clusters. Exposes tools to check "
            "network connectivity, OS health, database connectivity, "
            "data integrity, replica status, and workload discovery."
        ),
    )

    # ── Server tools ─────────────────────────────────────────────────────────────

    @app.tool(
        title="Server Health",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def server_health(ctx: Context) -> dict:
        """[Server] Report MCP server health and advertised capabilities."""
        from .plugins.utils import ok
        await ctx.log(f"Health check - version {_server_version}", level="info")
        try:
            tool_count = len(await app.list_tools())
        except Exception:
            tool_count = -1
        return ok({
            "status": "healthy",
            "version": _server_version,
            "plugins": ["network", "vm_linux", "oracle_db", "mongodb", "workload_discovery"],
            "capabilities": {
                "tools": tool_count,
                "resources": 3,
                "prompts": 3,
            },
            "description": (
                "Recovery validation MCP server for infrastructure health checks "
                "and workload discovery."
            ),
        })

    @app.tool(
        title="List Credential IDs",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def list_credential_ids() -> dict:
        """[Credentials] List available credential IDs without exposing passwords."""
        from .plugins.utils import ok, err
        try:
            if os.path.exists(secrets_path):
                with open(secrets_path, "r", encoding="utf-8") as fh:
                    fresh = json.load(fh)
            else:
                fresh = secrets
            ids = sorted(fresh.keys())
            return ok({"credential_ids": ids, "count": len(ids)})
        except Exception as exc:
            return err(f"Could not read credential IDs: {exc}", code="CRED_READ_ERROR")

    @app.tool(
        title="Store Run Result",
        annotations=ToolAnnotations(idempotentHint=True),
    )
    def store_run_result(
        run_id: str,
        score: int,
        status: str,
        executive_summary: str,
        technician_report: str,
        failures: str = "[]",
    ) -> dict:
        """[Dashboard] Persist a completed validation run result for the dashboard.

        Args:
            run_id: Unique identifier for this validation run.
            score: Numeric score 0–100.
            status: One of PASS, PARTIAL, or FAIL.
            executive_summary: High-level summary for stakeholders.
            technician_report: Detailed technical findings.
            failures: JSON array of failure objects (default: empty array).
        """
        from .plugins.utils import ok, err
        try:
            json.loads(failures)
        except json.JSONDecodeError as exc:
            return err(f"failures must be a valid JSON array: {exc}", code="INVALID_INPUT")
        _store_result(run_id, {
            "score":             score,
            "status":            status,
            "executive_summary": executive_summary,
            "technician_report": technician_report,
            "failures":          failures,
        })
        return ok({"run_id": run_id, "stored": True})

    @app.tool(
        title="Validation Report UI",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def get_validation_report_ui(run_id: str) -> dict:
        """[Dashboard] Return an HTML dashboard for a completed validation run.

        Args:
            run_id: The run ID previously stored via store_run_result.
        """
        from .plugins.utils import ok, err
        r = _run_results.get(run_id)
        if not r:
            return err(f"No result found for run_id={run_id}", code="RESULT_NOT_FOUND")
        return ok({"content_type": "text/html", "html": _render_report_html(run_id, r), "run_id": run_id})

    # ── Plugin tools ──────────────────────────────────────────────────────────────
    net.attach(app)
    vms_validator.attach(app)
    oracle_db.attach(app)
    mongo_db.attach(app)
    workload_discovery.attach(app)

    # ── Native MCP resources (acceptance profiles) ────────────────────────────────
    resource_dir = os.path.join(os.path.dirname(__file__), "resources", "acceptance")

    @app.resource(
        "resource://acceptance/vm-core",
        title="VM Core Acceptance Criteria",
        description="Thresholds for Linux VM health: filesystem usage, memory, required services.",
        mime_type="application/json",
    )
    def acceptance_vm_core() -> str:
        with open(os.path.join(resource_dir, "vm-core.json"), "r", encoding="utf-8") as f:
            return f.read()

    @app.resource(
        "resource://acceptance/db-oracle",
        title="Oracle DB Acceptance Criteria",
        description="Criteria for Oracle validation: tablespace usage, connection requirements.",
        mime_type="application/json",
    )
    def acceptance_db_oracle() -> str:
        with open(os.path.join(resource_dir, "db-oracle.json"), "r", encoding="utf-8") as f:
            return f.read()

    @app.resource(
        "resource://acceptance/db-mongo",
        title="MongoDB Acceptance Criteria",
        description="Criteria for MongoDB validation: replica health, replication lag.",
        mime_type="application/json",
    )
    def acceptance_db_mongo() -> str:
        with open(os.path.join(resource_dir, "db-mongo.json"), "r", encoding="utf-8") as f:
            return f.read()

    # ── Native MCP prompts (orchestration templates) ──────────────────────────────
    prompt_dir = os.path.join(os.path.dirname(__file__), "prompts")

    @app.prompt("planner")
    def planner_prompt() -> str:
        with open(os.path.join(prompt_dir, "planner.md"), "r", encoding="utf-8") as f:
            return f.read()

    @app.prompt("evaluator")
    def evaluator_prompt(run_id: str = "") -> str:
        """Evaluate validation results against acceptance criteria.

        Args:
            run_id: Optional run ID to include stored result in the prompt context.
        """
        with open(os.path.join(prompt_dir, "evaluator.md"), "r", encoding="utf-8") as f:
            template = f.read()
        if run_id and run_id in _run_results:
            r = _run_results[run_id]
            template += (
                f"\n\n## Run Context (run_id={run_id})\n"
                f"- Score: {r['score']}/100\n"
                f"- Status: {r['status']}\n\n"
                f"### Executive Summary\n{r['executive_summary']}\n\n"
                f"### Technician Report\n{r['technician_report']}\n"
            )
        return template

    @app.prompt("summarizer")
    def summarizer_prompt(run_id: str = "") -> str:
        """Generate an executive summary of validation results.

        Args:
            run_id: Optional run ID to include stored result in the prompt context.
        """
        with open(os.path.join(prompt_dir, "summarizer.md"), "r", encoding="utf-8") as f:
            template = f.read()
        if run_id and run_id in _run_results:
            r = _run_results[run_id]
            template += (
                f"\n\n## Run Context (run_id={run_id})\n"
                f"- Score: {r['score']}/100\n"
                f"- Status: {r['status']}\n\n"
                f"### Executive Summary\n{r['executive_summary']}\n\n"
                f"### Technician Report\n{r['technician_report']}\n"
            )
        return template

    return app


def _is_broken_pipe(exc: BaseException) -> bool:
    """Return True if exc is (or contains) a BrokenPipeError."""
    if isinstance(exc, BrokenPipeError):
        return True
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_broken_pipe(e) for e in exc.exceptions)
    return False


def main() -> None:
    """Entry point for running the MCP server."""
    app = create_app()

    try:
        if SETTINGS.transport == "stdio":
            app.run(transport="stdio")
        else:
            app.run(transport=SETTINGS.transport, host=SETTINGS.host, port=SETTINGS.port)
    except OSError:
        # Client disconnected — expected for stdio/HTTP teardown.
        return
    except BaseException as exc:  # noqa: BLE001
        if not _is_broken_pipe(exc):
            raise


if __name__ == "__main__":
    main()
