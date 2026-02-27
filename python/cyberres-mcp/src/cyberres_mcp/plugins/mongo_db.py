"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""MongoDB validation tools.

All Mongo tools use SSH to execute local Mongo shell commands on the
target VM. This supports recovery validation scenarios where MongoDB
is only locally reachable after restore/failover.
"""

from typing import Dict, Any, Optional, Tuple, List
import json
import logging
import re
import shlex

# Use unified SSH utilities
from .ssh_utils import ssh_exec as _ssh_exec_impl


def run_ssh_command(
    host: str,
    username: str,
    password: Optional[str] = None,
    key_path: Optional[str] = None,
    command: str = "",
    port: int = 22,
    timeout: float = 10.0,
    stdin_data: Optional[str] = None,
) -> Tuple[int, str, str]:
    """
    Execute SSH command and return (return_code, stdout, stderr).

    This is a backward-compatible wrapper around ssh_utils.ssh_exec.
    """
    return _ssh_exec_impl(
        host,
        username,
        command,
        password,
        key_path,
        port,
        timeout,
        stdin_data=stdin_data,
    )


def _json_from_stdout(stdout: str):
    """Return the last valid JSON object/array found in stdout."""
    lines = [l.strip() for l in stdout.splitlines() if l.strip()]
    for line in reversed(lines):
        if line.startswith("{") or line.startswith("["):
            try:
                return json.loads(line)
            except Exception:
                continue
    return None


def _js_quote(s: str) -> str:
    # Escape for single-quoted JS string literals.
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _looks_like_auth_error(data: Any, stderr: str, stdout: str) -> bool:
    combined = f"{stderr}\n{stdout}".lower()
    if any(
        token in combined
        for token in [
            "requires authentication",
            "authentication failed",
            "not authorized",
            "unauthorized",
            "auth failed",
        ]
    ):
        return True
    if isinstance(data, dict):
        code_name = str(data.get("codeName", "")).lower()
        errmsg = str(data.get("errmsg", "")).lower()
        if code_name in {"unauthorized", "authenticationfailed"}:
            return True
        if "requires authentication" in errmsg or "not authorized" in errmsg:
            return True
    return False


def _build_ssh_mongo_error_message(stderr: str, stdout: str = "") -> str:
    combined = f"{stderr}\n{stdout}".strip()
    lower = combined.lower()
    if "mongosh: command not found" in lower or "mongo: command not found" in lower:
        return (
            "SSH succeeded but Mongo shell was not found (mongosh/mongo). "
            "Install mongosh or ensure PATH is configured for the SSH user."
        )
    if "no space left on device" in lower:
        return (
            "SSH succeeded but remote filesystem is full (No space left on device). "
            "Free space on the target and retry."
        )
    if _looks_like_auth_error(None, stderr, stdout):
        return (
            "Mongo shell query failed due to authentication. "
            "Provide mongo credentials in the credential entry (mongo.username/mongo.password), "
            "or configure local trusted auth for the SSH user."
        )
    return "SSH connection succeeded, but Mongo shell query failed."


def _classify_mongo_shell_error(stderr: str, stdout: str = "") -> Tuple[str, str]:
    combined = f"{stderr}\n{stdout}"
    lower = combined.lower()
    if "not running with --replset" in lower:
        return (
            "MONGO_NOT_REPLSET",
            "MongoDB is running in standalone mode (not started with --replSet), so rs.status() is not applicable.",
        )
    if "no replset config has been received" in lower:
        return (
            "MONGO_REPLSET_UNINITIALIZED",
            "MongoDB is replSet-enabled but not initialized yet (no replica-set config).",
        )
    if _looks_like_auth_error(None, stderr, stdout):
        return (
            "MONGO_AUTH_ERROR",
            "Mongo shell query failed due to authentication. "
            "Provide mongo credentials in credential_id (mongo.username/mongo.password).",
        )
    return "MONGO_ERROR", _build_ssh_mongo_error_message(stderr, stdout)


def attach(mcp):
    """Register MongoDB tools onto the FastMCP instance."""
    logger = logging.getLogger("mcp.mongo")
    try:
        from .utils import ok, err, resolve_ssh_auth, resolve_scoped_auth
    except Exception:
        # fallback if relative import differs when packaged
        from plugins.utils import ok, err, resolve_ssh_auth, resolve_scoped_auth  # type: ignore

    def _resolve_ssh_auth_inputs(
        ssh_user: str,
        ssh_password: Optional[str],
        ssh_key_path: Optional[str],
        credential_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        resolved_user, resolved_password, resolved_key_path, auth_err = resolve_ssh_auth(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
            logger=logger,
        )
        return (
            resolved_user or ssh_user,
            resolved_password,
            resolved_key_path,
            auth_err,
        )

    def _resolve_optional_mongo_auth(
        credential_id: Optional[str],
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        mongo_user, mongo_password, mongo_err = resolve_scoped_auth(
            username=None,
            password=None,
            credential_id=credential_id,
            scope_name="mongo",
            user_keys=["username", "user", "mongo_user"],
            password_keys=["password", "mongo_password"],
            logger=logger,
        )
        if mongo_err and mongo_user:
            return mongo_user, mongo_password, mongo_err
        return mongo_user, mongo_password, None

    def _discover_mongo_runtime_details(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str],
        ssh_key_path: Optional[str],
    ) -> Dict[str, Any]:
        # 1) Detect shell binary
        shell_cmd = (
            "if command -v mongosh >/dev/null 2>&1; then echo mongosh; "
            "elif command -v mongo >/dev/null 2>&1; then echo mongo; "
            "else echo none; fi"
        )
        shell_rc, shell_out, shell_err = run_ssh_command(
            host=ssh_host,
            username=ssh_user,
            password=ssh_password,
            key_path=ssh_key_path,
            command=shell_cmd,
        )
        shell_bin = (shell_out.strip().splitlines()[0].strip() if shell_out.strip() else "none")

        # 2) Discover mongod process args
        _, ps_out, _ = run_ssh_command(
            host=ssh_host,
            username=ssh_user,
            password=ssh_password,
            key_path=ssh_key_path,
            command="ps -eo args | awk '/[m]ongod/ {print; exit}' || true",
        )
        mongod_cmdline = ps_out.strip().splitlines()[0].strip() if ps_out.strip() else ""

        port: Optional[int] = None
        replset_name: Optional[str] = None

        if mongod_cmdline:
            m_port = re.search(r"--port(?:=|\s+)(\d+)", mongod_cmdline)
            if m_port:
                try:
                    port = int(m_port.group(1))
                except Exception:
                    port = None
            m_repl = re.search(r"--replSet(?:=|\s+)([^\s]+)", mongod_cmdline)
            if m_repl:
                replset_name = m_repl.group(1).strip()

        # 3) Fallback to config file parse
        if port is None or not replset_name:
            _, cfg_out, _ = run_ssh_command(
                host=ssh_host,
                username=ssh_user,
                password=ssh_password,
                key_path=ssh_key_path,
                command=(
                    "cat /etc/mongod.conf /etc/mongodb.conf "
                    "/usr/local/etc/mongod.conf 2>/dev/null || true"
                ),
            )
            if port is None:
                m_cfg_port = re.search(r"(?m)^[ \t]*port:[ \t]*(\d+)", cfg_out)
                if m_cfg_port:
                    try:
                        port = int(m_cfg_port.group(1))
                    except Exception:
                        port = None
            if not replset_name:
                m_cfg_repl = re.search(r"(?m)^[ \t]*replSetName:[ \t]*([^\s#]+)", cfg_out)
                if m_cfg_repl:
                    replset_name = m_cfg_repl.group(1).strip()

        if port is None:
            port = 27017

        return {
            "ssh_rc": shell_rc,
            "shell": None if shell_bin == "none" else shell_bin,
            "shell_probe_stderr": shell_err.strip(),
            "ports": [port],
            "selected_port": port,
            "replset_name": replset_name,
            "mongod_cmdline": mongod_cmdline,
        }

    def _run_mongo_eval_via_ssh(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str],
        ssh_key_path: Optional[str],
        shell_bin: str,
        mongo_port: int,
        js_code: str,
        mongo_user: Optional[str],
        mongo_password: Optional[str],
        auth_db: str = "admin",
    ) -> Dict[str, Any]:
        attempts: List[Dict[str, Any]] = []
        candidate_modes: List[str] = ["ssh_local_noauth"]
        if mongo_user and mongo_password:
            candidate_modes.append("ssh_local_with_mongo_creds")

        for mode in candidate_modes:
            stdin_data = None
            if mode == "ssh_local_with_mongo_creds":
                auth_script = (
                    "var __authDb = db.getSiblingDB(" + json.dumps(auth_db) + ");\n"
                    "if (__authDb.auth(" + json.dumps(mongo_user or "") + ", " + json.dumps(mongo_password or "") + ")) {\n"
                    "  print(" + js_code + ");\n"
                    "} else {\n"
                    "  print(JSON.stringify({ok:0, codeName:'AuthenticationFailed', errmsg:'authentication failed'}));\n"
                    "}\n"
                )
                cmd = (
                    f"{shlex.quote(shell_bin)} --quiet --host 127.0.0.1 --port {mongo_port}"
                )
                stdin_data = auth_script
            else:
                cmd = (
                    f"{shlex.quote(shell_bin)} --quiet --host 127.0.0.1 --port {mongo_port} "
                    f"--eval {shlex.quote(js_code)}"
                )

            rc, out, stderr = run_ssh_command(
                host=ssh_host,
                username=ssh_user,
                password=ssh_password,
                key_path=ssh_key_path,
                command=cmd,
                stdin_data=stdin_data,
            )
            parsed = _json_from_stdout(out)
            auth_failed = _looks_like_auth_error(parsed, stderr, out)
            attempts.append({
                "mode": mode,
                "rc": rc,
                "stderr": (stderr or "").strip()[:400],
                "stdout": (out or "").strip()[:400],
            })

            if auth_failed and mode == "ssh_local_noauth" and "ssh_local_with_mongo_creds" in candidate_modes:
                continue

            if rc != 0:
                code, msg = _classify_mongo_shell_error(stderr, out)
                return {
                    "ok": False,
                    "code": code,
                    "message": msg,
                    "rc": rc,
                    "stdout": out,
                    "stderr": stderr,
                    "attempts": attempts,
                }

            if parsed is None:
                return {
                    "ok": False,
                    "code": "PARSE_ERROR",
                    "message": "Could not parse JSON from Mongo shell output",
                    "rc": rc,
                    "stdout": out,
                    "stderr": stderr,
                    "attempts": attempts,
                }

            if isinstance(parsed, dict):
                ok_value = parsed.get("ok")
                if ok_value in (0, 0.0, False):
                    msg = str(parsed.get("errmsg") or parsed.get("codeName") or "Mongo command returned ok:0")
                    code, classified_msg = _classify_mongo_shell_error(
                        stderr,
                        f"{out}\n{msg}",
                    )
                    return {
                        "ok": False,
                        "code": code,
                        "message": classified_msg if code != "MONGO_ERROR" else msg,
                        "rc": rc,
                        "stdout": out,
                        "stderr": stderr,
                        "attempts": attempts,
                        "raw": parsed,
                    }

            return {
                "ok": True,
                "data": parsed,
                "rc": rc,
                "stdout": out,
                "stderr": stderr,
                "mode": mode,
                "attempts": attempts,
            }

        return {
            "ok": False,
            "code": "MONGO_ERROR",
            "message": "Mongo command execution failed",
            "attempts": attempts,
        }

    def _db_mongo_connect_impl(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[MongoDB][SSH] Validate local MongoDB connectivity and return version/hello info."""
        ssh_user, ssh_password, ssh_key_path, ssh_err = _resolve_ssh_auth_inputs(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )
        if ssh_err:
            return err(ssh_err, code="INPUT_ERROR")

        mongo_user, mongo_password, mongo_err = _resolve_optional_mongo_auth(credential_id)
        if mongo_err:
            return err(mongo_err, code="INPUT_ERROR")

        discovery = _discover_mongo_runtime_details(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
        )
        if discovery.get("ssh_rc", 0) != 0:
            return err(
                "SSH connection failed during Mongo runtime discovery",
                code="SSH_ERROR",
                rc=discovery.get("ssh_rc"),
                stderr=discovery.get("shell_probe_stderr"),
                discovery=discovery,
            )
        shell_bin = discovery.get("shell")
        if not shell_bin:
            return err(
                "SSH succeeded, but mongosh/mongo was not found on remote host",
                code="MONGO_ERROR",
                discovery=discovery,
            )

        js = (
            "JSON.stringify((function(){"
            "var ping=db.adminCommand({ping:1});"
            "var build=db.adminCommand({buildInfo:1});"
            "var hello={};"
            "try{hello=db.adminCommand({hello:1});}catch(e){try{hello=db.isMaster();}catch(e2){hello={};}}"
            "return {ping:ping,version:(build.version||null),hello:hello};"
            "})())"
        )
        exec_res = _run_mongo_eval_via_ssh(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            shell_bin=shell_bin,
            mongo_port=int(discovery["selected_port"]),
            js_code=js,
            mongo_user=mongo_user,
            mongo_password=mongo_password,
            auth_db="admin",
        )
        if not exec_res.get("ok"):
            return err(
                str(exec_res.get("message", "Mongo SSH command failed")),
                code=str(exec_res.get("code", "MONGO_ERROR")),
                rc=exec_res.get("rc"),
                stderr=exec_res.get("stderr"),
                stdout=exec_res.get("stdout"),
                attempts=exec_res.get("attempts"),
                discovery=discovery,
            )

        data = exec_res["data"] if isinstance(exec_res.get("data"), dict) else {}
        return ok({
            "ping": data.get("ping"),
            "version": data.get("version"),
            "hello": data.get("hello"),
            "connection": {"via": "ssh_mongo_shell", "mode": exec_res.get("mode")},
            "discovery": discovery,
        })

    def _db_mongo_rs_status_impl(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[MongoDB][SSH] Return replica-set status from the target VM."""
        ssh_user, ssh_password, ssh_key_path, ssh_err = _resolve_ssh_auth_inputs(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )
        if ssh_err:
            return err(ssh_err, code="INPUT_ERROR")

        mongo_user, mongo_password, mongo_err = _resolve_optional_mongo_auth(credential_id)
        if mongo_err:
            return err(mongo_err, code="INPUT_ERROR")

        discovery = _discover_mongo_runtime_details(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
        )
        if discovery.get("ssh_rc", 0) != 0:
            return err(
                "SSH connection failed during Mongo runtime discovery",
                code="SSH_ERROR",
                rc=discovery.get("ssh_rc"),
                stderr=discovery.get("shell_probe_stderr"),
                discovery=discovery,
            )
        shell_bin = discovery.get("shell")
        if not shell_bin:
            return err(
                "SSH succeeded, but mongosh/mongo was not found on remote host",
                code="MONGO_ERROR",
                discovery=discovery,
            )

        exec_res = _run_mongo_eval_via_ssh(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            shell_bin=shell_bin,
            mongo_port=int(discovery["selected_port"]),
            js_code="JSON.stringify(rs.status())",
            mongo_user=mongo_user,
            mongo_password=mongo_password,
            auth_db="admin",
        )
        if not exec_res.get("ok"):
            return err(
                str(exec_res.get("message", "Mongo SSH command failed")),
                code=str(exec_res.get("code", "MONGO_ERROR")),
                rc=exec_res.get("rc"),
                stderr=exec_res.get("stderr"),
                stdout=exec_res.get("stdout"),
                attempts=exec_res.get("attempts"),
                discovery=discovery,
            )

        data = exec_res["data"] if isinstance(exec_res.get("data"), dict) else {}
        return ok({
            "set": data.get("set"),
            "myState": data.get("myState"),
            "members": data.get("members", []),
            "raw": data,
            "connection": {"via": "ssh_mongo_shell", "mode": exec_res.get("mode")},
            "discovery": discovery,
        })

    @mcp.tool()
    def db_mongo_connect(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[MongoDB][SSH] Validate local MongoDB connectivity and return version/hello info."""
        return _db_mongo_connect_impl(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )

    @mcp.tool()
    def db_mongo_rs_status(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[MongoDB][SSH] Return replica-set status from the target VM."""
        return _db_mongo_rs_status_impl(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )

    @mcp.tool()
    def db_mongo_ssh_ping(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[MongoDB][SSH][Alias] Backward-compatible alias for `db_mongo_connect`."""
        return _db_mongo_connect_impl(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )

    @mcp.tool()
    def db_mongo_ssh_rs_status(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[MongoDB][SSH][Alias] Backward-compatible alias for `db_mongo_rs_status`."""
        return _db_mongo_rs_status_impl(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )

    @mcp.tool(name="validate_collection")
    def db_mongo_ssh_validate_collection(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
        db_name: str = "admin",
        collection: str = "",
        full: bool = True,
    ) -> Dict[str, Any]:
        """[MongoDB][SSH] Validate collection integrity using `validate({full})`.

        If `collection` is omitted, validates all non-system collections in `db_name`.
        """

        ssh_user, ssh_password, ssh_key_path, ssh_err = _resolve_ssh_auth_inputs(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )
        if ssh_err:
            return err(ssh_err, code="INPUT_ERROR")

        mongo_user, mongo_password, mongo_err = _resolve_optional_mongo_auth(credential_id)
        if mongo_err:
            return err(mongo_err, code="INPUT_ERROR")

        discovery = _discover_mongo_runtime_details(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
        )
        if discovery.get("ssh_rc", 0) != 0:
            return err(
                "SSH connection failed during Mongo runtime discovery",
                code="SSH_ERROR",
                rc=discovery.get("ssh_rc"),
                stderr=discovery.get("shell_probe_stderr"),
                discovery=discovery,
                via="ssh_mongo_shell",
            )
        shell_bin = discovery.get("shell")
        if not shell_bin:
            return err(
                "SSH succeeded, but mongosh/mongo was not found on remote host",
                code="MONGO_ERROR",
                discovery=discovery,
            )

        def _validate_one_collection(target_collection: str) -> Dict[str, Any]:
            js = (
                "JSON.stringify("
                f"db.getSiblingDB('{_js_quote(db_name)}')"
                f".getCollection('{_js_quote(target_collection)}')"
                f".validate({{full: {str(full).lower()}}})"
                ")"
            )
            exec_res = _run_mongo_eval_via_ssh(
                ssh_host=ssh_host,
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                ssh_key_path=ssh_key_path,
                shell_bin=shell_bin,
                mongo_port=int(discovery["selected_port"]),
                js_code=js,
                mongo_user=mongo_user,
                mongo_password=mongo_password,
                auth_db="admin",
            )
            if not exec_res.get("ok"):
                return {
                    "ok": False,
                    "exec_error": {
                        "message": str(exec_res.get("message", "Mongo SSH command failed")),
                        "code": str(exec_res.get("code", "MONGO_ERROR")),
                        "rc": exec_res.get("rc"),
                        "stderr": exec_res.get("stderr"),
                        "stdout": exec_res.get("stdout"),
                        "attempts": exec_res.get("attempts"),
                    },
                }

            data = exec_res["data"] if isinstance(exec_res.get("data"), dict) else {}
            valid = bool(data.get("valid", data.get("ok", 0)))
            result: Dict[str, Any] = {
                "via": "ssh_mongo_shell",
                "db": db_name,
                "collection": target_collection,
                "full": full,
                "validate": data,
                "connection": {"mode": exec_res.get("mode")},
                "discovery": discovery,
            }
            for key in ("errors", "warnings", "nIndexes", "nrecords", "repaired"):
                if key in data:
                    result[key] = data[key]
            return {"ok": valid, "result": result}

        # Single collection mode (backward-compatible response shape)
        if collection:
            single = _validate_one_collection(collection)
            if single.get("exec_error"):
                exec_error = single["exec_error"]
                return err(
                    str(exec_error.get("message", "Mongo SSH command failed")),
                    code=str(exec_error.get("code", "MONGO_ERROR")),
                    rc=exec_error.get("rc"),
                    stderr=exec_error.get("stderr"),
                    stdout=exec_error.get("stdout"),
                    attempts=exec_error.get("attempts"),
                    discovery=discovery,
                    via="ssh_mongo_shell",
                )

            result = single["result"]
            if single.get("ok"):
                return ok(result)
            return err("collection validation reported invalid", code="VALIDATE_FAILED", **result)

        # Multi-collection mode
        list_collections_js = (
            "JSON.stringify("
            f"db.getSiblingDB('{_js_quote(db_name)}').getCollectionNames()"
            ")"
        )
        list_exec = _run_mongo_eval_via_ssh(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            shell_bin=shell_bin,
            mongo_port=int(discovery["selected_port"]),
            js_code=list_collections_js,
            mongo_user=mongo_user,
            mongo_password=mongo_password,
            auth_db="admin",
        )
        if not list_exec.get("ok"):
            return err(
                str(list_exec.get("message", "Mongo SSH command failed")),
                code=str(list_exec.get("code", "MONGO_ERROR")),
                rc=list_exec.get("rc"),
                stderr=list_exec.get("stderr"),
                stdout=list_exec.get("stdout"),
                attempts=list_exec.get("attempts"),
                discovery=discovery,
                via="ssh_mongo_shell",
            )

        raw_names = list_exec.get("data")
        if not isinstance(raw_names, list):
            return err(
                "Could not parse collection list from Mongo shell output",
                code="PARSE_ERROR",
                discovery=discovery,
                via="ssh_mongo_shell",
            )

        all_collections = [name for name in raw_names if isinstance(name, str) and name.strip()]
        non_system_collections = [name for name in all_collections if not name.startswith("system.")]
        target_collections = non_system_collections if non_system_collections else all_collections

        if not target_collections:
            return ok({
                "via": "ssh_mongo_shell",
                "db": db_name,
                "full": full,
                "message": "No collections found to validate",
                "discovered_collections": all_collections,
                "validated_collections": [],
                "summary": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 0,
                },
                "results": [],
                "discovery": discovery,
            })

        results: List[Dict[str, Any]] = []
        passed = 0
        failed = 0
        errors = 0
        for target_collection in target_collections:
            single = _validate_one_collection(target_collection)
            if single.get("exec_error"):
                exec_error = single["exec_error"]
                errors += 1
                results.append({
                    "collection": target_collection,
                    "status": "ERROR",
                    "error": exec_error,
                })
                continue

            single_result = single["result"]
            if single.get("ok"):
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"
            results.append({
                "collection": target_collection,
                "status": status,
                "details": single_result,
            })

        payload = {
            "via": "ssh_mongo_shell",
            "db": db_name,
            "full": full,
            "discovered_collections": all_collections,
            "validated_collections": target_collections,
            "summary": {
                "total": len(target_collections),
                "passed": passed,
                "failed": failed,
                "errors": errors,
            },
            "results": results,
            "discovery": discovery,
        }

        if failed > 0 or errors > 0:
            return err("one or more collection validations failed", code="VALIDATE_FAILED", **payload)
        return ok(payload)
