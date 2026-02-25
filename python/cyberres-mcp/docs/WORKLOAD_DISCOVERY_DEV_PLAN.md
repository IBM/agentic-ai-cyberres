# Workload Discovery Tool - Development Plan

**Version:** 1.0  
**Date:** 2026-02-11  
**Status:** Ready for Development

## Overview

This document provides a detailed, actionable development plan for implementing the workload discovery tool. It breaks down the technical plan into specific tasks with clear acceptance criteria and estimated effort.

---

## Development Approach

### Methodology
- **Iterative Development**: Build incrementally with working features at each stage
- **Test-Driven Development**: Write tests before implementation where practical
- **Continuous Integration**: Ensure each component integrates with existing system
- **Documentation-First**: Document APIs and usage as features are built

### Development Priorities
1. **Foundation First**: Core infrastructure and data models
2. **Linux Focus**: Start with Linux (most common in enterprise)
3. **High-Value Apps**: Prioritize most common enterprise applications
4. **Incremental Testing**: Test each component as it's built
5. **Integration**: Ensure seamless integration with existing plugins

---

## Sprint 1: Foundation & Core Infrastructure (Days 1-3)

### Goals
- Set up project structure
- Implement core data models
- Create basic SSH execution framework
- Build OS detection for Linux

### Tasks

#### Task 1.1: Project Structure Setup
**Effort:** 2 hours  
**Files to Create:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery.py`
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/__init__.py`
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/os_detector.py`
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/app_detector.py`
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/signatures.py`
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/confidence.py`
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/aggregator.py`

**Acceptance Criteria:**
- [ ] Directory structure created
- [ ] All files have proper copyright headers
- [ ] Basic imports and module structure in place

#### Task 1.2: Data Models Implementation
**Effort:** 4 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/models.py`

**Implementation:**
- Add all enums (OSType, OSDistribution, ApplicationCategory, etc.)
- Add OSInfo model
- Add NetworkBinding model
- Add ApplicationInstance model
- Add ContainerInfo model
- Add WorkloadDiscoveryResult model
- Add DiscoveryRequest model

**Acceptance Criteria:**
- [ ] All models defined with proper types
- [ ] Pydantic validation working
- [ ] Models can be serialized to JSON
- [ ] Unit tests for model validation

#### Task 1.3: OS Detector - Linux Implementation
**Effort:** 6 hours  
**Files to Create/Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/os_detector.py`

**Implementation:**
```python
class OSDetector:
    def detect(self, request: DiscoveryRequest) -> OSInfo
    def _detect_linux(self, ssh_exec_func) -> OSInfo
    def _parse_os_release(self, content: str) -> Dict
    def _parse_lsb_release(self, content: str) -> Dict
    def _detect_distribution(self, os_release: Dict) -> OSDistribution
    def _get_kernel_version(self, ssh_exec_func) -> str
    def _get_architecture(self, ssh_exec_func) -> str
    def _get_hostname(self, ssh_exec_func) -> str
    def _get_uptime(self, ssh_exec_func) -> int
```

**Detection Commands:**
- `cat /etc/os-release`
- `lsb_release -a`
- `uname -a`
- `cat /proc/version`
- `hostname`
- `cat /proc/uptime`

**Acceptance Criteria:**
- [ ] Detects RHEL, CentOS, Ubuntu, Debian, SUSE
- [ ] Extracts version numbers correctly
- [ ] Gets kernel version and architecture
- [ ] Handles missing files gracefully
- [ ] Returns confidence score
- [ ] Unit tests with mock SSH responses
- [ ] Integration test on real Linux VM

#### Task 1.4: Basic Plugin Registration
**Effort:** 2 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery.py`
- `python/cyberres-mcp/src/cyberres_mcp/server.py`

**Implementation:**
- Create `attach()` function in workload_discovery.py
- Implement `discover_os_only` tool
- Register plugin in server.py

**Acceptance Criteria:**
- [ ] Plugin loads without errors
- [ ] `discover_os_only` tool available via MCP
- [ ] Tool returns valid OSInfo structure
- [ ] Error handling works correctly

