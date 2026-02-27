"""
Tool execution layer for BeeAI agents.
Handles MCP tool execution, result parsing, and error handling.
"""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from beeai_framework.tools.mcp import MCPTool
from models import CheckResult, ValidationStatus

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


class ToolExecutor:
    """Executes MCP tools with proper error handling and retry logic."""
    
    def __init__(self, mcp_tools: List[MCPTool], max_retries: int = 3):
        """Initialize tool executor.
        
        Args:
            mcp_tools: List of available MCP tools
            max_retries: Maximum retry attempts for failed executions
        """
        self.mcp_tools = mcp_tools
        self.max_retries = max_retries
        self._tool_map = {tool.name: tool for tool in mcp_tools}
        
        logger.info(f"Tool executor initialized with {len(mcp_tools)} tools")
    
    def find_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Find tool by name.
        
        Args:
            tool_name: Name of the tool to find
        
        Returns:
            MCPTool or None if not found
        """
        return self._tool_map.get(tool_name)
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute MCP tool with arguments.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
        
        Returns:
            Tool execution result
        
        Raises:
            ToolExecutionError: If tool execution fails
        """
        tool = self.find_tool(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool not found: {tool_name}")
        
        logger.info(f"Executing tool: {tool_name}")
        logger.debug(f"Tool arguments: {tool_args}")
        
        try:
            # Execute the tool using BeeAI's MCPTool interface
            # MCPTool.run() returns JSONToolOutput with .result attribute
            result_output = await tool.run(input=tool_args)
            
            # Get result - it's already a dict if it's JSON, or a string otherwise
            import json
            if isinstance(result_output.result, str):
                result = json.loads(result_output.result)
            else:
                result = result_output.result
            
            logger.info(f"Tool {tool_name} executed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {tool_name} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ToolExecutionError(error_msg) from e
    
    async def execute_with_retry(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool with exponential backoff retry.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
        
        Returns:
            Tool execution result
        
        Raises:
            ToolExecutionError: If all retry attempts fail
        """
        import asyncio
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** (attempt - 1)
                    logger.info(f"Retry attempt {attempt} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                
                return await self.execute_tool(tool_name, tool_args)
                
            except ToolExecutionError as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
        
        raise ToolExecutionError(
            f"Tool execution failed after {self.max_retries} attempts: {last_error}"
        )
    
    def parse_check_result(
        self,
        tool_result: Dict[str, Any],
        check_def: Any,
        expected_value: Optional[str] = None
    ) -> CheckResult:
        """Parse tool result into CheckResult with intelligent analysis.
        
        Args:
            tool_result: Raw tool execution result
            check_def: Check definition with expected criteria
            expected_value: Optional expected value for comparison
        
        Returns:
            CheckResult with status and details
        """
        # Handle both formats:
        # Format 1: {"success": bool, "data": {...}, "error": str/dict}
        # Format 2: {"ok": bool, ...direct data fields...}
        
        # Determine success status
        if "ok" in tool_result:
            # Oracle/MongoDB/VM format with "ok" field
            success = tool_result.get("ok", False)
            error = tool_result.get("error")
            # All other fields are data
            data = {k: v for k, v in tool_result.items() if k not in ["ok", "error"]}
        else:
            # Standard format with "success" field
            success = tool_result.get("success", False)
            data = tool_result.get("data", {})
            error = tool_result.get("error")
        
        # Convert error to string if it's a dict
        error_message = error
        if isinstance(error, dict):
            error_message = error.get('message', str(error))
        elif error is None and not success:
            error_message = "Tool execution failed"
        
        # ── Special case: vm_linux_services returns ok=False when services are
        # missing, but the result still contains useful data (missing list).
        # Treat this as a WARNING (not a hard FAIL) and surface the missing names.
        check_name_lower = check_def.check_name.lower()
        if not success and "service" in check_name_lower:
            missing = tool_result.get("missing", [])
            required = tool_result.get("required", [])
            running = tool_result.get("running", [])
            code = tool_result.get("code", "")
            if code == "SERVICE_CHECK_FAILED" or missing:
                # Services are missing — report as WARNING with names
                if missing:
                    msg = f"Required service(s) not running: {', '.join(missing)}"
                else:
                    msg = f"Service check failed (SSH error or no services found)"
                running_required = [s for s in required if s in running]
                actual_str = (
                    f"Running: {', '.join(running_required) or 'none of required'}; "
                    f"Missing: {', '.join(missing) or 'none'}"
                )
                return CheckResult(
                    check_id=check_def.check_id,
                    check_name=check_def.check_name,
                    status=ValidationStatus.WARNING,
                    message=msg,
                    expected=expected_value or check_def.expected_result,
                    actual=actual_str,
                    details={"missing": missing, "required": required, "running_count": len(running)}
                )
        
        # Handle failure
        if not success:
            return CheckResult(
                check_id=check_def.check_id,
                check_name=check_def.check_name,
                status=ValidationStatus.FAIL,
                message=error_message,
                expected=expected_value or check_def.expected_result,
                actual="Execution failed",
                details=data if data else None
            )
        
        # Success - create intelligent summary
        summary = self._create_intelligent_summary(check_def, data, tool_result)
        status = self._determine_check_status(check_def, data, tool_result)
        
        return CheckResult(
            check_id=check_def.check_id,
            check_name=check_def.check_name,
            status=status,
            message=summary,
            expected=expected_value or check_def.expected_result,
            actual=self._extract_actual_value(data, tool_result),
            details=data if data else tool_result
        )
    
    def _create_intelligent_summary(
        self,
        check_def: Any,
        data: Dict[str, Any],
        full_result: Dict[str, Any]
    ) -> str:
        """Create intelligent summary of check results.
        
        Args:
            check_def: Check definition
            data: Extracted data from result
            full_result: Full tool result
        
        Returns:
            Human-readable summary
        """
        check_name = check_def.check_name.lower()
        
        # Oracle Database Connection
        if "oracle" in check_name and "connect" in check_name:
            instance = full_result.get("instance_name", "Unknown")
            version = full_result.get("version", "Unknown")
            sids = full_result.get("discovery", {}).get("sids", [])
            connection_via = full_result.get("connection", {}).get("via", "unknown")
            
            if sids:
                return f"Oracle instance '{sids[0]}' is accessible via {connection_via}. Version: {version}"
            return f"Oracle connection successful via {connection_via}"
        
        # Oracle Tablespace
        if "tablespace" in check_name:
            tablespaces = full_result.get("tablespaces", [])
            if tablespaces:
                critical = [t for t in tablespaces if t.get("used_pct", 0) > 90]
                warning = [t for t in tablespaces if 80 <= t.get("used_pct", 0) <= 90]
                
                if critical:
                    ts_names = ", ".join([t["tablespace_name"] for t in critical])
                    return f"⚠️ CRITICAL: {len(critical)} tablespace(s) over 90% full: {ts_names}"
                elif warning:
                    ts_names = ", ".join([t["tablespace_name"] for t in warning])
                    return f"⚠️ WARNING: {len(warning)} tablespace(s) over 80% full: {ts_names}"
                else:
                    return f"✓ All {len(tablespaces)} tablespaces have adequate free space"
            return "Tablespace information retrieved"
        
        # Oracle Discovery
        if "oracle" in check_name and "discover" in check_name:
            sids = full_result.get("discovery", {}).get("sids", [])
            services = full_result.get("discovery", {}).get("services", [])
            
            if sids or services:
                parts = []
                if sids:
                    parts.append(f"{len(sids)} SID(s): {', '.join(sids)}")
                if services:
                    parts.append(f"{len(services)} service(s)")
                return f"Oracle discovery successful: {'; '.join(parts)}"
            return "Oracle discovery completed"
        
        # MongoDB connection / ping
        if "mongo" in check_name:
            if "connect" in check_name or "ping" in check_name:
                version = full_result.get("version")
                via = full_result.get("connection", {}).get("via", "ssh_mongo_shell")
                if version:
                    return f"MongoDB {version} reachable via {via}"
                return "MongoDB connection successful"
            elif "replica" in check_name or "rs" in check_name or "status" in check_name:
                rs_set = full_result.get("set")
                members = full_result.get("members", [])
                my_state = full_result.get("myState")
                state_map = {1: "PRIMARY", 2: "SECONDARY", 7: "ARBITER"}
                state_str = state_map.get(my_state, f"state={my_state}") if my_state is not None else "unknown"
                if rs_set:
                    return f"Replica set '{rs_set}': {len(members)} member(s), this node is {state_str}"
                return "MongoDB replica set status retrieved"

        # MongoDB collection integrity (validate_collection tool)
        # Two response shapes:
        #   auto-discover (collection=""):  ok, summary{total,passed,failed}, results[{collection,status}]
        #   single-collection:              ok, collection, db, validate{valid}, errors, warnings
        if "collection" in check_name and ("integrity" in check_name or "valid" in check_name):
            db_name = full_result.get("db", "admin")

            # ── Auto-discover mode (collection="" → multiple collections validated) ──
            if "summary" in full_result and "results" in full_result:
                summary = full_result.get("summary", {})
                total   = summary.get("total", 0)
                passed  = summary.get("passed", 0)
                failed  = summary.get("failed", 0)
                errors  = summary.get("errors", 0)
                validated = full_result.get("validated_collections", [])
                col_list  = ", ".join(validated[:3]) + ("..." if len(validated) > 3 else "")
                if failed or errors:
                    return (
                        f"❌ {failed}/{total} collection(s) failed integrity check "
                        f"in '{db_name}': {col_list}"
                    )
                return (
                    f"✓ {passed}/{total} collection(s) passed integrity validation "
                    f"in '{db_name}': {col_list}"
                )

            # ── Single-collection mode ──
            collection = full_result.get("collection", "")
            valid      = full_result.get("validate", {}).get("valid", True)
            col_errors = full_result.get("errors", [])
            warnings   = full_result.get("warnings", [])
            label = f"{db_name}.{collection}" if db_name and collection else (collection or "collection")
            if not valid or col_errors:
                err_str = "; ".join(str(e) for e in col_errors[:3]) if col_errors else "validation failed"
                return f"❌ Collection '{label}' integrity check FAILED: {err_str}"
            if warnings:
                warn_str = "; ".join(str(w) for w in warnings[:2])
                return f"⚠️ Collection '{label}' valid with warnings: {warn_str}"
            return f"✓ Collection '{label}' passed full integrity validation"
        
        # VM System Resources (uptime, load, memory)
        if "vm" in check_name and ("system" in check_name or "uptime" in check_name or "resource" in check_name):
            stdout = full_result.get("stdout", "")
            if stdout:
                lines = stdout.strip().split('\n')
                if lines:
                    # First line is typically uptime
                    uptime_line = lines[0] if lines else ""
                    # Look for memory info
                    mem_total = mem_free = None
                    for line in lines:
                        if "MemTotal" in line:
                            mem_total = line.split()[1]
                        elif "MemFree" in line or "MemAvailable" in line:
                            mem_free = line.split()[1]
                    
                    parts = []
                    if "load average" in uptime_line:
                        parts.append(uptime_line.split("load average:")[1].strip())
                    if mem_total and mem_free:
                        try:
                            total_mb = int(mem_total) // 1024
                            free_mb = int(mem_free) // 1024
                            used_pct = ((int(mem_total) - int(mem_free)) / int(mem_total)) * 100
                            parts.append(f"Memory: {used_pct:.1f}% used ({total_mb}MB total)")
                        except:
                            pass
                    
                    if parts:
                        return f"System health: {'; '.join(parts)}"
            return "System resources checked"
        
        # VM Filesystem Usage
        if "vm" in check_name and ("filesystem" in check_name or "disk" in check_name or "fs" in check_name):
            filesystems = full_result.get("filesystems", [])
            if filesystems:
                critical = [fs for fs in filesystems if fs.get("use_pct", 0) > 90]
                warning = [fs for fs in filesystems if 80 <= fs.get("use_pct", 0) <= 90]
                
                if critical:
                    fs_names = ", ".join([f"{fs['mountpoint']} ({fs['use_pct']}%)" for fs in critical])
                    return f"⚠️ CRITICAL: {len(critical)} filesystem(s) over 90% full: {fs_names}"
                elif warning:
                    fs_names = ", ".join([f"{fs['mountpoint']} ({fs['use_pct']}%)" for fs in warning])
                    return f"⚠️ WARNING: {len(warning)} filesystem(s) over 80% full: {fs_names}"
                else:
                    max_usage = max([fs.get("use_pct", 0) for fs in filesystems])
                    return f"✓ All {len(filesystems)} filesystems healthy (max usage: {max_usage}%)"
            return "Filesystem usage checked"
        
        # VM Services
        if "vm" in check_name and "service" in check_name:
            running = full_result.get("running", [])
            missing = full_result.get("missing", [])
            required = full_result.get("required", [])
            
            if missing:
                return f"⚠️ {len(missing)} required service(s) not running: {', '.join(missing)}"
            elif required:
                # At least one required service is running
                running_required = [s for s in required if s in running]
                if running_required:
                    return f"✓ Required service(s) running: {', '.join(running_required)}"
            
            return f"Services checked: {len(running)} running"
        
        # Network connectivity
        if "network" in check_name or "ping" in check_name or "connect" in check_name:
            return "Network connectivity verified"
        
        # Generic success
        return f"Check '{check_def.check_name}' completed successfully"
    
    def _determine_check_status(
        self,
        check_def: Any,
        data: Dict[str, Any],
        full_result: Dict[str, Any]
    ) -> ValidationStatus:
        """Determine validation status based on check results.
        
        Args:
            check_def: Check definition
            data: Extracted data
            full_result: Full tool result
        
        Returns:
            ValidationStatus
        """
        check_name = check_def.check_name.lower()
        
        # Tablespace checks - determine status based on usage
        if "tablespace" in check_name:
            tablespaces = full_result.get("tablespaces", [])
            if tablespaces:
                max_usage = max([t.get("used_pct", 0) for t in tablespaces])
                if max_usage > 90:
                    return ValidationStatus.FAIL
                elif max_usage > 80:
                    return ValidationStatus.WARNING
        
        # VM Filesystem checks - determine status based on usage
        if "vm" in check_name and ("filesystem" in check_name or "disk" in check_name or "fs" in check_name):
            filesystems = full_result.get("filesystems", [])
            if filesystems:
                max_usage = max([fs.get("use_pct", 0) for fs in filesystems])
                if max_usage > 90:
                    return ValidationStatus.FAIL
                elif max_usage > 85:
                    return ValidationStatus.WARNING
        
        # VM Services checks - determine status based on missing services
        if "vm" in check_name and "service" in check_name:
            missing = full_result.get("missing", [])
            if missing:
                return ValidationStatus.WARNING  # Missing services is a warning, not a failure

        # MongoDB collection integrity — validate_collection
        # Two response shapes: auto-discover (summary+results) or single-collection (validate{valid})
        if "collection" in check_name and ("integrity" in check_name or "valid" in check_name):
            # Auto-discover mode
            if "summary" in full_result and "results" in full_result:
                summary = full_result.get("summary", {})
                if summary.get("failed", 0) or summary.get("errors", 0):
                    return ValidationStatus.FAIL
                # All passed — check individual result warnings
                results = full_result.get("results", [])
                has_warnings = any(
                    r.get("status", "").upper() == "WARN"
                    for r in results
                )
                if has_warnings:
                    return ValidationStatus.WARNING
            else:
                # Single-collection mode
                validate_doc = full_result.get("validate", {})
                errors = full_result.get("errors", [])
                valid = validate_doc.get("valid", True) if isinstance(validate_doc, dict) else True
                if not valid or errors:
                    return ValidationStatus.FAIL
                warnings_list = full_result.get("warnings", [])
                if warnings_list:
                    return ValidationStatus.WARNING

        # Default to PASS for successful execution
        return ValidationStatus.PASS
    
    def _extract_actual_value(
        self,
        data: Dict[str, Any],
        full_result: Dict[str, Any]
    ) -> str:
        """Extract actual value for display.
        
        Args:
            data: Extracted data
            full_result: Full tool result
        
        Returns:
            String representation of actual value
        """
        # For tablespaces, show summary
        if "tablespaces" in full_result:
            tablespaces = full_result["tablespaces"]
            if tablespaces:
                usage_summary = ", ".join([
                    f"{t['tablespace_name']}: {t['used_pct']:.1f}%"
                    for t in tablespaces
                ])
                return usage_summary
        
        # For discovery, show what was found
        if "discovery" in full_result:
            discovery = full_result["discovery"]
            parts = []
            if discovery.get("sids"):
                parts.append(f"SIDs: {', '.join(discovery['sids'])}")
            if discovery.get("services"):
                parts.append(f"Services: {', '.join(discovery['services'])}")
            if parts:
                return "; ".join(parts)
        
        # For connection info
        if "connection" in full_result:
            return f"Connected via {full_result['connection'].get('via', 'unknown')}"
        
        # Default: show success
        return "Success"
    
    def _extract_value(self, data: Dict[str, Any], check_def: Any) -> Any:
        """Extract relevant value from tool result data."""
        # This would be customized based on check type
        # For now, return the whole data
        return data
    
    def _compare_values(self, actual: Any, expected: str) -> bool:
        """Compare actual value against expected criteria.
        
        Args:
            actual: Actual value from tool execution
            expected: Expected value or criteria string
        
        Returns:
            True if values match criteria
        """
        # Simple string comparison for now
        # In production, this would handle:
        # - Numeric comparisons (>, <, >=, <=)
        # - Range checks
        # - Pattern matching
        # - Complex criteria
        
        return str(actual) == expected


# Made with Bob