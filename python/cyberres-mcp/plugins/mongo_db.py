"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""MongoDB validation tools.

This module uses ``pymongo`` to connect to MongoDB servers and
clusters, perform a simple ping, fetch server version, and return
replica set status if applicable. Only read-only commands are
issued. Errors are captured and returned to the caller.
"""

from typing import Dict, Any, Optional, Tuple
import logging
import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import json, shlex


def _make_ssh_client(known_hosts_path: Optional[str] = None):
    """Return a Paramiko SSHClient that verifies host keys.

    Loads ``known_hosts_path`` or ``~/.ssh/known_hosts`` when available,
    and uses ``RejectPolicy`` so unknown hosts are refused instead of
    silently accepted (avoids the AutoAddPolicy MITM risk).
    """
    import paramiko
    from paramiko import SSHClient, RejectPolicy

    client = SSHClient()
    client.set_missing_host_key_policy(RejectPolicy())
    default_kh = os.path.expanduser("~/.ssh/known_hosts")
    path = known_hosts_path or (default_kh if os.path.isfile(default_kh) else None)
    if path and os.path.isfile(path):
        try:
            client.load_host_keys(path)
        except Exception:
            pass
    return client


def run_ssh_command(
    host: str,
    username: str,
    password: Optional[str] = None,
    key_path: Optional[str] = None,
    command: str = "",
    port: int = 22,
    timeout: float = 10.0,
    known_hosts_path: Optional[str] = None,
) -> Tuple[int, str, str]:
    """
    Minimal SSH exec helper using Paramiko.
    Returns (return_code, stdout, stderr) with UTF-8 decoded text.
    """
    import paramiko  # lazy import keeps module import-time light

    client = _make_ssh_client(known_hosts_path)

    try:
        if key_path:
            pkey = None
            # Try Ed25519, then RSA
            for Key in (paramiko.Ed25519Key, paramiko.RSAKey):
                try:
                    pkey = Key.from_private_key_file(key_path)
                    break
                except Exception:
                    pkey = None
            if pkey:
                client.connect(hostname=host, port=port, username=username, pkey=pkey, timeout=timeout)
            else:
                # Fallback lets Paramiko read the file directly
                client.connect(hostname=host, port=port, username=username, key_filename=key_path, timeout=timeout)
        else:
            client.connect(hostname=host, port=port, username=username, password=password, timeout=timeout)

        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        return rc, out, err
    finally:
        try:
            client.close()
        except Exception:
            pass


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

def _build_local_uri(mongo_user: Optional[str], mongo_password: Optional[str],
                     port: int, auth_db: str) -> str:
    if mongo_user and mongo_password:
        # Percent-encode credentials so they embed correctly in the URI.
        from urllib.parse import quote as _pct
        user = _pct(mongo_user, safe="")
        pwd = _pct(mongo_password, safe="")
        return f"mongodb://{user}:{pwd}@127.0.0.1:{port}/{auth_db}?authSource={auth_db}"
    return f"mongodb://127.0.0.1:{port}/{auth_db}"

def _js_quote(s: str) -> str:
    # escape for single-quoted JS string literal
    return s.replace("\\", "\\\\").replace("'", "\\'")

def attach(mcp):
    """Register MongoDB tools onto the FastMCP instance."""
    logger = logging.getLogger("mcp.mongo")
    try:
        from .utils import ok, err
    except Exception:
        # fallback if relative import differs when packaged
        from plugins.utils import ok, err  # type: ignore

    @mcp.tool()
    def db_mongo_connect(uri: Optional[str] = None,
                         host: Optional[str] = None,
                         port: int = 27017,
                         user: Optional[str] = None,
                         password: Optional[str] = None,
                         database: str = "admin") -> Dict[str, Any]:
        """Connect to MongoDB and return ping response and server version."""
        try:
            # Build a connection URI if not provided
            if not uri:
                if user and password:
                    uri = f"mongodb://{user}:{password}@{host}:{port}/{database}?authSource={database}"
                else:
                    uri = f"mongodb://{host}:{port}/{database}"
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            # ``ping`` admin command returns OK if server reachable
            pong = client.admin.command("ping")
            ver = client.server_info().get("version")
            return ok({"ping": pong, "version": ver})
        except PyMongoError as e:
            logger.warning("mongo_connect failed", extra={"error": str(e)})
            return err(str(e), code="MONGO_ERROR")

    @mcp.tool()
    def db_mongo_rs_status(uri: str) -> Dict[str, Any]:
        """Return replica set status for a MongoDB cluster."""
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            status = client.admin.command("replSetGetStatus")
            # Extract a few salient fields
            return ok({
                "set": status.get("set"),
                "myState": status.get("myState"),
                "members": status.get("members", []),
            })
        except PyMongoError as e:
            logger.warning("mongo_rs_status failed", extra={"error": str(e)})
            return err(str(e), code="MONGO_ERROR")

    @mcp.tool()
    def db_mongo_ssh_ping(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        port: int = 27017,
        mongo_user: Optional[str] = None,
        mongo_password: Optional[str] = None,
        auth_db: str = "admin",
        mongosh_path: str = "mongosh"
    ) -> Dict[str, Any]:
        """
        SSH into the server and run: db.adminCommand({ ping: 1 }) locally via mongosh.
        Use when MongoDB listens only on 127.0.0.1 of the remote host.
        """
        uri = _build_local_uri(mongo_user, mongo_password, port, auth_db)
        # Build a single-line shell command; --quiet + JSON.stringify for clean JSON
        cmd = f"{shlex.quote(mongosh_path)} --quiet '{uri}' --eval 'JSON.stringify(db.adminCommand({{ ping: 1 }}))'"
        rc, out, err = run_ssh_command(
            host=ssh_host,
            username=ssh_user,
            password=ssh_password,
            key_path=ssh_key_path,
            command=cmd
        )
        if rc != 0:
            logger.warning("ssh ping failed", extra={"rc": rc, "stderr": err})
            return err("ssh exec failed", code="SSH_ERROR", rc=rc, stderr=err, stdout=out, via="ssh_exec")
        data = _json_from_stdout(out)
        if not data:
            logger.warning("ssh ping parse failed")
            return err("could not parse JSON from mongosh output", code="PARSE_ERROR", stdout=out, via="ssh_exec")
        return ok({"ping": data}, via="ssh_exec")

    @mcp.tool()
    def db_mongo_ssh_rs_status(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        port: int = 27017,
        mongo_user: Optional[str] = None,
        mongo_password: Optional[str] = None,
        auth_db: str = "admin",
        mongosh_path: str = "mongosh"
    ) -> Dict[str, Any]:
        """
        SSH into the server and run: rs.status() locally via mongosh.
        """
        uri = _build_local_uri(mongo_user, mongo_password, port, auth_db)
        cmd = f"{shlex.quote(mongosh_path)} --quiet '{uri}' --eval 'JSON.stringify(rs.status())'"
        rc, out, err = run_ssh_command(
            host=ssh_host,
            username=ssh_user,
            password=ssh_password,
            key_path=ssh_key_path,
            command=cmd
        )
        if rc != 0:
            logger.warning("ssh rs.status failed", extra={"rc": rc, "stderr": err})
            return err("ssh exec failed", code="SSH_ERROR", rc=rc, stderr=err, stdout=out, via="ssh_exec")
        data = _json_from_stdout(out)
        if not data:
            logger.warning("ssh rs.status parse failed")
            return err("could not parse JSON from mongosh output", code="PARSE_ERROR", stdout=out, via="ssh_exec")
        return ok({
            "set": data.get("set"),
            "myState": data.get("myState"),
            "members": data.get("members", []),
            "raw": data,
        }, via="ssh_exec")

    @mcp.tool(name="validate_collection")
    def db_mongo_ssh_validate_collection(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        # Mongo on the remote host
        port: int = 27017,
        mongo_user: Optional[str] = None,
        mongo_password: Optional[str] = None,
        auth_db: str = "admin",    # where the creds are valid
        db_name: str = "admin",    # database owning the collection
        collection: str = "",      # collection to validate (required)
        full: bool = True,         # validate({ full: true }) is thorough
        mongosh_path: str = "mongosh"
        ) -> Dict[str, Any]:
        """
        SSH into the VM and run:
          db.getSiblingDB(<db_name>).getCollection(<collection>).validate({ full: <bool> })
        via mongosh. Returns parsed JSON 'validate' output plus a friendly summary.
        """
        if not collection:
            return err("collection is required", code="INPUT_ERROR", via="ssh_exec")

        uri = _build_local_uri(mongo_user, mongo_password, port, auth_db)

        js = (
            "JSON.stringify("
            f"db.getSiblingDB('{_js_quote(db_name)}')"
            f".getCollection('{_js_quote(collection)}')"
            f".validate({{full: {str(full).lower()}}})"
            ")"
        )

        cmd = f"{shlex.quote(mongosh_path)} --quiet '{uri}' --eval '{js}'"

        rc, out, err = run_ssh_command(
            host=ssh_host,
            username=ssh_user,
            password=ssh_password,
            key_path=ssh_key_path,
            command=cmd
        )
        if rc != 0:
            logger.warning("ssh validate failed", extra={"rc": rc, "stderr": err})
            return err("ssh exec failed", code="SSH_ERROR", rc=rc, stderr=err, stdout=out, via="ssh_exec")

        data = _json_from_stdout(out)
        if not data:
            logger.warning("ssh validate parse failed")
            return err("could not parse JSON from mongosh output", code="PARSE_ERROR", stdout=out, via="ssh_exec")

        # normalize common fields (Mongo versions differ a bit)
        valid = bool(data.get("valid", data.get("ok", 0)))
        res: Dict[str, Any] = {
            "via": "ssh_exec",
            "db": db_name,
            "collection": collection,
            "full": full,
            "validate": data
        }
        for k in ("errors", "warnings", "nIndexes", "nrecords", "repaired"):
            if k in data: res[k] = data[k]
        if valid:
            return ok(res)
        else:
            return err("collection validation reported invalid", code="VALIDATE_FAILED", **res)