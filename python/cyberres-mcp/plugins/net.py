"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""Network-related validation tools.

This module defines a simple TCP port checker that attempts to
establish a connection to one or more ports on a given host. It is
designed to be lightweight and non-invasive, returning latency
measurements and whether each port was reachable. Failures are
reported with error messages from the underlying socket operation.
"""

from typing import List, Dict, Any
import logging
import socket
import time


def attach(mcp):
    """Register network tools onto the given FastMCP instance."""
    logger = logging.getLogger("mcp.net")
    try:
        from .utils import ok as resp_ok, err as resp_err
    except Exception:
        from plugins.utils import ok as resp_ok, err as resp_err  # type: ignore

    @mcp.tool()
    def tcp_portcheck(host: str, ports: List[int], timeout_s: float = 1.0) -> Dict[str, Any]:
        """Selective TCP connectivity check.

        Attempts to connect to each port in ``ports`` on the specified
        ``host``. Reports the latency of each connection attempt and
        whether it succeeded. A failure includes the exception message
        encountered.

        Parameters
        ----------
        host : str
            Hostname or IP address to probe.
        ports : List[int]
            List of integer port numbers to attempt connections to.
        timeout_s : float, optional
            Timeout in seconds for each connection attempt.

        Returns
        -------
        dict
            A dictionary containing the host, per-port results, and a
            boolean summarizing whether all ports were reachable.
        """
        results = []
        for port in ports:
            start = time.time()
            port_ok = False
            error = None
            try:
                with socket.create_connection((host, port), timeout=timeout_s):
                    port_ok = True
            except Exception as e:
                error = str(e)
            latency_ms = (time.time() - start) * 1000.0
            results.append({
                "port": port,
                "ok": port_ok,
                "latency_ms": round(latency_ms, 2),
                "error": error,
            })
        all_ok = all(r["ok"] for r in results)
        if not all_ok:
            logger.info("tcp_portcheck failures", extra={"host": host, "failed_ports": [r["port"] for r in results if not r["ok"]]})
        return resp_ok({
            "host": host,
            "results": results,
            "all_ok": all_ok,
        })