"""
Copyright contributors to the agentic-ai-cyberres project
"""

"""Oracle database validation tools.

These tools use the `oracledb` Python package in thin mode to connect
to an Oracle database. They expose simple read-only queries to verify
connectivity, capture instance and database metadata, and report
tablespace utilization. Credentials and DSN parameters are supplied
from the validation request.
"""

from typing import Dict, Any, Optional
import logging
import oracledb
import re
import shlex


def attach(mcp):
    """Register Oracle DB tools onto the FastMCP instance."""
    logger = logging.getLogger("mcp.oracle")
    try:
        from .utils import ok, err
    except Exception:
        from plugins.utils import ok, err  # type: ignore
    try:
        from .mongo_db import run_ssh_command
    except Exception:
        from plugins.mongo_db import run_ssh_command  # type: ignore

    @mcp.tool()
    def db_oracle_connect(dsn: Optional[str] = None,
                          host: Optional[str] = None,
                          port: int = 1521,
                          service: Optional[str] = None,
                          user: Optional[str] = None,
                          password: Optional[str] = None) -> Dict[str, Any]:
        """Attempt to connect to an Oracle instance and return basic info.

        If a DSN is not supplied, one will be constructed from
        host/port/service using ``oracledb.makedsn``. If connection
        succeeds, queries against ``v$instance`` and ``v$database``
        return instance name, version, open mode, and role. On
        failure, the error message is returned.
        """
        conn = None
        cur = None
        try:
            # Validate inputs for thin mode: require either DSN or host+service
            if not dsn and not (host and service):
                return err("Provide either dsn or host+service for connection", code="INPUT_ERROR")
            if not dsn and host and service:
                dsn = oracledb.makedsn(host, port, service_name=service)
            conn = oracledb.connect(user=user, password=password, dsn=dsn)
            cur = conn.cursor()
            cur.execute("select instance_name, version from v$instance")
            inst = cur.fetchone()
            cur.execute("select open_mode, database_role from v$database")
            db = cur.fetchone()
            return ok({
                "instance_name": inst[0],
                "version": inst[1],
                "open_mode": db[0],
                "database_role": db[1],
            })
        except Exception as e:
            msg = str(e)
            logger.warning("oracle_connect failed", extra={"error": msg})
            # Helpful hint for DPY-3001 (thick mode requirement)
            if "DPY-3001" in msg:
                return err(
                    "DPY-3001: Supply dsn or host+service for thin mode, or initialize thick mode",
                    code="ORACLE_THIN_MODE_DSN_REQUIRED",
                )
            return err(msg, code="ORACLE_ERROR")
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except Exception:
                pass

    @mcp.tool()
    def db_oracle_tablespaces(dsn: str, user: str, password: str) -> Dict[str, Any]:
        """Fetch tablespace usage for an Oracle database.

        Uses DBA views to compute used and free megabytes for each
        tablespace, along with the percentage used. Returns a list
        sorted by descending usage. If the query fails, returns an
        error message instead.
        """
        conn = None
        cur = None
        sql = """
        select
          df.tablespace_name,
          round((df.total_mb - nvl(fs.free_mb,0)) / df.total_mb * 100, 2) as used_pct,
          round(nvl(fs.free_mb,0),2) as free_mb
        from
          (select tablespace_name, sum(bytes)/1024/1024 as total_mb from dba_data_files group by tablespace_name) df
          left join (select tablespace_name, sum(bytes)/1024/1024 as free_mb from dba_free_space group by tablespace_name) fs
            on df.tablespace_name = fs.tablespace_name
        order by used_pct desc
        """
        try:
            if not dsn:
                return err("dsn is required", code="INPUT_ERROR")
            conn = oracledb.connect(user=user, password=password, dsn=dsn)
            cur = conn.cursor()
            cur.execute(sql)
            cols = [desc[0].lower() for desc in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            return ok({"tablespaces": rows})
        except Exception as e:
            msg = str(e)
            logger.warning("oracle_tablespaces failed", extra={"error": msg})
            if "DPY-3001" in msg:
                return err(
                    "DPY-3001: Supply a valid dsn for thin mode, or initialize thick mode",
                    code="ORACLE_THIN_MODE_DSN_REQUIRED",
                )
            return err(msg, code="ORACLE_ERROR")

    @mcp.tool()
    def db_oracle_discover_and_validate(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        oracle_user: Optional[str] = None,
        oracle_password: Optional[str] = None,
        lsnrctl_path: str = "lsnrctl",
        sudo_oracle: bool = False,
    ) -> Dict[str, Any]:
        """
        Discover Oracle listener/services via SSH and optionally validate DB connectivity.

        - Uses `ps -ef | grep pmon` to infer SIDs
        - Runs `lsnrctl status` to parse services and port(s)
        - Builds candidate DSNs as `<host>/<service_name>` for thin mode
        - If `oracle_user` and `oracle_password` are provided, attempts a connect
          to the first discovered service and returns basic instance info.
        """
        # 1) Check for PMON to infer SIDs
        rc, pmon_out, pmon_err = run_ssh_command(
            host=ssh_host,
            username=ssh_user,
            password=ssh_password,
            key_path=ssh_key_path,
            command="ps -ef | egrep 'ora_pmon_|pmon' | grep -v grep || true",
        )
        # Sanitize host for logging
        safe_host = shlex.quote(ssh_host)
        sids = []
        sid_re = re.compile(r"ora_pmon_([A-Za-z0-9_#$]+)")
        for line in pmon_out.splitlines():
            m = sid_re.search(line)
            if m:
                sids.append(m.group(1))

        # 2) Listener status (try status, then services)
        cmd_prefix = "sudo -u oracle -H sh -lc '" if sudo_oracle else ""
        cmd_suffix = "'" if sudo_oracle else ""
        rc2, lsnr_out, lsnr_err = run_ssh_command(
            host=ssh_host,
            username=ssh_user,
            password=ssh_password,
            key_path=ssh_key_path,
            command=f"{cmd_prefix}{lsnrctl_path} status || {lsnrctl_path} services || true{cmd_suffix}",
        )
        # Parse services and port
        services = []
        # Patterns for lsnrctl output across versions
        for m in re.finditer(r"Service\s+\"([A-Za-z0-9_.$-]+)\"", lsnr_out):
            services.append(m.group(1))
        ports = []
        for m in re.finditer(r"\(PORT=([0-9]+)\)", lsnr_out):
            ports.append(int(m.group(1)))

        # 2b) If listener parsing failed, try reading listener.ora and tnsnames.ora
        if not services or not ports:
            try:
                from .settings import SETTINGS
            except Exception:
                from settings import SETTINGS  # type: ignore
            for path in [
                SETTINGS.oracle_listener_ora,
                "/etc/oracle/listener.ora",
            ]:
                rc3, out3, _ = run_ssh_command(
                    host=ssh_host,
                    username=ssh_user,
                    password=ssh_password,
                    key_path=ssh_key_path,
                    command=f"{cmd_prefix}cat {path} 2>/dev/null || true{cmd_suffix}",
                )
                for m in re.finditer(r"\(PORT=([0-9]+)\)", out3):
                    try:
                        ports.append(int(m.group(1)))
                    except Exception:
                        pass
            for path in [
                SETTINGS.oracle_tnsnames_ora,
                "/etc/oracle/tnsnames.ora",
            ]:
                rc4, out4, _ = run_ssh_command(
                    host=ssh_host,
                    username=ssh_user,
                    password=ssh_password,
                    key_path=ssh_key_path,
                    command=f"{cmd_prefix}cat {path} 2>/dev/null || true{cmd_suffix}",
                )
                for m in re.finditer(r"SERVICE_NAME\s*=\s*([A-Za-z0-9_.$-]+)", out4):
                    services.append(m.group(1))

        discoveries = {
            "sids": sorted(list(set(sids))),
            "services": sorted(list(set(services))),
            "ports": sorted(list(set(ports))),
        }

        # Build candidate DSNs (fallback: use SID as service and default port 1521)
        candidate_dsns = [f"{ssh_host}/{svc}" for svc in discoveries["services"]]
        if not candidate_dsns and discoveries["sids"]:
            candidate_dsns = [f"{ssh_host}/{discoveries['sids'][0]}"]

        result: Dict[str, Any] = {
            "discoveries": discoveries,
            "candidate_dsns": candidate_dsns,
        }

        # Optionally validate connectivity if creds are provided
        if oracle_user and oracle_password and candidate_dsns:
            conn = None
            cur = None
            try:
                dsn = candidate_dsns[0]
                conn = oracledb.connect(user=oracle_user, password=oracle_password, dsn=dsn)
                cur = conn.cursor()
                cur.execute("select instance_name, version from v$instance")
                inst = cur.fetchone()
                cur.execute("select open_mode, database_role from v$database")
                db = cur.fetchone()
                result.update({
                    "validation": {
                        "dsn": dsn,
                        "instance_name": inst[0],
                        "version": inst[1],
                        "open_mode": db[0],
                        "database_role": db[1],
                    }
                })
            except Exception as e:
                msg = str(e)
                logger.info("oracle validation failed after discovery", extra={"error": msg})
                result.update({
                    "validation_error": {
                        "message": msg,
                        "code": "ORACLE_ERROR"
                    }
                })
            finally:
                try:
                    if cur:
                        cur.close()
                    if conn:
                        conn.close()
                except Exception:
                    pass

        return ok(result)