### Sprint 1 Deliverables
- ✅ Project structure established
- ✅ Core data models implemented
- ✅ Linux OS detection working
- ✅ Basic MCP tool registered
- ✅ Unit tests passing

---

## Sprint 2: Application Detection - Process & Port Scanning (Days 4-6)

### Goals
- Implement process-based detection
- Add port-based detection
- Create initial signature database
- Implement confidence scoring

### Tasks

#### Task 2.1: Signature Database
**Effort:** 4 hours  
**Files to Create:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/signatures.py`
- `python/cyberres-mcp/src/cyberres_mcp/resources/signatures/databases.json`
- `python/cyberres-mcp/src/cyberres_mcp/resources/signatures/web_servers.json`
- `python/cyberres-mcp/src/cyberres_mcp/resources/signatures/app_servers.json`
- `python/cyberres-mcp/src/cyberres_mcp/resources/signatures/containers.json`

**Implementation:**
```python
class SignatureDatabase:
    def __init__(self)
    def load_signatures(self) -> Dict[str, ApplicationSignature]
    def get_by_category(self, category: ApplicationCategory) -> List
    def match_process(self, process_name: str) -> List[Match]
    def match_port(self, port: int) -> List[Match]
    def add_custom(self, signature: ApplicationSignature)
    def list_all(self) -> List[Dict]
```

**Signature Format (JSON):**
```json
{
  "oracle": {
    "name": "Oracle Database",
    "category": "database",
    "vendor": "Oracle Corporation",
    "process_patterns": ["ora_pmon_.*", "oracle.*LISTENER"],
    "port_numbers": [1521, 1522],
    "config_paths": ["/u01/app/oracle/product/*/network/admin/listener.ora"],
    "package_names": ["oracle.*"],
    "service_names": ["oracle.*", "dbora"],
    "confidence_boost": 0.9
  }
}
```

**Initial Signatures (10 applications):**
- Oracle Database
- PostgreSQL
- MySQL/MariaDB
- MongoDB
- Apache HTTP Server
- Nginx
- Redis
- Docker
- Tomcat
- WebLogic

**Acceptance Criteria:**
- [ ] Signature database loads from JSON files
- [ ] Pattern matching works for processes
- [ ] Port matching works correctly
- [ ] Can add custom signatures
- [ ] Unit tests for signature matching

#### Task 2.2: Process Scanner
**Effort:** 5 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/app_detector.py`

**Implementation:**
```python
class ProcessScanner:
    def scan(self, ssh_exec_func) -> List[ProcessInfo]
    def _parse_ps_output(self, output: str) -> List[ProcessInfo]
    def _match_signatures(self, processes: List[ProcessInfo]) -> List[ApplicationInstance]
    def _extract_version(self, process: ProcessInfo) -> Optional[str]
    def _extract_config_paths(self, process: ProcessInfo) -> List[str]
```

**Commands:**
- Linux: `ps -eo pid,user,cmd --no-headers`
- Parse output and match against signatures

**Acceptance Criteria:**
- [ ] Scans all running processes
- [ ] Matches process names against signatures
- [ ] Extracts PIDs, users, command lines
- [ ] Identifies applications correctly
- [ ] Unit tests with mock process lists
- [ ] Integration test on test VM

#### Task 2.3: Port Scanner
**Effort:** 4 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/app_detector.py`

**Implementation:**
```python
class PortScanner:
    def scan(self, ssh_exec_func) -> List[NetworkBinding]
    def _parse_netstat_output(self, output: str) -> List[NetworkBinding]
    def _parse_ss_output(self, output: str) -> List[NetworkBinding]
    def _match_signatures(self, bindings: List[NetworkBinding]) -> List[ApplicationInstance]
    def _correlate_with_processes(self, bindings: List, processes: List) -> List
```

**Commands:**
- Linux: `ss -tulpn` or `netstat -tulpn`
- Parse listening ports and associated processes

**Acceptance Criteria:**
- [ ] Scans all listening ports
- [ ] Matches ports against signatures
- [ ] Correlates ports with processes
- [ ] Handles both IPv4 and IPv6
- [ ] Unit tests with mock netstat output

#### Task 2.4: Confidence Scorer
**Effort:** 3 hours  
**Files to Create:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/confidence.py`

