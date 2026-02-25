# Single Prompt Workflow: Discovery → Validation

**Purpose:** One prompt that discovers workloads and identifies validation tools

---

## The Complete Prompt

Copy and paste this into Claude Desktop:

```
I need you to perform a complete workload discovery and validation workflow on my server:

SERVER DETAILS:
- Host: <your-server-ip>
- SSH User: <your-username>
- SSH Password: <your-password>
- SSH Port: 22

WORKFLOW:
1. Discover the operating system using discover_os_only
2. Discover all applications using discover_applications
3. For any LOW confidence applications, use get_raw_server_data to get more details
4. Based on what you find, identify which validation tools are available:
   - For Oracle databases: oracle_db_* tools
   - For MongoDB: mongo_db_* tools
   - For VMs/Linux: vm_* tools
   - For network: net_* tools
5. Create a comprehensive report showing:
   - Operating system details
   - All discovered applications with confidence levels
   - Available validation tools for each discovered application
   - Recommended next steps for validation

Please execute this workflow step by step and provide a detailed report at the end.
```

---

## Example Output

When you use this prompt, Claude will:

### Step 1: OS Discovery
```
Discovering operating system...
✅ OS: Linux
✅ Distribution: Ubuntu 20.04 LTS
✅ Kernel: 5.4.0-42-generic
✅ Confidence: HIGH
```

### Step 2: Application Discovery
```
Discovering applications...
✅ Oracle Database 19c (HIGH confidence)
   - Process: ora_pmon_ORCLCDB
   - Port: 1521
   - Detection: process_scan + port_scan

✅ PostgreSQL 14.2 (HIGH confidence)
   - Process: postgres
   - Port: 5432
   - Detection: process_scan + port_scan

⚠️ Unknown Java Application (LOW confidence)
   - Process: java -jar /opt/myapp/server.jar
   - Port: 8080, 8443
   - Detection: process_scan
```

### Step 3: Enhanced Discovery (for LOW confidence)
```
Getting raw data for unknown Java application...
✅ Raw process data shows:
   java -Xmx4g -jar /opt/myapp/server.jar --spring.profiles.active=prod

Analysis: This is a Spring Boot application
- Type: REST API service
- Memory: 4GB heap
- Environment: Production
- Confidence upgraded to: MEDIUM
```

### Step 4: Validation Tools Mapping
```
Available validation tools for discovered applications:

1. Oracle Database 19c
   ✅ oracle_db_check_connectivity
   ✅ oracle_db_validate_instance
   ✅ oracle_db_check_tablespaces
   ✅ oracle_db_verify_backup_config
   
2. PostgreSQL 14.2
   ⚠️ No dedicated PostgreSQL validation tools available
   ✅ Can use: vm_check_service_status
   ✅ Can use: net_check_port
   
3. Spring Boot Application
   ⚠️ No dedicated validation tools
   ✅ Can use: vm_check_service_status
   ✅ Can use: net_check_port
   ✅ Can use: get_raw_server_data for logs/config
```

### Step 5: Comprehensive Report
```
=================================================================
WORKLOAD DISCOVERY & VALIDATION REPORT
=================================================================

SERVER: 10.0.1.5 (Ubuntu 20.04 LTS)

DISCOVERED WORKLOADS:
1. Oracle Database 19c (HIGH confidence)
2. PostgreSQL 14.2 (HIGH confidence)
3. Spring Boot REST API (MEDIUM confidence)

VALIDATION TOOLS AVAILABLE:
✅ Oracle Database: 4 dedicated tools
⚠️ PostgreSQL: Generic tools only
⚠️ Spring Boot: Generic tools only

RECOMMENDED NEXT STEPS:

For Oracle Database:
1. Run: oracle_db_check_connectivity
2. Run: oracle_db_validate_instance
3. Run: oracle_db_check_tablespaces

For PostgreSQL:
1. Run: vm_check_service_status (service: postgresql)
2. Run: net_check_port (port: 5432)
3. Consider manual validation

For Spring Boot Application:
1. Run: vm_check_service_status (check if running)
2. Run: net_check_port (ports: 8080, 8443)
3. Run: get_raw_server_data (collect logs)
4. Review /opt/myapp/logs/ manually

VALIDATION PRIORITY:
1. HIGH: Oracle Database (critical, has dedicated tools)
2. MEDIUM: PostgreSQL (important, generic tools)
3. LOW: Spring Boot (custom app, manual validation)

=================================================================
```

---

## Shorter Version (Quick Discovery)

If you want a faster version:

```
Discover all workloads on server <ip> (user: <user>, pass: <pass>) and tell me:
1. What's running (OS + applications)
2. Which validation tools I can use for each
3. What to validate first

Use discover_os_only, discover_applications, and get_raw_server_data as needed.
```

---

## Advanced Version (With Validation Execution)

If you want Claude to also run the validation:

```
Complete workflow for server <ip> (user: <user>, pass: <pass>):

PHASE 1 - DISCOVERY:
1. Discover OS and applications
2. Identify validation tools available

PHASE 2 - VALIDATION:
3. For each discovered application:
   - Run appropriate validation tools
   - Report validation results
   - Flag any issues found

PHASE 3 - REPORT:
4. Provide comprehensive report with:
   - What was discovered
   - What was validated
   - What passed/failed
   - Recommended actions

Execute all phases and provide detailed results.
```

