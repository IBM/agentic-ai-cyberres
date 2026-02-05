#
# Copyright contributors to the agentic-ai-cyberres project
#
"""Result evaluation for recovery validation agent."""

import json
import logging
import os
import re
from typing import Dict, Any, List, Optional
from models import ResourceType, ValidationStatus, CheckResult, ResourceValidationResult
from executor import ExecutionResult

logger = logging.getLogger(__name__)


class AcceptanceCriteria:
    """Acceptance criteria for validation."""
    
    def __init__(self, criteria: Dict[str, Any]):
        """Initialize acceptance criteria.
        
        Args:
            criteria: Criteria dictionary
        """
        self.criteria = criteria
    
    @classmethod
    def load_from_file(cls, resource_type: ResourceType) -> "AcceptanceCriteria":
        """Load acceptance criteria from file.
        
        Args:
            resource_type: Type of resource
        
        Returns:
            AcceptanceCriteria instance
        """
        # Determine file path based on resource type
        base_dir = os.path.dirname(os.path.dirname(__file__))
        resource_dir = os.path.join(base_dir, "cyberres-mcp", "resources", "acceptance")
        
        filename_map = {
            ResourceType.VM: "vm-core.json",
            ResourceType.ORACLE: "db-oracle.json",
            ResourceType.MONGODB: "db-mongo.json"
        }
        
        filepath = os.path.join(resource_dir, filename_map[resource_type])
        
        try:
            with open(filepath, 'r') as f:
                criteria = json.load(f)
            logger.info(f"Loaded acceptance criteria from {filepath}")
            return cls(criteria)
        except FileNotFoundError:
            logger.warning(f"Acceptance criteria file not found: {filepath}, using defaults")
            return cls({})
        except Exception as e:
            logger.error(f"Error loading acceptance criteria: {e}")
            return cls({})


