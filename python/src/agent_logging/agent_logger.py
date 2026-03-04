#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
Agent logging for BeeAI recovery-validation workflow.

Provides:
  setup_logging()          — configure dual-stream logging (console + JSON file)
  AgentTracker             — emit structured console + log events for one agent role
  WorkflowProgressDisplay  — live phase-progress table for a single VM workflow

Console output (INFO):
  Clean agent role banners with icons, decisions, and warnings.
  No raw stack traces, no SSH/MCP internals.

Log file output (DEBUG, JSON lines):
  Every tool call, result, retry, decision, and phase transition.
  Passwords are redacted by SensitiveDataFilter.

Usage::

    from agent_logging.agent_logger import setup_logging, AgentTracker, WorkflowProgressDisplay

    log_file = setup_logging(log_dir="logs", log_level="DEBUG", console_level="INFO",
                             log_file_prefix="beeai", suppress_noisy_loggers=True)

    tracker = AgentTracker("DiscoveryAgent", resource="192.168.1.100")
    tracker.start("Scanning workloads")
    with tracker.phase("discovery", "Port scanning"):
        ...
    tracker.thinking("Found 3 open ports — checking for MongoDB...")
    tracker.decision("Detected MongoDB on port 27017", confidence=0.9)
    tracker.finish("Discovery complete")

    progress = WorkflowProgressDisplay("192.168.1.100")
    progress.start_workflow()
    progress.update_phase("discovery", "running", "Scanning ports...")
    progress.update_phase("discovery", "done", "4.2s")
    progress.finish_workflow(status="success", score=85, elapsed=12.3)
"""

import json
import logging
import logging.handlers
import os
import re
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Optional


# ── ANSI colour helpers ───────────────────────────────────────────────────────

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_RED    = "\033[31m"
_CYAN   = "\033[36m"
_WHITE  = "\033[37m"
_GREY   = "\033[90m"

def _c(text: str, *codes: str) -> str:
    """Wrap text in ANSI codes (no-op if stdout is not a tty)."""
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + _RESET


# ── Agent role registry ───────────────────────────────────────────────────────

AGENT_ROLES: Dict[str, tuple[str, str]] = {
    "discovery":    ("🔍", "Discovery Agent"),
    "planning":     ("📋", "Planning Agent"),
    "validation":   ("⚙️ ", "Validation Agent"),
    "evaluation":   ("🧠", "Evaluation Agent"),
    "credentials":  ("🔑", "Credential Resolver"),
    "orchestrator": ("🤖", "Orchestrator"),
    "system":       ("⚙️ ", "System"),
    "fleet":        ("🐝", "Fleet Orchestrator"),
}

def _role_display(agent_name: str) -> tuple[str, str]:
    """Return (icon, display_name) for an agent name."""
    key = agent_name.lower().replace(" ", "").replace("agent", "")
    for k, v in AGENT_ROLES.items():
        if k in key or key in k:
            return v
    return ("🤖", agent_name)


# ── SensitiveDataFilter ───────────────────────────────────────────────────────

class SensitiveDataFilter(logging.Filter):
    """
    Redact passwords, tokens, and API keys from log records.

    Mirrors the filter already applied in cyberres-mcp/server.py so that
    agent-side logs are equally safe.
    """

    _sensitive_key_re = re.compile(
        r"(pass(word)?|token|secret|key|authorization|auth|pwd|api_key)",
        re.IGNORECASE,
    )
    _uri_creds_re = re.compile(r"(://[^/\s:@]+:)([^@\s]+)(@)")

    # Reserved LogRecord attributes that must never be overwritten.
    # Python 3.12+ raises ValueError: "Attempt to overwrite '<attr>' in LogRecord"
    # if you assign to these via record.__dict__[k].
    _LOGRECORD_RESERVED = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "taskName",
        "message",
    })

    def _scrub(self, value: str) -> str:
        masked = self._uri_creds_re.sub(r"\1***\3", value)
        masked = re.sub(r"([A-Za-z0-9_-]{24,})", "***", masked)
        return masked

    def filter(self, record: logging.LogRecord) -> bool:
        # Scrub the message string directly (safe — msg is a plain attribute).
        if isinstance(record.msg, str):
            record.msg = self._scrub(record.msg)

        # Only touch user-supplied extra fields; never touch reserved LogRecord
        # attributes (Python 3.12+ raises ValueError if you try).
        for k, v in list(record.__dict__.items()):
            if k in self._LOGRECORD_RESERVED or k.startswith("_"):
                continue
            if isinstance(v, str):
                if self._sensitive_key_re.search(k):
                    record.__dict__[k] = "***"
                else:
                    record.__dict__[k] = self._scrub(v)
            elif isinstance(v, dict):
                safe: Dict[str, Any] = {}
                for dk, dv in v.items():
                    if self._sensitive_key_re.search(str(dk)):
                        safe[dk] = "***"
                    elif isinstance(dv, str):
                        safe[dk] = self._scrub(dv)
                    else:
                        safe[dk] = dv
                record.__dict__[k] = safe
        return True


# ── JSON log formatter ────────────────────────────────────────────────────────

class JsonLineFormatter(logging.Formatter):
    """
    Format each log record as a single JSON line.

    Fields emitted:
      ts, level, logger, agent, phase, event, host, message, + any extras
    """

    def format(self, record: logging.LogRecord) -> str:
        doc: Dict[str, Any] = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "agent":   getattr(record, "agent", ""),
            "phase":   getattr(record, "phase", ""),
            "event":   getattr(record, "event", ""),
            "host":    getattr(record, "host", ""),
            "message": record.getMessage(),
        }
        # Include any extra structured fields attached by the caller
        _skip = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "agent", "phase", "event", "host",
        }
        for k, v in record.__dict__.items():
            if k not in _skip and not k.startswith("_"):
                doc[k] = v
        if record.exc_info:
            doc["exception"] = self.formatException(record.exc_info)
        return json.dumps(doc, default=str)


# ── Console formatter ─────────────────────────────────────────────────────────

class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter.

    Shows:  [HH:MM:SS]  LEVEL  message
    Hides:  logger name, agent internals (those go to the JSON file)
    """

    _LEVEL_COLOURS = {
        "DEBUG":    _GREY,
        "INFO":     _WHITE,
        "WARNING":  _YELLOW,
        "ERROR":    _RED,
        "CRITICAL": _RED + _BOLD,
    }

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        colour = self._LEVEL_COLOURS.get(record.levelname, _WHITE)
        level_tag = f"{colour}{record.levelname:<8}{_RESET}" if sys.stdout.isatty() else record.levelname
        return f"  {_c(ts, _GREY)}  {level_tag}  {record.getMessage()}"


