"""
Copyright contributors to the agentic-ai-cyberres project
"""

from __future__ import annotations
from typing import Any, Dict, Optional


def ok(data: Optional[Dict[str, Any]] = None, **extra: Any) -> Dict[str, Any]:
    resp: Dict[str, Any] = {"ok": True}
    if data:
        resp.update(data)
    if extra:
        resp.update(extra)
    return resp


def err(message: str, *, code: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    resp: Dict[str, Any] = {"ok": False, "error": {"message": message}}
    if code:
        resp["error"]["code"] = code
    if extra:
        resp.update(extra)
    return resp
