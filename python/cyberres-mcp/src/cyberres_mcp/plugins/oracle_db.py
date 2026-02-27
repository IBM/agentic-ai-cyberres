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

from typing import Dict, Any, Optional, List, Tuple
import logging
import oracledb
import re
import shlex


def attach(mcp):
    """Register Oracle DB tools onto the FastMCP instance."""
    logger = logging.getLogger("mcp.oracle")
    try:
        from .utils import ok, err, resolve_ssh_auth, resolve_scoped_auth
    except Exception:
        from plugins.utils import ok, err, resolve_ssh_auth, resolve_scoped_auth  # type: ignore
    try:
        from .mongo_db import run_ssh_command
    except Exception:
        from plugins.mongo_db import run_ssh_command  # type: ignore

    def _run_ssh_command_with_optional_sudo(
        ssh_host: str,
        ssh_user: str,
        command: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        sudo_oracle: bool = False,
    ) -> Tuple[int, str, str]:
        if sudo_oracle:
            wrapped = shlex.quote(command)
            command = f"sudo -u oracle -H sh -lc {wrapped}"
        return run_ssh_command(
            host=ssh_host,
            username=ssh_user,
            password=ssh_password,
            key_path=ssh_key_path,
            command=command,
        )

    def _run_sqlplus_query_via_ssh(
        ssh_host: str,
        ssh_user: str,
        sql_query: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        sudo_oracle: bool = False,
        oracle_sid: Optional[str] = None,
    ) -> Tuple[int, str, str]:
        sql_lines = [
            "set pagesize 0 feedback off verify off heading off echo off linesize 32767 trimspool on",
            f"{sql_query.strip().rstrip(';')};",
            "exit;",
        ]
        quoted_sql_lines = " ".join(shlex.quote(line) for line in sql_lines)
        sid_assignment = ""
        if oracle_sid:
            sid_assignment = f"export ORACLE_SID={shlex.quote(oracle_sid)}; "
        command = (
            f"{sid_assignment}"
            "if command -v sqlplus >/dev/null 2>&1; then SQLPLUS_BIN=$(command -v sqlplus); "
            "elif [ -n \"$ORACLE_HOME\" ] && [ -x \"$ORACLE_HOME/bin/sqlplus\" ]; then SQLPLUS_BIN=\"$ORACLE_HOME/bin/sqlplus\"; "
            "else SQLPLUS_BIN=$(find /u01 /opt /usr -type f -name sqlplus 2>/dev/null | head -n 1); fi; "
            "if [ -z \"$SQLPLUS_BIN\" ]; then echo \"sqlplus: command not found\" >&2; exit 127; fi; "
            "if [ -z \"$ORACLE_HOME\" ]; then ORACLE_HOME=$(dirname \"$(dirname \"$SQLPLUS_BIN\")\"); export ORACLE_HOME; fi; "
            "if [ -n \"$ORACLE_HOME\" ]; then export PATH=\"$ORACLE_HOME/bin:$PATH\"; export LD_LIBRARY_PATH=\"$ORACLE_HOME/lib:${LD_LIBRARY_PATH:-}\"; fi; "
            "if [ -z \"$ORACLE_SID\" ]; then "
            "ORACLE_SID=$(ps -ef | awk '/ora_pmon_/ && !/awk|grep/ {sub(/.*ora_pmon_/, \"\", $0); print $0; exit}'); "
            "export ORACLE_SID; "
            "fi; "
            "if [ -n \"$ORACLE_SID\" ]; then "
            "if [ -x /usr/local/bin/oraenv ]; then ORAENV_ASK=NO . /usr/local/bin/oraenv >/dev/null 2>&1 || true; "
            "elif [ -x /usr/bin/oraenv ]; then ORAENV_ASK=NO . /usr/bin/oraenv >/dev/null 2>&1 || true; fi; "
            "fi; "
            f"printf '%s\\n' {quoted_sql_lines} | \"$SQLPLUS_BIN\" -S '/ as sysdba'"
        )
        return _run_ssh_command_with_optional_sudo(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            command=command,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            sudo_oracle=sudo_oracle,
        )

    def _build_ssh_os_auth_error_message(stderr: str, stdout: str = "") -> str:
        combined = f"{stderr}\n{stdout}".strip()
        err_lower = combined.lower()
        ora_match = re.search(r"(ORA-\d{5}:[^\n\r]*)", combined)
        if ora_match:
            return f"Oracle query failed in SSH OS-auth mode: {ora_match.group(1)}"
        if "sqlplus: command not found" in err_lower:
            return (
                "SSH succeeded but sqlplus was not found for Oracle OS-auth. "
                "Install Oracle client/server binaries or fix PATH/ORACLE_HOME for the SSH target user."
            )
        if "no space left on device" in err_lower:
            return (
                "SSH succeeded but remote filesystem is full (No space left on device). "
                "Free space on the target (especially /tmp and Oracle mount points) and retry."
            )
        if "sp2-0667" in err_lower or "sp2-0750" in err_lower:
            return (
                "SSH succeeded but Oracle environment is incomplete for sqlplus (ORACLE_HOME/message files). "
                "Set ORACLE_HOME correctly for the oracle user or ensure oraenv is configured."
            )
        return (
            "SSH connection succeeded, but Oracle OS-auth query failed. "
            "Try sudo_oracle=true and verify Oracle environment for the remote user."
        )

    def _resolve_ssh_auth_inputs(
        ssh_user: str,
        ssh_password: Optional[str],
        ssh_key_path: Optional[str],
        credential_id: Optional[str] = None,
    ) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        """Resolve SSH auth from args first, then secrets by credential_id."""
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

    def _resolve_oracle_auth_inputs(
        oracle_user: Optional[str],
        oracle_password: Optional[str],
        credential_id: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolve Oracle DB auth from args first, then credential_id."""
        return resolve_scoped_auth(
            username=oracle_user,
            password=oracle_password,
            credential_id=credential_id,
            scope_name="oracle",
            user_keys=["username", "user", "oracle_user"],
            password_keys=["password", "oracle_password"],
            logger=logger,
        )

    def _parse_pipe_rows(stdout: str, min_columns: int) -> List[List[str]]:
        rows: List[List[str]] = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped or "|" not in stripped:
                continue
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) >= min_columns:
                rows.append(parts)
        return rows

    def _parse_first_scalar(stdout: str) -> Optional[str]:
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("sql>"):
                continue
            if stripped.lower().startswith("error at line"):
                continue
            if stripped.lower().startswith("ora-"):
                continue
            return stripped
        return None

    def _safe_int(value: Optional[str], default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(str(value).strip())
        except Exception:
            try:
                return int(float(str(value).strip()))
            except Exception:
                return default

    def _safe_float(value: Optional[str], default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(str(value).strip())
        except Exception:
            return default

    def _discover_oracle_connection_details(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        lsnrctl_path: str = "lsnrctl",
        sudo_oracle: bool = False,
    ) -> Dict[str, Any]:
        """Discover Oracle services/ports on a remote host via SSH."""
        # 1) Check PMON processes to infer SIDs
        _, pmon_out, _ = _run_ssh_command_with_optional_sudo(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            command="ps -ef | egrep 'ora_pmon_|pmon' | grep -v grep || true",
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            sudo_oracle=sudo_oracle,
        )

        sids = []
        sid_re = re.compile(r"ora_pmon_([A-Za-z0-9_#$]+)")
        for line in pmon_out.splitlines():
            m = sid_re.search(line)
            if m:
                sids.append(m.group(1))

        # 2) Listener status
        quoted_lsnrctl = shlex.quote(lsnrctl_path)
        _, lsnr_out, _ = _run_ssh_command_with_optional_sudo(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            command=f"{quoted_lsnrctl} status || {quoted_lsnrctl} services || true",
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            sudo_oracle=sudo_oracle,
        )

        services = []
        for m in re.finditer(r"Service\s+\"([A-Za-z0-9_.$-]+)\"", lsnr_out):
            services.append(m.group(1))
        ports = []
        for m in re.finditer(r"\(PORT=([0-9]+)\)", lsnr_out):
            try:
                ports.append(int(m.group(1)))
            except Exception:
                pass

        # 3) Fallback: listener.ora / tnsnames.ora
        if not services or not ports:
            try:
                from ..settings import SETTINGS
            except Exception:
                try:
                    from cyberres_mcp.settings import SETTINGS  # type: ignore
                except Exception:
                    class FallbackSettings:
                        oracle_listener_ora = "/u01/app/oracle/product/*/network/admin/listener.ora"
                        oracle_tnsnames_ora = "/u01/app/oracle/product/*/network/admin/tnsnames.ora"
                    SETTINGS = FallbackSettings()  # type: ignore

            for path in [SETTINGS.oracle_listener_ora, "/etc/oracle/listener.ora"]:
                _, out3, _ = _run_ssh_command_with_optional_sudo(
                    ssh_host=ssh_host,
                    ssh_user=ssh_user,
                    command=f"cat {path} 2>/dev/null || true",
                    ssh_password=ssh_password,
                    ssh_key_path=ssh_key_path,
                    sudo_oracle=sudo_oracle,
                )
                for m in re.finditer(r"\(PORT=([0-9]+)\)", out3):
                    try:
                        ports.append(int(m.group(1)))
                    except Exception:
                        pass

            for path in [SETTINGS.oracle_tnsnames_ora, "/etc/oracle/tnsnames.ora"]:
                _, out4, _ = _run_ssh_command_with_optional_sudo(
                    ssh_host=ssh_host,
                    ssh_user=ssh_user,
                    command=f"cat {path} 2>/dev/null || true",
                    ssh_password=ssh_password,
                    ssh_key_path=ssh_key_path,
                    sudo_oracle=sudo_oracle,
                )
                for m in re.finditer(r"SERVICE_NAME\s*=\s*([A-Za-z0-9_.$-]+)", out4):
                    services.append(m.group(1))

        discoveries = {
            "sids": sorted(list(set(sids))),
            "services": sorted(list(set(services))),
            "ports": sorted(list(set(ports))),
        }

        # Build candidate DSNs using discovered ports; default to 1521 if unknown.
        candidate_dsns: List[str] = []
        candidate_ports = discoveries["ports"] if discoveries["ports"] else [1521]
        for svc in discoveries["services"]:
            for discovered_port in candidate_ports:
                if discovered_port == 1521:
                    candidate_dsns.append(f"{ssh_host}/{svc}")
                else:
                    candidate_dsns.append(
                        oracledb.makedsn(ssh_host, discovered_port, service_name=svc)
                    )

        if not candidate_dsns and discoveries["sids"]:
            sid = discoveries["sids"][0]
            for discovered_port in candidate_ports:
                if discovered_port == 1521:
                    candidate_dsns.append(f"{ssh_host}/{sid}")
                else:
                    candidate_dsns.append(oracledb.makedsn(ssh_host, discovered_port, sid=sid))

        # Preserve order while deduplicating.
        deduped_dsns: List[str] = []
        seen = set()
        for candidate in candidate_dsns:
            if candidate not in seen:
                seen.add(candidate)
                deduped_dsns.append(candidate)

        return {
            "discoveries": discoveries,
            "candidate_dsns": deduped_dsns,
        }

    @mcp.tool()
    def db_oracle_connect(ssh_host: str,
                          ssh_user: str,
                          ssh_password: Optional[str] = None,
                          ssh_key_path: Optional[str] = None,
                          credential_id: Optional[str] = None,
                          sudo_oracle: bool = False) -> Dict[str, Any]:
        """[Oracle][SSH] Validate Oracle connectivity and return instance metadata.

        Uses SSH + sqlplus OS authentication on the target host.
        """
        ssh_user, ssh_password, ssh_key_path, auth_error = _resolve_ssh_auth_inputs(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )
        if auth_error:
            return err(auth_error, code="INPUT_ERROR")
        discovery = _discover_oracle_connection_details(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            lsnrctl_path="lsnrctl",
            sudo_oracle=sudo_oracle,
        )
        discovered_sids = discovery.get("discoveries", {}).get("sids", [])
        sid_for_sqlplus = discovered_sids[0] if discovered_sids else None
        sql = """
        SELECT
            i.instance_name || '|' || i.version || '|' || d.open_mode || '|' || d.database_role
        FROM v$instance i
        CROSS JOIN v$database d
        """
        rc, out, stderr = _run_sqlplus_query_via_ssh(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            sql_query=sql,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            sudo_oracle=sudo_oracle,
            oracle_sid=sid_for_sqlplus,
        )
        rows = _parse_pipe_rows(out, 4)
        if rows:
            row = rows[0]
            return ok({
                "instance_name": row[0],
                "version": row[1],
                "open_mode": row[2],
                "database_role": row[3],
                "connection": {"via": "ssh_sqlplus_os_auth"},
                "discovery": discovery.get("discoveries", {}),
                "candidate_dsns": discovery.get("candidate_dsns", []),
            })
        return err(
            _build_ssh_os_auth_error_message(stderr, out),
            code="ORACLE_ERROR",
            rc=rc,
            stderr=stderr,
            stdout=out,
            discovery=discovery.get("discoveries", {}),
        )

    @mcp.tool()
    def db_oracle_tablespaces(ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
        sudo_oracle: bool = False,
    ) -> Dict[str, Any]:
        """[Oracle][SSH] Report tablespace usage percentage and free space."""
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
        ssh_user, ssh_password, ssh_key_path, auth_error = _resolve_ssh_auth_inputs(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )
        if auth_error:
            return err(auth_error, code="INPUT_ERROR")
        discovery = _discover_oracle_connection_details(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            lsnrctl_path="lsnrctl",
            sudo_oracle=sudo_oracle,
        )
        discovered_sids = discovery.get("discoveries", {}).get("sids", [])
        sid_for_sqlplus = discovered_sids[0] if discovered_sids else None
        ssh_sql = """
        SELECT
            df.tablespace_name || '|' ||
            ROUND((df.total_mb - NVL(fs.free_mb,0)) / df.total_mb * 100, 2) || '|' ||
            ROUND(NVL(fs.free_mb,0),2)
        FROM
            (SELECT tablespace_name, SUM(bytes)/1024/1024 AS total_mb
             FROM dba_data_files
             GROUP BY tablespace_name) df
            LEFT JOIN
            (SELECT tablespace_name, SUM(bytes)/1024/1024 AS free_mb
             FROM dba_free_space
             GROUP BY tablespace_name) fs
            ON df.tablespace_name = fs.tablespace_name
        ORDER BY ROUND((df.total_mb - NVL(fs.free_mb,0)) / df.total_mb * 100, 2) DESC
        """
        rc, out, stderr = _run_sqlplus_query_via_ssh(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            sql_query=ssh_sql,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            sudo_oracle=sudo_oracle,
            oracle_sid=sid_for_sqlplus,
        )
        parsed_rows = _parse_pipe_rows(out, 3)
        tablespaces = []
        for parts in parsed_rows:
            used_pct = None
            free_mb = None
            try:
                used_pct = float(parts[1])
            except Exception:
                pass
            try:
                free_mb = float(parts[2])
            except Exception:
                pass
            tablespaces.append({
                "tablespace_name": parts[0],
                "used_pct": used_pct,
                "free_mb": free_mb,
            })
        if tablespaces:
            return ok({
                "tablespaces": tablespaces,
                "connection": {"via": "ssh_sqlplus_os_auth"},
                "discovery": discovery.get("discoveries", {}),
                "candidate_dsns": discovery.get("candidate_dsns", []),
            })
        return err(
            _build_ssh_os_auth_error_message(stderr, out),
            code="ORACLE_ERROR",
            rc=rc,
            stderr=stderr,
            stdout=out,
            discovery=discovery.get("discoveries", {}),
        )

    @mcp.tool()
    def db_oracle_data_validation(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        credential_id: Optional[str] = None,
        sudo_oracle: bool = False,
    ) -> Dict[str, Any]:
        """[Oracle][SSH] Run post-recovery data-integrity and production-readiness checks."""
        ssh_user, ssh_password, ssh_key_path, auth_error = _resolve_ssh_auth_inputs(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )
        if auth_error:
            return err(auth_error, code="INPUT_ERROR")

        discovery = _discover_oracle_connection_details(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            lsnrctl_path="lsnrctl",
            sudo_oracle=sudo_oracle,
        )
        discovered_sids = discovery.get("discoveries", {}).get("sids", [])
        sid_for_sqlplus = discovered_sids[0] if discovered_sids else None

        core_sql = """
        SELECT
            NVL((SELECT open_mode FROM v$database), 'UNKNOWN') || '|' ||
            NVL((SELECT database_role FROM v$database), 'UNKNOWN') || '|' ||
            NVL((SELECT log_mode FROM v$database), 'UNKNOWN') || '|' ||
            NVL((SELECT COUNT(*) FROM v$recover_file), 0) || '|' ||
            NVL((SELECT SUM(blocks) FROM v$database_block_corruption), 0) || '|' ||
            NVL((SELECT COUNT(*) FROM v$datafile WHERE status NOT IN ('ONLINE', 'SYSTEM')), 0) || '|' ||
            NVL((SELECT COUNT(*) FROM v$datafile_header WHERE error IS NOT NULL), 0) || '|' ||
            NVL((SELECT COUNT(*) FROM dba_objects WHERE status = 'INVALID'), 0) || '|' ||
            NVL((
                SELECT ROUND(MAX(used_pct), 2)
                FROM (
                    SELECT ROUND((df.total_mb - NVL(fs.free_mb,0)) / NULLIF(df.total_mb,0) * 100, 2) AS used_pct
                    FROM (SELECT tablespace_name, SUM(bytes)/1024/1024 AS total_mb FROM dba_data_files GROUP BY tablespace_name) df
                    LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1024/1024 AS free_mb FROM dba_free_space GROUP BY tablespace_name) fs
                    ON df.tablespace_name = fs.tablespace_name
                )
            ), 0) || '|' ||
            NVL((
                SELECT COUNT(*)
                FROM (
                    SELECT ROUND((df.total_mb - NVL(fs.free_mb,0)) / NULLIF(df.total_mb,0) * 100, 2) AS used_pct
                    FROM (SELECT tablespace_name, SUM(bytes)/1024/1024 AS total_mb FROM dba_data_files GROUP BY tablespace_name) df
                    LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1024/1024 AS free_mb FROM dba_free_space GROUP BY tablespace_name) fs
                    ON df.tablespace_name = fs.tablespace_name
                )
                WHERE used_pct >= 95
            ), 0) || '|' ||
            NVL((SELECT COUNT(*) FROM v$archive_dest WHERE status = 'ERROR'), 0)
        FROM dual
        """
        rc, out, stderr = _run_sqlplus_query_via_ssh(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            sql_query=core_sql,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            sudo_oracle=sudo_oracle,
            oracle_sid=sid_for_sqlplus,
        )
        core_rows = _parse_pipe_rows(out, 11)
        if not core_rows:
            return err(
                _build_ssh_os_auth_error_message(stderr, out),
                code="ORACLE_ERROR",
                rc=rc,
                stderr=stderr,
                stdout=out,
                discovery=discovery.get("discoveries", {}),
            )

        row = core_rows[0]
        open_mode = row[0]
        database_role = row[1]
        log_mode = row[2]
        recover_file_count = _safe_int(row[3])
        corrupted_blocks = _safe_int(row[4])
        offline_datafiles = _safe_int(row[5])
        datafile_header_errors = _safe_int(row[6])
        invalid_objects = _safe_int(row[7])
        max_tablespace_used_pct = _safe_float(row[8])
        critical_tablespace_count = _safe_int(row[9])
        archive_dest_errors = _safe_int(row[10])

        backup_age_days: Optional[int] = None
        backup_age_query_error: Optional[str] = None
        backup_sql = """
        SELECT NVL(TRUNC(SYSDATE - MAX(end_time)), -1)
        FROM v$rman_backup_job_details
        WHERE status = 'COMPLETED'
        """
        backup_rc, backup_out, backup_stderr = _run_sqlplus_query_via_ssh(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            sql_query=backup_sql,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            sudo_oracle=sudo_oracle,
            oracle_sid=sid_for_sqlplus,
        )
        if backup_rc == 0:
            backup_scalar = _parse_first_scalar(backup_out)
            if backup_scalar is not None:
                parsed_days = _safe_int(backup_scalar, default=-1)
                if parsed_days >= 0:
                    backup_age_days = parsed_days
            elif "ORA-" in backup_out or "SP2-" in backup_out:
                backup_age_query_error = _build_ssh_os_auth_error_message(backup_stderr, backup_out)
        else:
            backup_age_query_error = _build_ssh_os_auth_error_message(backup_stderr, backup_out)

        archived_log_age_minutes: Optional[int] = None
        archived_log_query_error: Optional[str] = None
        archived_log_sql = """
        SELECT NVL(TRUNC((SYSDATE - MAX(next_time)) * 24 * 60), -1)
        FROM v$archived_log
        WHERE archived = 'YES'
        """
        archived_rc, archived_out, archived_stderr = _run_sqlplus_query_via_ssh(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            sql_query=archived_log_sql,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            sudo_oracle=sudo_oracle,
            oracle_sid=sid_for_sqlplus,
        )
        if archived_rc == 0:
            archived_scalar = _parse_first_scalar(archived_out)
            if archived_scalar is not None:
                parsed_minutes = _safe_int(archived_scalar, default=-1)
                if parsed_minutes >= 0:
                    archived_log_age_minutes = parsed_minutes
            elif "ORA-" in archived_out or "SP2-" in archived_out:
                archived_log_query_error = _build_ssh_os_auth_error_message(archived_stderr, archived_out)
        else:
            archived_log_query_error = _build_ssh_os_auth_error_message(archived_stderr, archived_out)

        checks: List[Dict[str, Any]] = []
        fail_count = 0
        warn_count = 0

        def _add_check(name: str, status: str, observed: Any, expected: str, impact: str) -> None:
            nonlocal fail_count, warn_count
            checks.append({
                "name": name,
                "status": status,
                "observed": observed,
                "expected": expected,
                "impact": impact,
            })
            if status == "FAIL":
                fail_count += 1
            elif status == "WARN":
                warn_count += 1

        _add_check(
            name="open_mode",
            status="PASS" if open_mode == "READ WRITE" else "FAIL",
            observed=open_mode,
            expected="READ WRITE",
            impact="Database must be open read/write to safely serve production traffic.",
        )
        _add_check(
            name="database_role",
            status="PASS" if database_role == "PRIMARY" else "FAIL",
            observed=database_role,
            expected="PRIMARY",
            impact="Recovered target should be PRIMARY before production cutover.",
        )
        _add_check(
            name="media_recovery_required_files",
            status="PASS" if recover_file_count == 0 else "FAIL",
            observed=recover_file_count,
            expected="0",
            impact="Files needing recovery indicate incomplete restore/recovery.",
        )
        _add_check(
            name="database_block_corruption",
            status="PASS" if corrupted_blocks == 0 else "FAIL",
            observed=corrupted_blocks,
            expected="0",
            impact="Non-zero corrupted blocks indicates physical corruption risk.",
        )
        _add_check(
            name="datafiles_online",
            status="PASS" if offline_datafiles == 0 else "FAIL",
            observed=offline_datafiles,
            expected="0 offline datafiles",
            impact="Offline datafiles can cause data loss or runtime failures.",
        )
        _add_check(
            name="datafile_header_errors",
            status="PASS" if datafile_header_errors == 0 else "FAIL",
            observed=datafile_header_errors,
            expected="0",
            impact="Header errors indicate potential datafile inconsistency.",
        )
        _add_check(
            name="tablespace_capacity_critical",
            status="PASS" if critical_tablespace_count == 0 else "FAIL",
            observed={
                "critical_tablespace_count": critical_tablespace_count,
                "max_used_pct": max_tablespace_used_pct,
            },
            expected="0 tablespaces >= 95% used",
            impact="Critical tablespaces can block writes immediately after cutover.",
        )
        _add_check(
            name="archive_destination_errors",
            status="PASS" if archive_dest_errors == 0 else "FAIL",
            observed=archive_dest_errors,
            expected="0",
            impact="Archive destination errors reduce recoverability after go-live.",
        )
        _add_check(
            name="archivelog_mode",
            status="PASS" if log_mode == "ARCHIVELOG" else "WARN",
            observed=log_mode,
            expected="ARCHIVELOG",
            impact="ARCHIVELOG mode is recommended for production recoverability.",
        )
        _add_check(
            name="invalid_objects",
            status="PASS" if invalid_objects == 0 else "WARN",
            observed=invalid_objects,
            expected="0",
            impact="Invalid objects may cause application runtime errors.",
        )
        if backup_age_days is None:
            _add_check(
                name="backup_recency",
                status="WARN",
                observed="unknown",
                expected="Most recent completed backup <= 7 days",
                impact="Unable to verify backup recency from RMAN metadata.",
            )
        else:
            _add_check(
                name="backup_recency",
                status="PASS" if backup_age_days <= 7 else "WARN",
                observed=f"{backup_age_days} days",
                expected="<= 7 days",
                impact="Stale backups increase risk if another incident occurs.",
            )
        if log_mode == "ARCHIVELOG":
            if archived_log_age_minutes is None:
                _add_check(
                    name="archived_log_freshness",
                    status="WARN",
                    observed="unknown",
                    expected="Most recent archived log <= 120 minutes",
                    impact="Unable to confirm recent archive log generation.",
                )
            else:
                _add_check(
                    name="archived_log_freshness",
                    status="PASS" if archived_log_age_minutes <= 120 else "WARN",
                    observed=f"{archived_log_age_minutes} minutes",
                    expected="<= 120 minutes",
                    impact="Old archive logs may indicate archive/redo shipping issues.",
                )

        overall_status = "FAIL" if fail_count > 0 else ("PASS_WITH_WARNINGS" if warn_count > 0 else "PASS")
        production_ready = fail_count == 0

        response: Dict[str, Any] = {
            "production_ready": production_ready,
            "overall_status": overall_status,
            "summary": {
                "total_checks": len(checks),
                "passed": len([c for c in checks if c["status"] == "PASS"]),
                "warnings": warn_count,
                "failed": fail_count,
            },
            "checks": checks,
            "metrics": {
                "open_mode": open_mode,
                "database_role": database_role,
                "log_mode": log_mode,
                "recover_file_count": recover_file_count,
                "corrupted_blocks": corrupted_blocks,
                "offline_datafiles": offline_datafiles,
                "datafile_header_errors": datafile_header_errors,
                "invalid_objects": invalid_objects,
                "max_tablespace_used_pct": max_tablespace_used_pct,
                "critical_tablespace_count_95_pct": critical_tablespace_count,
                "archive_dest_errors": archive_dest_errors,
                "backup_age_days": backup_age_days,
                "archived_log_age_minutes": archived_log_age_minutes,
            },
            "connection": {"via": "ssh_sqlplus_os_auth"},
            "discovery": discovery.get("discoveries", {}),
            "candidate_dsns": discovery.get("candidate_dsns", []),
        }

        if backup_age_query_error:
            response["backup_check_note"] = backup_age_query_error
        if archived_log_query_error:
            response["archived_log_check_note"] = archived_log_query_error

        return ok(response)

    @mcp.tool()
    def db_oracle_discover_and_validate(
        ssh_host: str,
        ssh_user: str,
        ssh_password: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        oracle_user: Optional[str] = None,
        oracle_password: Optional[str] = None,
        credential_id: Optional[str] = None,
        lsnrctl_path: str = "lsnrctl",
        sudo_oracle: bool = False,
    ) -> Dict[str, Any]:
        """[Oracle][SSH] Discover Oracle listener/SID details and optionally validate DB login.

        - Uses `ps -ef | grep pmon` to infer SIDs
        - Runs `lsnrctl status` to parse services and port(s)
        - Builds candidate DSNs as `<host>/<service_name>` for thin mode
        - If `oracle_user` and `oracle_password` are provided, attempts a connect
          to the first discovered service and returns basic instance info.
        """
        ssh_user, ssh_password, ssh_key_path, ssh_auth_err = _resolve_ssh_auth_inputs(
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            credential_id=credential_id,
        )
        if ssh_auth_err:
            return err(ssh_auth_err, code="INPUT_ERROR")

        oracle_user, oracle_password, oracle_auth_err = _resolve_oracle_auth_inputs(
            oracle_user=oracle_user,
            oracle_password=oracle_password,
            credential_id=credential_id,
        )
        # Keep discovery usable without DB creds; fail only if user is set but password missing.
        if oracle_auth_err and oracle_user:
            return err(oracle_auth_err, code="INPUT_ERROR")

        discovery = _discover_oracle_connection_details(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            ssh_key_path=ssh_key_path,
            lsnrctl_path=lsnrctl_path,
            sudo_oracle=sudo_oracle,
        )
        discoveries = discovery["discoveries"]
        candidate_dsns = discovery["candidate_dsns"]

        result: Dict[str, Any] = {
            "discoveries": discoveries,
            "candidate_dsns": candidate_dsns,
        }

        # Optionally validate connectivity if creds are provided
        if oracle_user and oracle_password and candidate_dsns:
            validation_attempts = []
            for dsn in candidate_dsns:
                conn = None
                cur = None
                try:
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
                    break
                except Exception as e:
                    msg = str(e)
                    logger.info("oracle validation failed after discovery", extra={"dsn": dsn, "error": msg})
                    validation_attempts.append({"dsn": dsn, "error": msg})
                finally:
                    try:
                        if cur:
                            cur.close()
                        if conn:
                            conn.close()
                    except Exception:
                        pass

            if "validation" not in result:
                result.update({
                    "validation_error": {
                        "message": "Failed to validate against all discovered DSNs",
                        "code": "ORACLE_ERROR",
                        "attempts": validation_attempts,
                    }
                })

        return ok(result)

    @mcp.tool()
    def db_oracle_discover_config(
        host: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        credential_id: Optional[str] = None,
        port: int = 1521,
        service: Optional[str] = None,
        sid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """[Oracle][Direct DB] Collect detailed Oracle configuration using DB credentials.
        
        Connects to Oracle database and retrieves comprehensive configuration including:
        - Instance information (name, version, status, startup time)
        - Database information (name, role, open mode, log mode)
        - Tablespace usage and details
        - Memory configuration (SGA, PGA)
        - Database parameters
        - Datafile locations and sizes
        - Redo log configuration
        - Archive log status
        
        Args:
            host: Oracle database host
            user: Database username (typically SYS or SYSTEM)
            password: Database password
            port: Database port (default: 1521)
            service: Service name (optional, will try to discover if not provided)
            sid: SID (optional, alternative to service name)
        
        Returns:
            Comprehensive Oracle configuration details or error message
        """
        conn = None
        cur = None
        user, password, auth_err = _resolve_oracle_auth_inputs(
            oracle_user=user,
            oracle_password=password,
            credential_id=credential_id,
        )
        if auth_err:
            return err(auth_err, code="INPUT_ERROR")
        if not user or not password:
            return err("Provide Oracle user/password or credential_id with oracle credentials", code="INPUT_ERROR")
        
        try:
            # Build DSN - try service first, then SID, then attempt discovery
            dsn = None
            if service:
                dsn = oracledb.makedsn(host, port, service_name=service)
            elif sid:
                dsn = oracledb.makedsn(host, port, sid=sid)
            else:
                # Try common service names
                for svc in ["ORCL", "XE", "ORCLPDB1"]:
                    try:
                        test_dsn = oracledb.makedsn(host, port, service_name=svc)
                        test_conn = oracledb.connect(user=user, password=password, dsn=test_dsn)
                        test_conn.close()
                        dsn = test_dsn
                        service = svc
                        break
                    except Exception:
                        continue
                
                if not dsn:
                    return err(
                        "Could not connect. Please provide service name or SID.",
                        code="ORACLE_CONNECTION_ERROR"
                    )
            
            # Connect to database
            conn = oracledb.connect(user=user, password=password, dsn=dsn)
            cur = conn.cursor()
            
            config = {}
            
            # 1. Instance Information
            cur.execute("""
                SELECT instance_name, host_name, version, status,
                       startup_time, database_status, instance_role
                FROM v$instance
            """)
            inst = cur.fetchone()
            config["instance"] = {
                "instance_name": inst[0],
                "host_name": inst[1],
                "version": inst[2],
                "status": inst[3],
                "startup_time": str(inst[4]) if inst[4] else None,
                "database_status": inst[5],
                "instance_role": inst[6],
            }
            
            # 2. Database Information
            cur.execute("""
                SELECT name, db_unique_name, dbid, open_mode,
                       log_mode, database_role, platform_name
                FROM v$database
            """)
            db = cur.fetchone()
            config["database"] = {
                "name": db[0],
                "db_unique_name": db[1],
                "dbid": db[2],
                "open_mode": db[3],
                "log_mode": db[4],
                "database_role": db[5],
                "platform_name": db[6],
            }
            
            # 3. Tablespace Information
            cur.execute("""
                SELECT
                    df.tablespace_name,
                    df.total_mb,
                    ROUND(df.total_mb - NVL(fs.free_mb, 0), 2) as used_mb,
                    ROUND(NVL(fs.free_mb, 0), 2) as free_mb,
                    ROUND((df.total_mb - NVL(fs.free_mb, 0)) / df.total_mb * 100, 2) as used_pct,
                    df.status
                FROM
                    (SELECT tablespace_name,
                            SUM(bytes)/1024/1024 as total_mb,
                            status
                     FROM dba_data_files
                     GROUP BY tablespace_name, status) df
                LEFT JOIN
                    (SELECT tablespace_name,
                            SUM(bytes)/1024/1024 as free_mb
                     FROM dba_free_space
                     GROUP BY tablespace_name) fs
                ON df.tablespace_name = fs.tablespace_name
                ORDER BY used_pct DESC
            """)
            cols = [desc[0].lower() for desc in cur.description]
            config["tablespaces"] = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            # 4. Memory Configuration
            cur.execute("""
                SELECT name, value, display_value
                FROM v$parameter
                WHERE name IN ('sga_target', 'sga_max_size', 'pga_aggregate_target',
                              'memory_target', 'memory_max_target')
            """)
            config["memory"] = {}
            for row in cur.fetchall():
                config["memory"][row[0]] = {
                    "value": row[1],
                    "display_value": row[2]
                }
            
            # 5. Datafiles
            cur.execute("""
                SELECT file_name, tablespace_name,
                       ROUND(bytes/1024/1024, 2) as size_mb,
                       status, autoextensible
                FROM dba_data_files
                ORDER BY tablespace_name, file_name
            """)
            cols = [desc[0].lower() for desc in cur.description]
            config["datafiles"] = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            # 6. Redo Logs
            cur.execute("""
                SELECT l.group#, l.thread#, l.sequence#, l.bytes/1024/1024 as size_mb,
                       l.members, l.status, lf.member as file_path
                FROM v$log l
                JOIN v$logfile lf ON l.group# = lf.group#
                ORDER BY l.group#, lf.member
            """)
            cols = [desc[0].lower() for desc in cur.description]
            config["redo_logs"] = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            # 7. Archive Log Mode
            cur.execute("""
                SELECT dest_name, status, destination,
                       ROUND(space_limit/1024/1024, 2) as space_limit_mb,
                       ROUND(space_used/1024/1024, 2) as space_used_mb
                FROM v$archive_dest
                WHERE status != 'INACTIVE'
            """)
            cols = [desc[0].lower() for desc in cur.description]
            config["archive_destinations"] = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            # 8. Key Database Parameters
            cur.execute("""
                SELECT name, value, display_value, description
                FROM v$parameter
                WHERE name IN ('db_block_size', 'db_cache_size', 'shared_pool_size',
                              'processes', 'sessions', 'open_cursors', 'db_recovery_file_dest',
                              'db_recovery_file_dest_size', 'control_files', 'db_create_file_dest')
                ORDER BY name
            """)
            config["parameters"] = {}
            for row in cur.fetchall():
                config["parameters"][row[0]] = {
                    "value": row[1],
                    "display_value": row[2],
                    "description": row[3]
                }
            
            # 9. Control Files
            cur.execute("SELECT name, status FROM v$controlfile")
            cols = [desc[0].lower() for desc in cur.description]
            config["control_files"] = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            # 10. Connection Info
            config["connection"] = {
                "host": host,
                "port": port,
                "service_name": service,
                "sid": sid,
                "dsn": dsn,
                "user": user
            }
            
            return ok(config)
            
        except Exception as e:
            msg = str(e)
            logger.warning("oracle_discover_config failed", extra={"error": msg})
            
            # Provide helpful error messages
            if "ORA-01017" in msg:
                return err("Invalid username/password", code="ORACLE_AUTH_ERROR")
            elif "ORA-12541" in msg or "ORA-12514" in msg:
                return err(
                    f"Cannot connect to {host}:{port}. Check host, port, and service/SID.",
                    code="ORACLE_CONNECTION_ERROR"
                )
            elif "DPY-6005" in msg or "Connection refused" in msg or "Errno 61" in msg:
                return err(
                    f"Connection refused to {host}:{port}. Possible causes:\n"
                    f"1. Oracle listener is not running on the target host\n"
                    f"2. Firewall is blocking port {port}\n"
                    f"3. Host/IP address is incorrect\n"
                    f"4. Port number is incorrect (default is 1521)\n"
                    f"5. Network connectivity issue\n"
                    f"Troubleshooting steps:\n"
                    f"- Verify Oracle listener is running: lsnrctl status\n"
                    f"- Check network connectivity: ping {host}\n"
                    f"- Test port connectivity: telnet {host} {port}\n"
                    f"- Verify firewall rules allow traffic on port {port}",
                    code="ORACLE_CONNECTION_REFUSED"
                )
            elif "DPY-3001" in msg:
                return err(
                    "DPY-3001: Provide service name or SID for thin mode connection",
                    code="ORACLE_THIN_MODE_DSN_REQUIRED"
                )
            elif "timed out" in msg.lower() or "timeout" in msg.lower():
                return err(
                    f"Connection timeout to {host}:{port}. Possible causes:\n"
                    f"1. Host is unreachable\n"
                    f"2. Firewall is dropping packets\n"
                    f"3. Network latency is too high\n"
                    f"Troubleshooting: Check network connectivity and firewall rules",
                    code="ORACLE_CONNECTION_TIMEOUT"
                )
            else:
                return err(
                    f"Oracle connection error: {msg}\n"
                    f"Connection details: host={host}, port={port}, service={service}, sid={sid}",
                    code="ORACLE_ERROR"
                )
        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except Exception:
                pass