# ── setup_logging ─────────────────────────────────────────────────────────────

def setup_logging(
    log_dir: str = "logs",
    log_level: str = "DEBUG",
    console_level: str = "INFO",
    log_file_prefix: str = "beeai",
    suppress_noisy_loggers: bool = True,
) -> str:
    """
    Configure dual-stream logging for the BeeAI agent.

    - Console handler: ``console_level`` (default INFO), human-readable
    - File handler:    ``log_level`` (default DEBUG), JSON lines

    Args:
        log_dir:               Directory for log files (created if absent)
        log_level:             Minimum level written to the log file
        console_level:         Minimum level written to the console
        log_file_prefix:       Prefix for the log file name
        suppress_noisy_loggers: Silence paramiko, mcp.*, asyncio, urllib3

    Returns:
        Absolute path to the log file created.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_path / f"{log_file_prefix}-{timestamp}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # root captures everything; handlers filter

    # Remove any handlers added by earlier basicConfig calls
    for h in list(root.handlers):
        root.removeHandler(h)

    # ── File handler (JSON lines, DEBUG, rotating 10 MB × 5 files) ───────────
    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,   # 10 MB per file
        backupCount=5,                # keep 5 rotated files
        encoding="utf-8",
    )
    fh.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))
    fh.setFormatter(JsonLineFormatter())
    fh.addFilter(SensitiveDataFilter())
    root.addHandler(fh)

    # ── Console handler (human-readable, INFO) ────────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    ch.setFormatter(ConsoleFormatter())
    ch.addFilter(SensitiveDataFilter())
    root.addHandler(ch)

    # ── Suppress noisy third-party loggers ────────────────────────────────────
    if suppress_noisy_loggers:
        for noisy in (
            "paramiko",
            "paramiko.transport",
            "mcp",
            "mcp.client",
            "mcp.server",
            "asyncio",
            "urllib3",
            "urllib3.connectionpool",
            "httpx",
            "httpcore",
            "beeai_framework",
        ):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    return str(log_file.resolve())


# ── AgentTracker ──────────────────────────────────────────────────────────────

class AgentTracker:
    """
    Emit structured console + log events for one agent role.

    Each method prints a clean line to the console (at INFO) and emits a
    structured JSON record to the log file (at DEBUG or INFO).

    Args:
        agent_name: Role name, e.g. "DiscoveryAgent", "Orchestrator"
        resource:   Optional target host/resource label shown in output

    Example::

        tracker = AgentTracker("DiscoveryAgent", resource="192.168.1.100")
        tracker.start("Scanning workloads")
        with tracker.phase("discovery", "Port scanning"):
            ...
        tracker.thinking("Found MongoDB on port 27017")
        tracker.decision("Detected MongoDB", confidence=0.9)
        tracker.finish("Discovery complete")
    """

    def __init__(self, agent_name: str, resource: str = ""):
        self._name = agent_name
        self._resource = resource
        self._icon, self._display = _role_display(agent_name)
        self._logger = logging.getLogger(f"agent.{agent_name.lower()}")

    # ── Banner helpers ────────────────────────────────────────────────────────

    def _header(self) -> str:
        res = f"  [{self._resource}]" if self._resource else ""
        return _c(f"  {self._icon} {self._display}{res}", _BOLD)

    def _log(
        self,
        level: int,
        message: str,
        event: str = "",
        phase: str = "",
        **extra: Any,
    ) -> None:
        self._logger.log(
            level,
            message,
            extra={
                "agent": self._name,
                "host":  self._resource,
                "event": event,
                "phase": phase,
                **extra,
            },
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, message: str) -> None:
        """Print agent banner and log workflow start."""
        print(f"\n{self._header()}")
        self._log(logging.INFO, message, event="start")

    def finish(self, message: str, success: bool = True) -> None:
        """Log workflow completion."""
        icon = "✅" if success else "❌"
        print(f"     {icon} {message}")
        self._log(logging.INFO, message, event="finish", success=success)

    def info(self, message: str, phase: str = "") -> None:
        """Log an informational message."""
        print(f"     ℹ️  {message}")
        self._log(logging.INFO, message, event="info", phase=phase)

    def thinking(self, message: str, phase: str = "") -> None:
        """Log an agent reasoning step (shown dimmed on console)."""
        print(f"     {_c('💭 ' + message, _DIM)}")
        self._log(logging.DEBUG, message, event="thinking", phase=phase)

    def decision(self, message: str, confidence: float = 1.0, phase: str = "") -> None:
        """Log a decision or conclusion."""
        print(f"     ✅ {message}")
        self._log(
            logging.INFO, message, event="decision",
            phase=phase, confidence=confidence,
        )

    def warning(self, message: str, phase: str = "") -> None:
        """Log a warning."""
        print(f"     {_c('⚠️  ' + message, _YELLOW)}")
        self._log(logging.WARNING, message, event="warning", phase=phase)

    def error(self, message: str, exc: Optional[Exception] = None, phase: str = "") -> None:
        """Log an error, optionally with exception details."""
        print(f"     {_c('❌ ' + message, _RED)}")
        if exc and logging.getLogger().isEnabledFor(logging.DEBUG):
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            self._log(logging.ERROR, message, event="error", phase=phase, traceback=tb)
        else:
            self._log(logging.ERROR, message, event="error", phase=phase)

    def tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        phase: str = "execution",
    ) -> None:
        """Log an MCP tool call (shown dimmed on console; args go to log file only)."""
        print(f"     {_c('⚙️  ' + tool_name, _DIM)}")
        self._log(
            logging.DEBUG,
            f"Tool call: {tool_name}",
            event="tool_call",
            phase=phase,
            tool=tool_name,
            tool_args=tool_args,   # renamed: 'args' is a reserved LogRecord attribute
        )

    def tool_result(
        self,
        tool_name: str,
        result: Any,
        success: bool = True,
        summary: str = "",
        phase: str = "execution",
    ) -> None:
        """Log an MCP tool result with a one-line console summary."""
        msg = summary or (f"✅ {tool_name}" if success else f"❌ {tool_name}")
        print(f"     {msg}")
        self._log(
            logging.INFO if success else logging.WARNING,
            summary or tool_name,
            event="tool_result",
            phase=phase,
            tool=tool_name,
            success=success,
        )

    def mode(self, phase: str, description: str = "") -> None:
        """
        Print a phase-change banner.

        Used by the orchestrator to announce which agent is now active.
        """
        icon, display = _role_display(phase)
        res = f"  [{self._resource}]" if self._resource else ""
        print(f"\n  {_c(icon + ' ' + display + res, _BOLD, _CYAN)}")
        if description:
            print(f"     {_c(description, _DIM)}")
        self._log(logging.INFO, description or phase, event="phase_start", phase=phase)

    @contextmanager
    def phase(self, phase_name: str, description: str = "") -> Generator[None, None, None]:
        """
        Context manager that logs phase start and end.

        Usage::

            with tracker.phase("initialization", "Loading LLM and MCP tools"):
                await orchestrator.initialize()
        """
        self._log(logging.INFO, description or phase_name, event="phase_start", phase=phase_name)
        try:
            yield
        except Exception as exc:
            self._log(
                logging.ERROR,
                f"Phase '{phase_name}' failed: {exc}",
                event="phase_error",
                phase=phase_name,
            )
            raise
        else:
            self._log(logging.INFO, f"Phase '{phase_name}' complete", event="phase_end", phase=phase_name)


# ── WorkflowProgressDisplay ───────────────────────────────────────────────────

class WorkflowProgressDisplay:
    """
    Live phase-progress table for a single VM validation workflow.

    Prints a simple status table that is updated as each phase completes.
    Does not use curses or ANSI cursor movement — just sequential prints,
    which work correctly in all terminals and CI environments.

    Example output::

        ┌──────────────┬──────────┬──────────┬────────────────────┐
        │  Phase       │  Status  │  Time    │  Detail            │
        ├──────────────┼──────────┼──────────┼────────────────────┤
        │  Discovery   │  ✅ done │  4.2s    │  MongoDB found     │
        │  Planning    │  ✅ done │  0.1s    │  5 checks          │
        │  Validation  │  ⚙️  run  │  ...     │                    │
        │  Evaluation  │  ⏳ wait │          │                    │
        └──────────────┴──────────┴──────────┴────────────────────┘

    Args:
        host: Target host label shown in the header
    """

    _PHASES = ["discovery", "planning", "validation", "evaluation"]

    _STATUS_ICONS = {
        "running": "⚙️  run ",
        "done":    "✅ done",
        "failed":  "❌ fail",
        "warning": "⚠️  warn",
        "skipped": "⏭️  skip",
        "waiting": "⏳ wait",
        "error":   "🔴 err ",
    }

    def __init__(self, host: str):
        self._host = host
        self._phases: Dict[str, Dict[str, str]] = {
            p: {"status": "waiting", "time": "", "detail": ""}
            for p in self._PHASES
        }

    def start_workflow(self) -> None:
        """Print the workflow header."""
        print(f"\n  {'─'*63}")
        print(f"  🐝 BeeAI Validation — {_c(self._host, _BOLD)}")
        print(f"  {'─'*63}")

    def update_phase(self, phase: str, status: str, detail: str = "") -> None:
        """
        Update a phase's status and optionally print a progress line.

        Args:
            phase:  One of: discovery, planning, validation, evaluation
            status: One of: running, done, failed, warning, skipped, waiting, error
            detail: Short detail string (e.g. "4.2s", "MongoDB found")
        """
        if phase in self._phases:
            self._phases[phase]["status"] = status
            if detail:
                if status == "done" and detail.endswith("s") and detail[:-1].replace(".", "").isdigit():
                    self._phases[phase]["time"] = detail
                else:
                    self._phases[phase]["detail"] = detail

        icon = self._STATUS_ICONS.get(status, "❓")
        phase_label = phase.capitalize().ljust(12)
        detail_str = f"  {detail}" if detail else ""
        print(f"     {phase_label}  {icon}{detail_str}")

    def finish_workflow(
        self,
        status: str,
        score: int = 0,
        elapsed: float = 0.0,
    ) -> None:
        """
        Print the workflow completion summary.

        Args:
            status:  "success" | "partial_success" | "failure"
            score:   Validation score 0-100
            elapsed: Total elapsed seconds
        """
        print(f"\n  {'─'*63}")

        if status == "success":
            colour = _GREEN
            icon = "✅"
            label = "PASSED"
        elif status == "partial_success":
            colour = _YELLOW
            icon = "⚠️ "
            label = "PARTIAL"
        else:
            colour = _RED
            icon = "❌"
            label = "FAILED"

        bar_len = 20
        filled = int(bar_len * score / 100)
        bar = _c("█" * filled, colour) + _c("░" * (bar_len - filled), _GREY)

        print(f"  {icon} {_c(label, colour, _BOLD)}  {bar}  {score}/100  ({elapsed:.1f}s)")
        print(f"  {'─'*63}\n")

# Made with Bob