**Implementation:**
```python
class ConfidenceScorer:
    METHOD_CONFIDENCE = {...}
    
    def calculate_confidence(
        self,
        detection_methods: List[DetectionMethod],
        signature_matches: int,
        version_detected: bool,
        config_found: bool,
        process_found: bool,
        port_matches: int
    ) -> tuple[float, ConfidenceLevel]
    
    def apply_boost_rules(self, app: ApplicationInstance) -> float
```

**Acceptance Criteria:**
- [ ] Calculates confidence scores correctly
- [ ] Applies boost rules for correlated findings
- [ ] Returns appropriate confidence levels
- [ ] Unit tests for various scenarios

### Sprint 2 Deliverables
- ✅ Signature database with 10 applications
- ✅ Process scanning working
- ✅ Port scanning working
- ✅ Confidence scoring implemented
- ✅ Integration tests passing

---

## Sprint 3: Application Detection - Advanced Methods (Days 7-9)

### Goals
- Add package manager detection
- Implement service enumeration
- Add configuration file detection
- Implement result aggregation

### Tasks

#### Task 3.1: Package Manager Detection
**Effort:** 5 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/app_detector.py`

**Implementation:**
```python
class PackageScanner:
    def scan(self, ssh_exec_func, os_info: OSInfo) -> List[PackageInfo]
    def _scan_rpm(self, ssh_exec_func) -> List[PackageInfo]
    def _scan_dpkg(self, ssh_exec_func) -> List[PackageInfo]
    def _match_signatures(self, packages: List[PackageInfo]) -> List[ApplicationInstance]
    def _get_package_details(self, ssh_exec_func, package_name: str) -> Dict
```

**Commands:**
- RPM: `rpm -qa`, `rpm -qi <package>`
- DPKG: `dpkg -l`, `dpkg -s <package>`

**Acceptance Criteria:**
- [ ] Detects installed packages
- [ ] Works with RPM-based systems
- [ ] Works with DEB-based systems
- [ ] Extracts version information
- [ ] Matches against signatures

#### Task 3.2: Service Enumeration
**Effort:** 4 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/app_detector.py`

**Implementation:**
```python
class ServiceScanner:
    def scan(self, ssh_exec_func, os_info: OSInfo) -> List[ServiceInfo]
    def _scan_systemd(self, ssh_exec_func) -> List[ServiceInfo]
    def _scan_initd(self, ssh_exec_func) -> List[ServiceInfo]
    def _match_signatures(self, services: List[ServiceInfo]) -> List[ApplicationInstance]
```

**Commands:**
- systemd: `systemctl list-units --type=service --all --no-pager`
- init.d: `ls -1 /etc/init.d/`

**Acceptance Criteria:**
- [ ] Lists all services
- [ ] Detects service status
- [ ] Works with systemd
- [ ] Works with init.d
- [ ] Matches against signatures

#### Task 3.3: Configuration File Detection
**Effort:** 4 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/app_detector.py`

**Implementation:**
```python
class ConfigScanner:
    def scan(self, ssh_exec_func, applications: List[ApplicationInstance]) -> List[ApplicationInstance]
    def _find_config_files(self, ssh_exec_func, paths: List[str]) -> List[str]
    def _parse_config(self, ssh_exec_func, path: str) -> Dict
    def _extract_version_from_config(self, config: Dict) -> Optional[str]
```

**Acceptance Criteria:**
- [ ] Finds configuration files
- [ ] Parses common config formats
- [ ] Extracts version information
- [ ] Enhances application details

#### Task 3.4: Result Aggregator
**Effort:** 5 hours  
**Files to Create:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/aggregator.py`

**Implementation:**
```python
class ResultAggregator:
    def aggregate(
        self,
        request: DiscoveryRequest,
        os_info: OSInfo,
        applications: List[ApplicationInstance],
        container_info: Optional[ContainerInfo],
        start_time: float
    ) -> WorkloadDiscoveryResult
    
    def _deduplicate_applications(self, apps: List) -> List
    def _merge_detections(self, apps: List) -> List
    def _calculate_statistics(self, apps: List) -> Dict
    def _filter_by_confidence(self, apps: List, min_conf: ConfidenceLevel) -> List
```

