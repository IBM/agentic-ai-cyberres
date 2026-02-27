#
# Copyright contributors to the agentic-ai-cyberres project
#
"""
Agent Logger - Structured dual-stream logging for BeeAI validation agents.

Provides:
- Console stream: Clean, human-readable agent activity (what the user sees)
- File stream: Full structured logs with timestamps, levels, context (system logs)
- AgentTracker: Tracks which agent is active and what decisions it's making
- Decision logging: Records agent reasoning and tool calls

Usage:
    from agent_logging.agent_logger import setup_logging, get_agent_logger, AgentTracker

    # Setup once at startup
    setup_logging(log_dir="logs", log_level="DEBUG")

    # In each agent
    logger = get_agent_logger("DiscoveryAgent")
    tracker = AgentTracker("DiscoveryAgent")

    with tracker.phase("port_scan"):
        tracker.decision("Scanning ports 22, 80, 443, 1521, 27017")
        tracker.tool_call("scan_ports", {"host": "192.168.1.100"})
        tracker.tool_result("scan_ports", {"open_ports": [22, 80]})
"""

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# ANSI colour codes for console output
# ─────────────────────────────────────────────
class Colours:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

    # Agents
    BLUE    = "\033[34m"
    CYAN    = "\033[36m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    RED     = "\033[31m"
    MAGENTA = "\033[35m"
    WHITE   = "\033[37m"

    # Backgrounds
    BG_BLUE  = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_RED   = "\033[41m"

    @staticmethod
    def strip(text: str) -> str:
        """Remove ANSI codes from text."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)


# Agent colour map – each agent gets a distinct colour
AGENT_COLOURS = {
    "Orchestrator":      Colours.MAGENTA,
    "DiscoveryAgent":    Colours.CYAN,
    "ValidationAgent":   Colours.BLUE,
    "EvaluationAgent":   Colours.GREEN,
    "BatchOrchestrator": Colours.YELLOW,
    "CredentialResolver": Colours.WHITE,
    "default":           Colours.WHITE,
}

# Phase icons
PHASE_ICONS = {
    "discovery":   "🔍",
    "planning":    "📋",
    "validation":  "✅",
    "evaluation":  "🎯",
    "reporting":   "📊",
    "credentials": "🔑",
    "batch":       "⚡",
    "cleanup":     "🧹",
    "default":     "▶",
}

# Status icons
STATUS_ICONS = {
    "start":    "▶",
    "success":  "✅",
    "warning":  "⚠️ ",
    "error":    "❌",
    "info":     "ℹ️ ",
    "decision": "💭",
    "tool":     "🔧",
    "result":   "📤",
    "skip":     "⏭️ ",
    "llm":      "🤖",
    "det":      "⚙️ ",
    "thinking": "💭",
    "step":     "→",
}

# Agent role names shown in console output (no implementation details exposed)
AGENT_ROLES = {
    "discovery":   ("🔍", "Discovery Agent"),
    "planning":    ("📋", "Planning Agent"),
    "validation":  ("✅", "Validation Agent"),
    "evaluation":  ("🎯", "Evaluation Agent"),
    "reporting":   ("📊", "Reporting Agent"),
    "credentials": ("🔑", "Credential Agent"),
    "batch":       ("⚡", "Batch Agent"),
}


# ─────────────────────────────────────────────
# Console formatter – clean, coloured output
# ─────────────────────────────────────────────
class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter.

    Shows:  [AGENT] icon  message
    Hides:  timestamps, module paths, stack traces (those go to file)
    """

    LEVEL_STYLES = {
        logging.DEBUG:    (Colours.DIM,    ""),
        logging.INFO:     (Colours.RESET,  ""),
        logging.WARNING:  (Colours.YELLOW, "⚠️  "),
        logging.ERROR:    (Colours.RED,    "❌ "),
        logging.CRITICAL: (Colours.RED + Colours.BOLD, "🔴 "),
    }

    def format(self, record: logging.LogRecord) -> str:
        colour, prefix = self.LEVEL_STYLES.get(record.levelno, (Colours.RESET, ""))

        # Agent tag
        agent = getattr(record, "agent", None)
        if agent:
            agent_colour = AGENT_COLOURS.get(agent, AGENT_COLOURS["default"])
            agent_tag = f"{agent_colour}[{agent}]{Colours.RESET} "
        else:
            agent_tag = ""

        # Phase tag
        phase = getattr(record, "phase", None)
        if phase:
            icon = PHASE_ICONS.get(phase, PHASE_ICONS["default"])
            phase_tag = f"{Colours.DIM}{icon} {phase}{Colours.RESET}  "
        else:
            phase_tag = ""

        msg = record.getMessage()
        return f"{agent_tag}{phase_tag}{colour}{prefix}{msg}{Colours.RESET}"


# ─────────────────────────────────────────────
# File formatter – structured JSON lines
# ─────────────────────────────────────────────
class FileFormatter(logging.Formatter):
    """
    Structured JSON-lines formatter for log files.

    Each line is a valid JSON object with full context.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts":      datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
            "module":  record.module,
            "line":    record.lineno,
        }

        # Add extra fields from LogRecord
        for field in ("agent", "phase", "tool", "decision", "resource", "batch_id"):
            val = getattr(record, field, None)
            if val is not None:
                entry[field] = val

        # Add exception info
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


# ─────────────────────────────────────────────
# Global setup
# ─────────────────────────────────────────────
_logging_configured = False
_log_file_path: Optional[Path] = None


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "DEBUG",
    console_level: str = "INFO",
    log_file_prefix: str = "beeai",
    suppress_noisy_loggers: bool = True,
) -> Path:
    """
    Configure dual-stream logging: console (clean) + file (structured JSON).

    Args:
        log_dir: Directory for log files
        log_level: File log level (DEBUG, INFO, WARNING, ERROR)
        console_level: Console log level (INFO recommended)
        log_file_prefix: Prefix for log file names
        suppress_noisy_loggers: Suppress MCP/paramiko/httpx noise on console

    Returns:
        Path to the log file
    """
    global _logging_configured, _log_file_path

    if _logging_configured:
        return _log_file_path  # type: ignore[return-value]

    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{log_file_prefix}_{timestamp}.log"
    _log_file_path = log_file

    # ── Root logger ──────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # Capture everything; handlers filter

    # Remove any existing handlers
    root.handlers.clear()

    # ── File handler (JSON lines, full detail) ───────────────────────────────
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))
    fh.setFormatter(FileFormatter())
    root.addHandler(fh)

    # ── Console handler (clean, coloured) ────────────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    ch.setFormatter(ConsoleFormatter())
    root.addHandler(ch)

    # ── Suppress noisy third-party loggers on console ────────────────────────
    # Strategy: set propagate=False so they DON'T reach the root console handler.
    # Add a dedicated file-only handler so their logs still go to the log file.
    if suppress_noisy_loggers:
        noisy = [
            "mcp", "mcp.server", "mcp.server.lowlevel", "mcp.server.lowlevel.server",
            "paramiko", "paramiko.transport",
            "httpx", "httpcore", "urllib3",
            "asyncio",
        ]
        for name in noisy:
            lg = logging.getLogger(name)
            lg.setLevel(logging.DEBUG)
            # File-only handler — full detail goes to log file
            noisy_fh = logging.FileHandler(log_file, encoding="utf-8")
            noisy_fh.setLevel(logging.DEBUG)
            noisy_fh.setFormatter(FileFormatter())
            lg.addHandler(noisy_fh)
            # CRITICAL: don't propagate to root (which has the console handler)
            lg.propagate = False

    _logging_configured = True

    # First log entry
    startup_logger = logging.getLogger("startup")
    startup_logger.info(
        f"Logging initialised — file: {log_file}",
        extra={"agent": "System"}
    )

    return log_file


def get_agent_logger(agent_name: str) -> logging.Logger:
    """
    Get a logger pre-configured for a specific agent.

    Args:
        agent_name: Name of the agent (e.g. "DiscoveryAgent")

    Returns:
        Logger with agent context
    """
    return logging.getLogger(f"agents.{agent_name}")


def get_log_file() -> Optional[Path]:
    """Return the current log file path."""
    return _log_file_path


# ─────────────────────────────────────────────
# AgentTracker – tracks agent decisions
# ─────────────────────────────────────────────
class AgentTracker:
    """
    Tracks agent activity with a modern "thinking steps" display style.

    Inspired by ChatGPT / Claude agent UIs:
    - Phase headers show which agent is active and what mode (LLM vs rule-based)
    - Tool calls shown as "Using: <tool>" with masked args
    - Results shown inline with ✅/⚠️/❌ and a one-line summary
    - Step numbers show progress through the plan
    - Thinking/reasoning shown as indented italic-style text

    Console output is clean and human-readable.
    File output is structured JSON for analysis.
    """

    # Width of the separator line
    _WIDTH = 60

    def __init__(self, agent_name: str, resource: Optional[str] = None):
        self.agent_name = agent_name
        self.resource = resource
        self.logger = get_agent_logger(agent_name)
        self._current_phase: Optional[str] = None
        self._phase_start: float = 0.0
        self._decisions: List[str] = []
        self._tool_calls: List[Dict[str, Any]] = []
        self._phase_stack: List[str] = []

    # ── internal helpers ──────────────────────────────────────────────────────

    def _extra(self, **kwargs) -> Dict[str, Any]:
        extra: Dict[str, Any] = {"agent": self.agent_name}
        if self._current_phase:
            extra["phase"] = self._current_phase
        if self.resource:
            extra["resource"] = self.resource
        extra.update(kwargs)
        return extra

    def _agent_badge(self, phase: Optional[str] = None) -> str:
        """Return a coloured agent badge, optionally with phase role tag."""
        colour = AGENT_COLOURS.get(self.agent_name, AGENT_COLOURS["default"])
        badge = f"{colour}{Colours.BOLD}[{self.agent_name}]{Colours.RESET}"
        if phase and phase in AGENT_ROLES:
            icon, role = AGENT_ROLES[phase]
            badge += f" {Colours.DIM}{icon} {role}{Colours.RESET}"
        return badge

    # ── public API ────────────────────────────────────────────────────────────

    def start(self, message: str = ""):
        """Print a workflow start banner."""
        msg = message or f"Starting {self.agent_name}"
        resource_str = f"  📍 {self.resource}" if self.resource else ""
        self.logger.info(
            f"\n{'═' * self._WIDTH}\n"
            f"  {self._agent_badge()}\n"
            f"  {msg}"
            f"{resource_str}\n"
            f"{'─' * self._WIDTH}",
            extra=self._extra()
        )

    def finish(self, message: str = "", success: bool = True):
        """Print a workflow completion line."""
        icon = "✅" if success else "❌"
        msg = message or f"{self.agent_name} complete"
        self.logger.info(
            f"{'─' * self._WIDTH}\n"
            f"  {icon} {msg}\n"
            f"{'═' * self._WIDTH}",
            extra=self._extra()
        )

    @contextmanager
    def phase(self, phase_name: str, description: str = ""):
        """Context manager for a named workflow phase."""
        self._phase_stack.append(phase_name)
        self._current_phase = phase_name
        self._phase_start = time.time()

        icon = PHASE_ICONS.get(phase_name, PHASE_ICONS["default"])
        desc = f"  {Colours.DIM}{description}{Colours.RESET}" if description else ""
        self.logger.info(
            f"\n  {icon} {Colours.BOLD}{phase_name.upper()}{Colours.RESET}{desc}",
            extra=self._extra()
        )

        try:
            yield self
            elapsed = time.time() - self._phase_start
            self.logger.info(
                f"  {'─'*40}  ✅ done ({elapsed:.1f}s)",
                extra=self._extra()
            )
        except Exception as e:
            elapsed = time.time() - self._phase_start
            self.logger.error(
                f"  {'─'*40}  ❌ failed ({elapsed:.1f}s): {e}",
                extra=self._extra()
            )
            raise
        finally:
            self._phase_stack.pop()
            self._current_phase = self._phase_stack[-1] if self._phase_stack else None

    def mode(self, phase: str, description: str = ""):
        """
        Print a clean agent-role banner at the start of each phase.

        Shows the agent's role and what it's doing — no implementation details.
        Inspired by how ChatGPT/Claude show agent steps without exposing internals.

        Args:
            phase: Phase key (e.g. "discovery", "planning", "validation", "evaluation")
            description: One-line description of what this phase does
        """
        if phase in AGENT_ROLES:
            icon, role = AGENT_ROLES[phase]
            badge = f"{Colours.CYAN}{icon}  {Colours.BOLD}{role}{Colours.RESET}"
        else:
            badge = f"{Colours.CYAN}▶  {Colours.BOLD}{phase.capitalize()}{Colours.RESET}"

        desc_line = (
            f"\n     {Colours.DIM}↳ {description}{Colours.RESET}"
            if description else ""
        )
        self.logger.info(
            f"\n  ┌─ {badge}{desc_line}\n  └{'─'*50}",
            extra=self._extra(decision=f"phase={phase}")
        )

    def thinking(self, thought: str):
        """
        Show an LLM 'thinking' step — displayed like ChatGPT's reasoning bubble.

        Args:
            thought: What the LLM is considering
        """
        self.logger.info(
            f"  {Colours.DIM}💭 Thinking: {thought}{Colours.RESET}",
            extra=self._extra(decision=thought)
        )

    def decision(self, reasoning: str, confidence: Optional[float] = None):
        """
        Log an agent decision — shown as an indented conclusion after thinking.

        Args:
            reasoning: What the agent decided
            confidence: Optional confidence level (0.0-1.0)
        """
        self._decisions.append(reasoning)
        conf_str = (
            f"  {Colours.DIM}({confidence:.0%} confidence){Colours.RESET}"
            if confidence is not None else ""
        )
        self.logger.info(
            f"  {Colours.GREEN}✓{Colours.RESET} {reasoning}{conf_str}",
            extra=self._extra(decision=reasoning)
        )

    def tool_call(self, tool_name: str, args: Dict[str, Any]):
        """
        Show a tool invocation in the style of modern agent UIs:
          > Using: db_mongo_ssh_ping  host=9.11.68.67  user=vikas

        Args:
            tool_name: MCP tool name
            args: Tool arguments (passwords masked)
        """
        safe_args = self._mask_sensitive(args)
        self._tool_calls.append({"tool": tool_name, "args": safe_args})

        # Build a compact one-line arg summary (key=value, skip None)
        arg_parts = [
            f"{k}={v}" for k, v in safe_args.items()
            if v is not None and k not in ("ssh_key_path",)
        ]
        arg_str = "  " + "  ".join(arg_parts[:4]) if arg_parts else ""

        self.logger.info(
            f"  {Colours.CYAN}▶ Using:{Colours.RESET} "
            f"{Colours.BOLD}{tool_name}{Colours.RESET}"
            f"{Colours.DIM}{arg_str}{Colours.RESET}",
            extra=self._extra(tool=tool_name)
        )
        self.logger.debug(
            f"     Full args: {json.dumps(safe_args, default=str)}",
            extra=self._extra(tool=tool_name)
        )

    def tool_result(
        self,
        tool_name: str,
        result: Any,
        success: bool = True,
        summary: Optional[str] = None,
    ):
        """
        Show a tool result inline — right after the tool_call line.

        Format:
          ✅  db_mongo_ssh_ping  →  MongoDB 7.0.1 reachable via ssh_mongo_shell
          ❌  vm_linux_services  →  Required service(s) not running: mongod.service

        Args:
            tool_name: MCP tool name
            result: Raw result dict
            success: Whether the call succeeded
            summary: Human-readable one-line summary (preferred over raw result)
        """
        if success:
            icon   = "✅"
            colour = Colours.GREEN
        else:
            icon   = "❌"
            colour = Colours.RED

        if summary:
            # Strip leading check-number prefix if present (e.g. "[1/7] Name — ✅ PASS: ...")
            # so we don't double-print the icon
            display = summary
        elif isinstance(result, dict):
            keys = list(result.keys())[:3]
            display = f"{{{', '.join(keys)}{'...' if len(result) > 3 else ''}}}"
        elif isinstance(result, list):
            display = f"[{len(result)} items]"
        elif isinstance(result, str) and len(result) > 120:
            display = result[:117] + "..."
        else:
            display = str(result)

        self.logger.info(
            f"  {colour}{icon}{Colours.RESET}  "
            f"{Colours.DIM}{tool_name}{Colours.RESET}  "
            f"{Colours.RESET}→  {display}",
            extra=self._extra(tool=tool_name)
        )
        self.logger.debug(
            f"     Full result: {json.dumps(result, default=str)[:500]}",
            extra=self._extra(tool=tool_name)
        )

    def info(self, message: str):
        """Log an informational message."""
        self.logger.info(
            f"  {Colours.DIM}ℹ  {message}{Colours.RESET}",
            extra=self._extra()
        )

    def warning(self, message: str):
        """Log a warning."""
        self.logger.warning(
            f"  ⚠️  {message}",
            extra=self._extra()
        )

    def error(self, message: str, exc: Optional[Exception] = None):
        """Log an error."""
        self.logger.error(
            f"  ❌ {message}",
            extra=self._extra(),
            exc_info=exc is not None
        )

    def skip(self, reason: str):
        """Log a skipped step."""
        self.logger.info(
            f"  {Colours.DIM}⏭  Skipped: {reason}{Colours.RESET}",
            extra=self._extra()
        )

    def summary(self) -> Dict[str, Any]:
        """Return a summary of tracked activity."""
        return {
            "agent": self.agent_name,
            "resource": self.resource,
            "decisions_made": len(self._decisions),
            "tool_calls": len(self._tool_calls),
            "decisions": self._decisions,
            "tools_used": [t["tool"] for t in self._tool_calls],
        }

    @staticmethod
    def _mask_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in a dictionary."""
        SENSITIVE_KEYS = {
            "password", "passwd", "secret", "token", "key",
            "api_key", "private_key", "ssh_password", "db_password",
        }
        if not isinstance(data, dict):
            return data

        masked = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                masked[k] = "***"
            elif isinstance(v, dict):
                masked[k] = AgentTracker._mask_sensitive(v)
            else:
                masked[k] = v
        return masked


# ─────────────────────────────────────────────
# Workflow progress display
# ─────────────────────────────────────────────
class WorkflowProgressDisplay:
    """
    Displays a clean workflow progress summary on the console.

    Shows the current state of a multi-phase validation workflow
    in a way that's easy to follow.
    """

    PHASES = ["discovery", "planning", "validation", "evaluation", "reporting"]

    def __init__(self, resource: str):
        self.resource = resource
        self.phase_status: Dict[str, str] = {}  # phase -> "pending"|"running"|"done"|"failed"|"skipped"
        self.logger = logging.getLogger("workflow.progress")

    def start_workflow(self):
        """Display workflow start banner."""
        print(f"\n{'═'*60}")
        print(f"  🚀 BeeAI Validation Workflow")
        print(f"  📍 Resource: {self.resource}")
        print(f"  🕐 Started: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'═'*60}")

    def update_phase(self, phase: str, status: str, detail: str = ""):
        """
        Update phase status.

        Args:
            phase: Phase name
            status: "running" | "done" | "failed" | "skipped"
            detail: Optional detail message
        """
        self.phase_status[phase] = status

        icons = {
            "running": f"{Colours.CYAN}⟳{Colours.RESET}",
            "done":    f"{Colours.GREEN}✓{Colours.RESET}",
            "failed":  f"{Colours.RED}✗{Colours.RESET}",
            "skipped": f"{Colours.DIM}−{Colours.RESET}",
            "pending": f"{Colours.DIM}○{Colours.RESET}",
        }
        icon = icons.get(status, "?")
        detail_str = f"  {Colours.DIM}{detail}{Colours.RESET}" if detail else ""
        print(f"  {icon} {phase.capitalize():<15}{detail_str}")

    def finish_workflow(self, status: str, score: Optional[int] = None, elapsed: float = 0):
        """Display workflow completion summary."""
        print(f"\n{'─'*60}")
        if status == "success":
            print(f"  ✅ Validation COMPLETE")
        elif status == "partial_success":
            print(f"  ⚠️  Validation PARTIAL")
        else:
            print(f"  ❌ Validation FAILED")

        if score is not None:
            bar_len = 30
            filled = int(bar_len * score / 100)
            bar_colour = Colours.GREEN if score >= 80 else (Colours.YELLOW if score >= 50 else Colours.RED)
            bar = f"{bar_colour}{'█' * filled}{'░' * (bar_len - filled)}{Colours.RESET}"
            print(f"  📊 Score: {bar} {score}/100")

        print(f"  ⏱  Elapsed: {elapsed:.1f}s")
        print(f"{'═'*60}\n")

# Made with Bob