---

## Customization Options

### Focus on Specific Applications

```
Discover workloads on <server> focusing on:
- Databases (Oracle, PostgreSQL, MongoDB, MySQL)
- Web servers (Apache, Nginx)
- Application servers (Tomcat, JBoss)

Then identify validation tools for each.
```

### Include Performance Checks

```
Discover workloads on <server> and:
1. Identify all applications
2. Find validation tools
3. Check resource usage (CPU, memory, disk)
4. Recommend optimization opportunities
```

### Security-Focused

```
Discover workloads on <server> with security focus:
1. Identify all running services
2. Check for known vulnerabilities
3. Verify security configurations
4. Recommend hardening steps
```

---

## Expected Tool Mappings

Claude will automatically map discovered applications to available tools:

### Database Applications

| Application | Validation Tools |
|-------------|------------------|
| Oracle Database | oracle_db_check_connectivity<br>oracle_db_validate_instance<br>oracle_db_check_tablespaces<br>oracle_db_verify_backup_config |
| MongoDB | mongo_db_check_connectivity<br>mongo_db_validate_replica_set<br>mongo_db_check_cluster_health |
| PostgreSQL | vm_check_service_status<br>net_check_port<br>get_raw_server_data |
| MySQL | vm_check_service_status<br>net_check_port<br>get_raw_server_data |

### Web/App Servers

| Application | Validation Tools |
|-------------|------------------|
| Apache | vm_check_service_status<br>net_check_port<br>get_raw_server_data |
| Nginx | vm_check_service_status<br>net_check_port<br>get_raw_server_data |
| Tomcat | vm_check_service_status<br>net_check_port<br>get_raw_server_data |

### System/Infrastructure

| Component | Validation Tools |
|-----------|------------------|
| Linux VM | vm_check_os_health<br>vm_check_disk_space<br>vm_check_service_status |
| Network | net_check_connectivity<br>net_check_port<br>net_trace_route |

---

## Tips for Best Results

### 1. Be Specific with Credentials
```
✅ Good: Host: 10.0.1.5, User: admin, Password: MyPass123
❌ Bad: Host: my server, User: the admin user
```

### 2. Request Detailed Output
```
✅ Good: "Provide detailed report with confidence levels"
❌ Bad: "Tell me what's on the server"
```

### 3. Ask for Prioritization
```
✅ Good: "Prioritize validation by criticality"
❌ Bad: "Validate everything"
```

### 4. Request Actionable Recommendations
```
✅ Good: "Recommend specific validation commands to run"
❌ Bad: "Tell me what to do"
```

---

## Troubleshooting

### Issue: Claude doesn't use all tools

**Solution:** Be explicit:
```
Use these tools in order:
1. discover_os_only
2. discover_applications
3. get_raw_server_data (for LOW confidence apps)
4. List available validation tools
```

### Issue: Missing validation tool mappings

**Solution:** Ask Claude to list all available tools first:
```
First, list all available tools you have.
Then discover workloads and map them to appropriate tools.
```

### Issue: Too much output

**Solution:** Request summary format:
```
Provide a summary table with:
- Application name
- Confidence level
- Available validation tools
- Priority (HIGH/MEDIUM/LOW)
```

---

## Real-World Example

**Prompt:**
```
Complete discovery and validation workflow for:
Host: 192.168.1.100
User: sysadmin
Password: SecurePass123

Focus on production databases and web services.
Prioritize by business criticality.
```

**Claude's Response:**
```
Executing discovery workflow...

PHASE 1: OS DISCOVERY
✅ Ubuntu 20.04 LTS (HIGH confidence)

PHASE 2: APPLICATION DISCOVERY
✅ Oracle Database 19c (HIGH confidence) - CRITICAL
✅ Apache HTTP Server 2.4 (HIGH confidence) - HIGH
✅ Redis 6.2 (MEDIUM confidence) - MEDIUM

PHASE 3: VALIDATION TOOL MAPPING
Oracle Database → 4 dedicated tools available
Apache → Generic tools (vm_check_service_status, net_check_port)
Redis → Generic tools (vm_check_service_status, net_check_port)

PHASE 4: PRIORITIZED VALIDATION PLAN
1. CRITICAL: Validate Oracle Database
   - oracle_db_check_connectivity
   - oracle_db_validate_instance
   - oracle_db_check_tablespaces
   
2. HIGH: Validate Apache
   - vm_check_service_status (service: apache2)
   - net_check_port (ports: 80, 443)
   
3. MEDIUM: Validate Redis
   - vm_check_service_status (service: redis)
   - net_check_port (port: 6379)

Ready to execute validation? (yes/no)
```

---

## Summary

**Single Prompt Benefits:**
- ✅ Complete workflow in one request
- ✅ Automatic tool mapping
- ✅ Prioritized recommendations
- ✅ Actionable next steps
- ✅ Comprehensive reporting

**Use this prompt to:**
1. Quickly assess new servers
2. Plan validation strategies
3. Identify gaps in tooling
4. Prioritize validation efforts
5. Generate audit reports

**Copy the prompt, customize with your server details, and paste into Claude Desktop!**