**Acceptance Criteria:**
- [ ] Deduplicates findings from multiple methods
- [ ] Merges related detections
- [ ] Calculates summary statistics
- [ ] Filters by confidence level
- [ ] Creates complete result structure

### Sprint 3 Deliverables
- ✅ Package manager detection working
- ✅ Service enumeration working
- ✅ Configuration file detection working
- ✅ Result aggregation implemented
- ✅ Multi-method detection validated

---

## Sprint 4: Main Tool Implementation & Container Detection (Days 10-12)

### Goals
- Implement main `discover_workload` tool
- Add container detection
- Implement error handling
- Add performance optimizations

### Tasks

#### Task 4.1: Main Discovery Tool
**Effort:** 6 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery.py`

**Implementation:**
- Complete `discover_workload` tool
- Orchestrate all detection methods
- Handle timeouts
- Collect errors and warnings
- Format final output

**Acceptance Criteria:**
- [ ] Tool executes full discovery workflow
- [ ] All detection methods integrated
- [ ] Timeout handling works
- [ ] Error collection works
- [ ] Returns complete WorkloadDiscoveryResult

#### Task 4.2: Container Detection
**Effort:** 5 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/app_detector.py`

**Implementation:**
```python
class ContainerDetector:
    def detect_containers(self, ssh_exec_func) -> Optional[ContainerInfo]
    def _detect_docker(self, ssh_exec_func) -> Dict
    def _detect_kubernetes(self, ssh_exec_func) -> Dict
    def _detect_containerd(self, ssh_exec_func) -> Dict
```

**Commands:**
- Docker: `docker version`, `docker info`, `docker ps`
- Kubernetes: `kubectl version`, `kubectl get nodes`
- containerd: `ctr version`

**Acceptance Criteria:**
- [ ] Detects Docker runtime
- [ ] Detects Kubernetes
- [ ] Gets container counts
- [ ] Gets image counts
- [ ] Handles missing runtimes gracefully

#### Task 4.3: Error Handling & Partial Discovery
**Effort:** 4 hours  
**Files to Modify:**
- All detector files

**Implementation:**
- Add try-catch blocks around all detection methods
- Collect errors in structured format
- Support partial results
- Add warning messages

**Acceptance Criteria:**
- [ ] Handles SSH failures gracefully
- [ ] Continues on partial failures
- [ ] Collects all errors
- [ ] Returns partial results when possible
- [ ] Clear error messages