class ResultEvaluator:
    """Evaluate validation results against acceptance criteria."""
    
    def __init__(self, acceptance_criteria: Optional[AcceptanceCriteria] = None):
        """Initialize result evaluator.
        
        Args:
            acceptance_criteria: Acceptance criteria (optional)
        """
        self.acceptance_criteria = acceptance_criteria
    
    def evaluate_vm_results(
        self,
        results: List[ExecutionResult],
        criteria: Dict[str, Any]
    ) -> List[CheckResult]:
        """Evaluate VM validation results.
        
        Args:
            results: List of execution results
            criteria: Acceptance criteria
        
        Returns:
            List of CheckResult
        """
        checks = []
        
        # Default criteria
        fs_max_pct = criteria.get("fs_max_pct", 85)
        mem_min_free_pct = criteria.get("mem_min_free_pct", 10)
        required_services = criteria.get("required_services", [])
        
        for result in results:
            if result.step_id == "vm_network_check":
                # Network connectivity check
                if result.success and result.result.get("ok"):
                    port_results = result.result.get("results", [])
                    all_ok = result.result.get("all_ok", False)
                    
                    checks.append(CheckResult(
                        check_id="vm_network_ssh",
                        check_name="SSH Port Connectivity",
                        status=ValidationStatus.PASS if all_ok else ValidationStatus.FAIL,
                        expected="SSH port accessible",
                        actual=f"Port check: {all_ok}",
                        message="SSH port is accessible" if all_ok else "SSH port not accessible",
                        details={"port_results": port_results}
                    ))
                else:
                    checks.append(CheckResult(
                        check_id="vm_network_ssh",
                        check_name="SSH Port Connectivity",
                        status=ValidationStatus.ERROR,
                        expected="SSH port accessible",
                        actual="Check failed",
                        message=result.error or "Network check failed"
                    ))
            
            elif result.step_id == "vm_uptime_load_mem":
                # Memory check
                if result.success and result.result.get("ok"):
                    stdout = result.result.get("stdout", "")
                    
                    # Parse memory info from /proc/meminfo
                    mem_total = None
                    mem_free = None
                    mem_available = None
                    
                    for line in stdout.split('\n'):
                        if 'MemTotal:' in line:
                            mem_total = int(re.search(r'(\d+)', line).group(1))
                        elif 'MemFree:' in line:
                            mem_free = int(re.search(r'(\d+)', line).group(1))
                        elif 'MemAvailable:' in line:
                            mem_available = int(re.search(r'(\d+)', line).group(1))
                    
                    if mem_total and (mem_available or mem_free):
                        free_mem = mem_available if mem_available else mem_free
                        free_pct = (free_mem / mem_total) * 100
                        
                        status = ValidationStatus.PASS if free_pct >= mem_min_free_pct else ValidationStatus.FAIL
                        
                        checks.append(CheckResult(
                            check_id="vm_memory_free",
                            check_name="Memory Free Percentage",
                            status=status,
                            expected=f">= {mem_min_free_pct}%",
                            actual=f"{free_pct:.1f}%",
                            message=f"Memory free: {free_pct:.1f}%" if status == ValidationStatus.PASS else f"Low memory: {free_pct:.1f}% < {mem_min_free_pct}%",
                            details={"mem_total_kb": mem_total, "mem_free_kb": free_mem}
                        ))
                    else:
                        checks.append(CheckResult(
                            check_id="vm_memory_free",
                            check_name="Memory Free Percentage",
                            status=ValidationStatus.WARNING,
                            expected=f">= {mem_min_free_pct}%",
                            actual="Could not parse memory info",
                            message="Unable to parse memory information"
                        ))
                else:
                    checks.append(CheckResult(
                        check_id="vm_memory_free",
                        check_name="Memory Free Percentage",
                        status=ValidationStatus.ERROR,
                        expected=f">= {mem_min_free_pct}%",
                        actual="Check failed",
                        message=result.error or "Memory check failed"
                    ))
            
            elif result.step_id == "vm_fs_usage":
                # Filesystem usage checks
                if result.success and result.result.get("ok"):
                    filesystems = result.result.get("filesystems", [])
                    
                    for fs in filesystems:
                        use_pct = fs.get("use_pct")
                        mountpoint = fs.get("mountpoint", "unknown")
                        
                        if use_pct is not None:
                            status = ValidationStatus.PASS if use_pct <= fs_max_pct else ValidationStatus.FAIL
                            
                            checks.append(CheckResult(
                                check_id=f"vm_fs_usage_{mountpoint.replace('/', '_')}",
                                check_name=f"Filesystem Usage: {mountpoint}",
                                status=status,
                                expected=f"<= {fs_max_pct}%",
                                actual=f"{use_pct}%",
                                message=f"Filesystem {mountpoint}: {use_pct}% used" if status == ValidationStatus.PASS else f"Filesystem {mountpoint} over threshold: {use_pct}% > {fs_max_pct}%",
                                details=fs
                            ))
                else:
                    checks.append(CheckResult(
                        check_id="vm_fs_usage",
                        check_name="Filesystem Usage",
                        status=ValidationStatus.ERROR,
                        expected=f"<= {fs_max_pct}%",
                        actual="Check failed",
                        message=result.error or "Filesystem check failed"
                    ))
            
            elif result.step_id == "vm_services_check":
                # Services check
                if result.success and result.result.get("ok"):
                    missing = result.result.get("missing", [])
                    running = result.result.get("running", [])
                    
                    status = ValidationStatus.PASS if not missing else ValidationStatus.FAIL
                    
                    checks.append(CheckResult(
                        check_id="vm_services_required",
                        check_name="Required Services Running",
                        status=status,
                        expected=f"All {len(required_services)} required services running",
                        actual=f"{len(running)} running, {len(missing)} missing",
                        message="All required services are running" if status == ValidationStatus.PASS else f"Missing services: {', '.join(missing)}",
                        details={"running": running, "missing": missing}
                    ))
                else:
                    checks.append(CheckResult(
                        check_id="vm_services_required",
                        check_name="Required Services Running",
                        status=ValidationStatus.ERROR,
                        expected="All required services running",
                        actual="Check failed",
                        message=result.error or "Services check failed"
                    ))
        
        return checks
    
    def evaluate_oracle_results(
        self,
        results: List[ExecutionResult],
        criteria: Dict[str, Any]
    ) -> List[CheckResult]:
        """Evaluate Oracle validation results.
        
        Args:
            results: List of execution results
            criteria: Acceptance criteria
        
        Returns:
            List of CheckResult
        """
        checks = []
        
        # Default criteria
        tablespace_min_free_pct = criteria.get("tablespace_min_free_pct", 15)
        
        for result in results:
            if result.step_id == "oracle_network_check":
                # Network connectivity check
                if result.success and result.result.get("ok"):
                    all_ok = result.result.get("all_ok", False)
                    
                    checks.append(CheckResult(
                        check_id="oracle_network_port",
                        check_name="Oracle Port Connectivity",
                        status=ValidationStatus.PASS if all_ok else ValidationStatus.FAIL,
                        expected="Oracle port accessible",
                        actual=f"Port check: {all_ok}",
                        message="Oracle port is accessible" if all_ok else "Oracle port not accessible"
                    ))
                else:
                    checks.append(CheckResult(
                        check_id="oracle_network_port",
                        check_name="Oracle Port Connectivity",
                        status=ValidationStatus.ERROR,
                        expected="Oracle port accessible",
                        actual="Check failed",
                        message=result.error or "Network check failed"
                    ))
            
            elif result.step_id == "oracle_connect":
                # Database connection check
                if result.success and result.result.get("ok"):
                    instance_name = result.result.get("instance_name", "unknown")
                    version = result.result.get("version", "unknown")
                    open_mode = result.result.get("open_mode", "unknown")
                    
                    checks.append(CheckResult(
                        check_id="oracle_connection",
                        check_name="Oracle Database Connection",
                        status=ValidationStatus.PASS,
                        expected="Connection successful",
                        actual=f"Connected to {instance_name} ({version})",
                        message=f"Successfully connected to Oracle instance {instance_name}",
                        details={"instance_name": instance_name, "version": version, "open_mode": open_mode}
                    ))
                else:
                    checks.append(CheckResult(
                        check_id="oracle_connection",
                        check_name="Oracle Database Connection",
                        status=ValidationStatus.FAIL,
                        expected="Connection successful",
                        actual="Connection failed",
                        message=result.error or "Database connection failed"
                    ))
            
            elif result.step_id == "oracle_tablespaces":
                # Tablespace usage checks
                if result.success and result.result.get("ok"):
                    tablespaces = result.result.get("tablespaces", [])
                    
                    for ts in tablespaces:
                        ts_name = ts.get("tablespace_name", "unknown")
                        free_mb = ts.get("free_mb", 0)
                        used_pct = ts.get("used_pct", 0)
                        
                        free_pct = 100 - used_pct
                        status = ValidationStatus.PASS if free_pct >= tablespace_min_free_pct else ValidationStatus.FAIL
                        
                        checks.append(CheckResult(
                            check_id=f"oracle_tablespace_{ts_name}",
                            check_name=f"Tablespace: {ts_name}",
                            status=status,
                            expected=f">= {tablespace_min_free_pct}% free",
                            actual=f"{free_pct:.1f}% free ({free_mb:.1f} MB)",
                            message=f"Tablespace {ts_name}: {free_pct:.1f}% free" if status == ValidationStatus.PASS else f"Tablespace {ts_name} low on space: {free_pct:.1f}% < {tablespace_min_free_pct}%",
                            details=ts
                        ))
                else:
                    checks.append(CheckResult(
                        check_id="oracle_tablespaces",
                        check_name="Tablespace Usage",
                        status=ValidationStatus.ERROR,
                        expected="Tablespace info retrieved",
                        actual="Check failed",
                        message=result.error or "Tablespace check failed"
                    ))
        
        return checks
    
    def evaluate_mongodb_results(
        self,
        results: List[ExecutionResult],
        criteria: Dict[str, Any]
    ) -> List[CheckResult]:
        """Evaluate MongoDB validation results.
        
        Args:
            results: List of execution results
            criteria: Acceptance criteria
        
        Returns:
            List of CheckResult
        """
        checks = []
        
        # Default criteria
        allowed_states = criteria.get("replication", {}).get("allowed_states", [1, 2])
        
        for result in results:
            if result.step_id == "mongodb_network_check":
                # Network connectivity check
                if result.success and result.result.get("ok"):
                    all_ok = result.result.get("all_ok", False)
                    
                    checks.append(CheckResult(
                        check_id="mongodb_network_port",
                        check_name="MongoDB Port Connectivity",
                        status=ValidationStatus.PASS if all_ok else ValidationStatus.FAIL,
                        expected="MongoDB port accessible",
                        actual=f"Port check: {all_ok}",
                        message="MongoDB port is accessible" if all_ok else "MongoDB port not accessible"
                    ))
                else:
                    checks.append(CheckResult(
                        check_id="mongodb_network_port",
                        check_name="MongoDB Port Connectivity",
                        status=ValidationStatus.ERROR,
                        expected="MongoDB port accessible",
                        actual="Check failed",
                        message=result.error or "Network check failed"
                    ))
            
            elif result.step_id == "mongodb_connect":
                # Database connection check
                if result.success and result.result.get("ok"):
                    version = result.result.get("version", "unknown")
                    
                    checks.append(CheckResult(
                        check_id="mongodb_connection",
                        check_name="MongoDB Connection",
                        status=ValidationStatus.PASS,
                        expected="Connection successful",
                        actual=f"Connected (version {version})",
                        message=f"Successfully connected to MongoDB version {version}",
                        details={"version": version}
                    ))
                else:
                    checks.append(CheckResult(
                        check_id="mongodb_connection",
                        check_name="MongoDB Connection",
                        status=ValidationStatus.FAIL,
                        expected="Connection successful",
                        actual="Connection failed",
                        message=result.error or "Database connection failed"
                    ))
            
            elif result.step_id == "mongodb_replica_status":
                # Replica set status check
                if result.success and result.result.get("ok"):
                    my_state = result.result.get("myState")
                    set_name = result.result.get("set", "unknown")
                    
                    if my_state is not None:
                        status = ValidationStatus.PASS if my_state in allowed_states else ValidationStatus.FAIL
                        
                        state_names = {1: "PRIMARY", 2: "SECONDARY", 7: "ARBITER"}
                        state_name = state_names.get(my_state, f"STATE_{my_state}")
                        
                        checks.append(CheckResult(
                            check_id="mongodb_replica_state",
                            check_name="Replica Set State",
                            status=status,
                            expected=f"State in {allowed_states}",
                            actual=f"State: {my_state} ({state_name})",
                            message=f"Replica set {set_name} in valid state: {state_name}" if status == ValidationStatus.PASS else f"Replica set {set_name} in unexpected state: {state_name}",
                            details={"set": set_name, "myState": my_state}
                        ))
                else:
                    # Not being a replica set is not necessarily a failure
                    checks.append(CheckResult(
                        check_id="mongodb_replica_state",
                        check_name="Replica Set State",
                        status=ValidationStatus.SKIPPED,
                        expected="Replica set status",
                        actual="Not a replica set or check failed",
                        message="Not configured as replica set or check failed"
                    ))
            
            elif result.step_id == "mongodb_collection_validate":
                # Collection validation check
                if result.success and result.result.get("ok"):
                    validate_data = result.result.get("validate", {})
                    valid = validate_data.get("valid", False)
                    errors = validate_data.get("errors", [])
                    warnings = validate_data.get("warnings", [])
                    
                    status = ValidationStatus.PASS if valid and not errors else ValidationStatus.FAIL
                    if warnings and status == ValidationStatus.PASS:
                        status = ValidationStatus.WARNING
                    
                    checks.append(CheckResult(
                        check_id="mongodb_collection_valid",
                        check_name="Collection Validation",
                        status=status,
                        expected="Collection valid",
                        actual=f"Valid: {valid}, Errors: {len(errors)}, Warnings: {len(warnings)}",
                        message="Collection validation passed" if status == ValidationStatus.PASS else f"Collection validation issues: {len(errors)} errors, {len(warnings)} warnings",
                        details={"errors": errors, "warnings": warnings}
                    ))
                else:
                    checks.append(CheckResult(
                        check_id="mongodb_collection_valid",
                        check_name="Collection Validation",
                        status=ValidationStatus.ERROR,
                        expected="Collection valid",
                        actual="Check failed",
                        message=result.error or "Collection validation failed"
                    ))
        
        return checks
    
    def evaluate(
        self,
        resource_type: ResourceType,
        results: List[ExecutionResult],
        custom_criteria: Optional[Dict[str, Any]] = None
    ) -> ResourceValidationResult:
        """Evaluate validation results.
        
        Args:
            resource_type: Type of resource
            results: List of execution results
            custom_criteria: Custom acceptance criteria (optional)
        
        Returns:
            ResourceValidationResult
        """
        # Load acceptance criteria if not provided
        if self.acceptance_criteria is None:
            self.acceptance_criteria = AcceptanceCriteria.load_from_file(resource_type)
        
        # Merge custom criteria
        criteria = dict(self.acceptance_criteria.criteria)
        if custom_criteria:
            criteria.update(custom_criteria)
        
        # Evaluate based on resource type
        if resource_type == ResourceType.VM:
            checks = self.evaluate_vm_results(results, criteria)
        elif resource_type == ResourceType.ORACLE:
            checks = self.evaluate_oracle_results(results, criteria)
        elif resource_type == ResourceType.MONGODB:
            checks = self.evaluate_mongodb_results(results, criteria)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        
        # Calculate overall status and score
        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c.status == ValidationStatus.PASS)
        failed_checks = sum(1 for c in checks if c.status == ValidationStatus.FAIL)
        
        # Calculate score (0-100)
        if total_checks > 0:
            score = int((passed_checks / total_checks) * 100)
        else:
            score = 0
        
        # Determine overall status
        if failed_checks > 0:
            overall_status = ValidationStatus.FAIL
        elif any(c.status == ValidationStatus.ERROR for c in checks):
            overall_status = ValidationStatus.ERROR
        elif any(c.status == ValidationStatus.WARNING for c in checks):
            overall_status = ValidationStatus.WARNING
        else:
            overall_status = ValidationStatus.PASS
        
        # Calculate execution time
        execution_time = sum(r.execution_time for r in results)
        
        # Extract host from results
        host = "unknown"
        for result in results:
            if "host" in result.result:
                host = result.result["host"]
                break
        
        return ResourceValidationResult(
            resource_type=resource_type,
            resource_host=host,
            overall_status=overall_status,
            score=score,
            checks=checks,
            execution_time_seconds=execution_time
        )

# Made with Bob
