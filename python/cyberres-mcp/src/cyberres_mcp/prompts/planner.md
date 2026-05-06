Given a ValidationRequest JSON, create a COMPREHENSIVE validation plan that ensures production readiness.

VALIDATION PHILOSOPHY:
Select ALL relevant tools across multiple validation layers to thoroughly validate the target resource:

1. **Network Layer**: Always verify connectivity to all required ports
2. **Application Layer**: Validate application-specific functionality and health
3. **Infrastructure Layer**: Verify underlying VM/system health (for VM-based resources)
4. **Data Layer**: Validate data integrity where applicable

TOOL SELECTION GUIDELINES:

1. **Network Connectivity** (ALWAYS include):
   - ``tcp_portcheck`` for relevant ports (SSH port 22 for VMs, 1521 for Oracle, 27017 for MongoDB)

2. **For VM resources**:
   - ``vm_linux_uptime_load_mem`` (system load, memory, uptime)
   - ``vm_linux_fs_usage`` (filesystem usage and capacity)
   - ``vm_linux_services`` (service status verification)

3. **For Oracle Database** (on VM):
   - Network: ``tcp_portcheck`` (ports 22, 1521)
   - Database: ``db_oracle_connect`` → ``db_oracle_tablespaces`` → ``db_oracle_data_validation``
   - Infrastructure: ``vm_linux_uptime_load_mem`` → ``vm_linux_fs_usage`` → ``vm_linux_services``

4. **For MongoDB** (on VM):
   - Network: ``tcp_portcheck`` (ports 22, 27017)
   - Database: ``db_mongo_connect`` → ``db_mongo_rs_status`` (if replica set) → ``db_mongo_ssh_validate_collection`` (if data validation needed)
   - Infrastructure: ``vm_linux_uptime_load_mem`` → ``vm_linux_fs_usage`` → ``vm_linux_services``

IMPORTANT:
- For database resources running on VMs, include BOTH database-specific AND VM infrastructure tools
- Include replica set/HA checks for production databases (e.g., ``db_mongo_rs_status`` for MongoDB)
- Include data validation tools where applicable
- Aim for COMPREHENSIVE validation, not minimal validation

Output your plan as JSON in the form ``{"steps":[{"tool":"tool_name","args":{...}}, ...]}`` with the tool names and arguments filled in.