#### Task 4.4: Performance Optimization
**Effort:** 4 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/app_detector.py`

**Implementation:**
- Batch SSH commands where possible
- Implement command caching
- Optimize command execution order
- Add parallel execution for independent checks

**Acceptance Criteria:**
- [ ] Discovery completes in < 60 seconds
- [ ] Commands batched efficiently
- [ ] No redundant SSH connections
- [ ] Performance tests passing

### Sprint 4 Deliverables
- ✅ Main discovery tool working end-to-end
- ✅ Container detection implemented
- ✅ Robust error handling
- ✅ Performance optimized
- ✅ Integration tests passing

---

## Sprint 5: Additional Tools & Extensibility (Days 13-15)

### Goals
- Implement signature management tools
- Add custom signature support
- Create comprehensive tests
- Write documentation

### Tasks

#### Task 5.1: Signature Management Tools
**Effort:** 4 hours  
**Files to Modify:**
- `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery.py`

**Implementation:**
- Implement `list_application_signatures` tool
- Implement `add_custom_signature` tool
- Add signature validation

**Acceptance Criteria:**
- [ ] Can list all signatures
- [ ] Can add custom signatures
- [ ] Signatures persist across restarts
- [ ] Validation prevents invalid signatures

#### Task 5.2: Expand Signature Database
**Effort:** 6 hours  
**Files to Create/Modify:**
- Add 40+ more application signatures

**Applications to Add:**
- Databases: MSSQL, Cassandra, CouchDB, InfluxDB
- Web Servers: IIS, Lighttpd, Caddy
- App Servers: JBoss, WebSphere, GlassFish
- Message Queues: ActiveMQ, ZeroMQ
- Caching: Varnish, HAProxy
- Monitoring: Prometheus, Grafana, Nagios
- And more...

**Acceptance Criteria:**
- [ ] 50+ applications in signature database
- [ ] All major categories covered
- [ ] Signatures tested and validated

#### Task 5.3: Comprehensive Testing
**Effort:** 8 hours  
**Files to Create:**
- `python/cyberres-mcp/tests/test_workload_discovery.py`
- `python/cyberres-mcp/tests/test_os_detector.py`
- `python/cyberres-mcp/tests/test_app_detector.py`
- `python/cyberres-mcp/tests/test_confidence.py`
- `python/cyberres-mcp/tests/integration/test_discovery_integration.py`

**Test Coverage:**
- Unit tests for all components
- Integration tests on test VMs
- Mock SSH responses for unit tests
- Edge case testing
- Performance testing

**Acceptance Criteria:**
- [ ] 80%+ code coverage
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Performance benchmarks met

#### Task 5.4: Documentation
**Effort:** 6 hours  
**Files to Create:**
- `python/cyberres-mcp/docs/WORKLOAD_DISCOVERY_USER_GUIDE.md`
- `python/cyberres-mcp/docs/WORKLOAD_DISCOVERY_API.md`
- Update `python/cyberres-mcp/README.md`

**Content:**
- User guide with examples
- API reference for all tools
- Signature creation guide
- Troubleshooting guide
- Integration examples

**Acceptance Criteria:**
- [ ] Complete user documentation
- [ ] API reference complete
- [ ] Examples working
- [ ] README updated

### Sprint 5 Deliverables
- ✅ Signature management tools working
- ✅ 50+ applications in database
- ✅ Comprehensive test suite
- ✅ Complete documentation
- ✅ Ready for production use

---

## Implementation Checklist

### Phase 1: Foundation ✓
- [ ] Project structure created
- [ ] Data models implemented
- [ ] OS detection working (Linux)
- [ ] Basic plugin registered
- [ ] Unit tests passing

### Phase 2: Core Detection ✓
- [ ] Signature database created (10 apps)
- [ ] Process scanning working
- [ ] Port scanning working
- [ ] Confidence scoring implemented
- [ ] Integration tests passing

### Phase 3: Advanced Detection ✓
- [ ] Package manager detection
- [ ] Service enumeration
- [ ] Configuration file detection
- [ ] Result aggregation
- [ ] Multi-method validation

### Phase 4: Complete Tool ✓
- [ ] Main discovery tool working
- [ ] Container detection
- [ ] Error handling robust
- [ ] Performance optimized
- [ ] End-to-end tests passing

### Phase 5: Production Ready ✓
- [ ] Signature management tools
- [ ] 50+ applications supported
- [ ] Comprehensive tests (80%+ coverage)
- [ ] Complete documentation
- [ ] Ready for deployment

---

## Success Criteria

### Functional Requirements
- ✅ Detects OS on Linux systems (RHEL, Ubuntu, Debian, SUSE)
- ✅ Identifies 50+ enterprise applications
- ✅ Multi-method detection (process, port, package, service, config)
- ✅ Confidence scoring working correctly
- ✅ Container detection (Docker, Kubernetes)
- ✅ Extensible signature system
- ✅ Robust error handling

### Performance Requirements
- ✅ Full discovery < 60 seconds
- ✅ OS-only discovery < 5 seconds
- ✅ Minimal server impact (< 5% CPU)
- ✅ Efficient SSH usage (batched commands)

### Quality Requirements
- ✅ 80%+ test coverage
- ✅ 90%+ detection accuracy
- ✅ < 5% false positive rate
- ✅ Graceful error handling
- ✅ Complete documentation

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Set up development environment** with test VMs
3. **Begin Sprint 1** - Foundation implementation
4. **Daily standups** to track progress
5. **Sprint reviews** after each sprint
6. **Continuous integration** with existing codebase

---

**Ready to Start Development!**

Switch to Code mode to begin implementation of Sprint 1.