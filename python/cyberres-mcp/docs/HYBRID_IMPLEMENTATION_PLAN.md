# Hybrid Architecture Implementation Plan

**Decision:** Implement Option 3 - Hybrid Approach  
**Status:** Planning Phase  
**Target:** Sprint 3 Implementation

---

## Executive Summary

We will implement a hybrid architecture that combines:
1. **Fast signature-based detection** in MCP server (already done in Sprint 1-2)
2. **Raw data access tool** in MCP server (new in Sprint 3)
3. **LLM enhancement logic** in Agent/Client (new in Sprint 3)

This gives us the best of both worlds: speed + intelligence.

---

## Current State (Sprint 1-2 Complete)

### ✅ What We Have

**MCP Server Tools:**
```python
# Tool 1: discover_os_only
# - Detects operating system
# - Returns: OSInfo with distribution, version, confidence

# Tool 2: discover_applications
# - Fast signature-based detection
# - Returns: List of ApplicationInfo with confidence scores
```

**Signature Database:**
```json
{
  "applications": [
    {
      "name": "Oracle Database",
      "category": "database",
      "process_patterns": ["ora_pmon_.*", "ora_smon_.*"],
      "ports": [1521, 1522, 1526, 1529]
    }
    // ... 17 more applications
  ]
}
```

**Detection Flow:**
```
User → Agent → MCP Tool (discover_applications)
                ↓
         Signature Matching
                ↓
         Structured Results
```

---

## Target State (Sprint 3 - Hybrid)

### 🎯 What We'll Add

**New MCP Server Tool:**
```python
# Tool 3: get_raw_server_data (NEW)
# - Returns raw process list, port list, config files
# - For agent-side LLM processing
# - Flexible data collection
```

**Agent Enhancement Logic:**
```python
# Agent workflow (NEW)
1. Call discover_applications (fast path)
2. Identify LOW confidence detections
3. Call get_raw_server_data for those cases
4. Use LLM to enhance/identify
5. Return complete results
```

**Enhanced Detection Flow:**
```
User → Agent → discover_applications (fast)
                ↓
         HIGH confidence? → Return immediately
                ↓ NO
         get_raw_server_data
                ↓
         LLM Enhancement
                ↓
         Enhanced Results
```

---

## Implementation Roadmap

### Phase 1: Add Raw Data Tool (MCP Server)

**File:** `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery/raw_data_collector.py`

```python
"""
Raw data collection for agent-side processing.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("mcp.workload_discovery.raw_data_collector")


class RawDataCollector:
    """Collects raw server data for agent processing."""
    
    def collect(self, ssh_exec, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Collect raw data from server.
        
        Args:
            ssh_exec: SSH execution function
            options: Collection options (what to collect)
            
        Returns:
            Dictionary with raw data:
            {
                "processes": "...",  # Raw ps output
                "ports": "...",      # Raw netstat output
                "configs": {...},    # Config file contents
                "packages": "...",   # Package list
                "services": "..."    # Service list
            }
        """
        options = options or {}
        result = {}
        
        # Collect process list
        if options.get("collect_processes", True):
            result["processes"] = self._collect_processes(ssh_exec)
        
        # Collect port list
        if options.get("collect_ports", True):
            result["ports"] = self._collect_ports(ssh_exec)
        
        # Collect config files
        if options.get("collect_configs", False):
            config_paths = options.get("config_paths", [])
            result["configs"] = self._collect_configs(ssh_exec, config_paths)
        
        # Collect package list
        if options.get("collect_packages", False):
            result["packages"] = self._collect_packages(ssh_exec)
        
        # Collect service list
        if options.get("collect_services", False):
            result["services"] = self._collect_services(ssh_exec)
        
        return result
    
    def _collect_processes(self, ssh_exec) -> str:
        """Collect process list."""
        exit_code, stdout, stderr = ssh_exec("ps aux")
        if exit_code == 0:
            return stdout
        return ""
    
    def _collect_ports(self, ssh_exec) -> str:
        """Collect listening ports."""
        # Try netstat first
        exit_code, stdout, stderr = ssh_exec("netstat -tulpn 2>/dev/null")
        if exit_code == 0:
            return stdout
        
        # Fallback to ss
        exit_code, stdout, stderr = ssh_exec("ss -tulpn 2>/dev/null")
        if exit_code == 0:
            return stdout
        
        return ""
    
    def _collect_configs(self, ssh_exec, paths: List[str]) -> Dict[str, str]:
        """Collect configuration files."""
        configs = {}
        for path in paths:
            exit_code, stdout, stderr = ssh_exec(f"cat {path} 2>/dev/null")
            if exit_code == 0:
                configs[path] = stdout
        return configs
    
    def _collect_packages(self, ssh_exec) -> str:
        """Collect installed packages."""
        # Try rpm
        exit_code, stdout, stderr = ssh_exec("rpm -qa 2>/dev/null")
        if exit_code == 0:
            return stdout
        
        # Try dpkg
        exit_code, stdout, stderr = ssh_exec("dpkg -l 2>/dev/null")
        if exit_code == 0:
            return stdout
        
        return ""
    
    def _collect_services(self, ssh_exec) -> str:
        """Collect running services."""
        # Try systemctl
        exit_code, stdout, stderr = ssh_exec("systemctl list-units --type=service 2>/dev/null")
        if exit_code == 0:
            return stdout
        
        # Try service
        exit_code, stdout, stderr = ssh_exec("service --status-all 2>/dev/null")
        if exit_code == 0:
            return stdout
        
        return ""
```

**File:** `python/cyberres-mcp/src/cyberres_mcp/plugins/workload_discovery.py` (update)

```python
# Add new tool registration

@server.call_tool()
async def get_raw_server_data(arguments: dict) -> list[CallToolResult]:
    """
    Get raw server data for agent-side processing.
    
    Use this when you need to:
    - Analyze unknown applications with LLM
    - Extract version information from complex output
    - Correlate multiple data sources
    - Perform custom detection logic
    
    Args:
        host: Target server hostname/IP
        ssh_port: SSH port (default: 22)
        ssh_user: SSH username
        ssh_password: SSH password (optional)
        ssh_key_path: SSH key path (optional)
        collect_processes: Collect process list (default: true)
        collect_ports: Collect port list (default: true)
        collect_configs: Collect config files (default: false)
        config_paths: List of config file paths to collect
        collect_packages: Collect package list (default: false)
        collect_services: Collect service list (default: false)
    
    Returns:
        Raw server data as JSON
    """
    try:
        # Create discovery request
        request = DiscoveryRequest(**arguments)
        
        # Create SSH executor
        from .ssh_utils import SSHExecutor
        executor = SSHExecutor(
            host=request.host,
            port=request.ssh_port,
            username=request.ssh_user or "",
            password=request.ssh_password,
            key_path=request.ssh_key_path
        )
        
        # Create wrapper for ssh_exec
        def ssh_exec(cmd: str):
            return executor.execute(cmd)
        
        # Collect raw data
        from .workload_discovery.raw_data_collector import RawDataCollector
        collector = RawDataCollector()
        
        options = {
            "collect_processes": arguments.get("collect_processes", True),
            "collect_ports": arguments.get("collect_ports", True),
            "collect_configs": arguments.get("collect_configs", False),
            "config_paths": arguments.get("config_paths", []),
            "collect_packages": arguments.get("collect_packages", False),
            "collect_services": arguments.get("collect_services", False)
        }
        
        raw_data = collector.collect(ssh_exec, options)
        
        return [
            CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(raw_data, indent=2)
                    )
                ]
            )
        ]
        
    except Exception as e:
        logger.error(f"Raw data collection failed: {str(e)}")
        return [
            CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "error": str(e),
                            "status": "failed"
                        }, indent=2)
                    )
                ],
                isError=True
            )
        ]
```

### Phase 2: Agent Enhancement Logic (MCP Client)

**File:** `python/src/workload_discovery_agent.py` (NEW)

```python
"""
Workload discovery agent with LLM enhancement.
Implements hybrid detection strategy.
"""

import asyncio
import json
from typing import List, Dict, Any
from mcp_client import MCPClient
from llm import LLMClient


class WorkloadDiscoveryAgent:
    """Agent for intelligent workload discovery."""
    
    def __init__(self, mcp_client: MCPClient, llm_client: LLMClient):
        self.mcp = mcp_client
        self.llm = llm_client
    
    async def discover_workloads(
        self,
        host: str,
        ssh_user: str,
        ssh_password: str = None,
        ssh_key_path: str = None,
        enhance_with_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Discover workloads using hybrid approach.
        
        Args:
            host: Target server
            ssh_user: SSH username
            ssh_password: SSH password (optional)
            ssh_key_path: SSH key path (optional)
            enhance_with_llm: Use LLM for enhancement (default: True)
        
        Returns:
            Complete discovery results with enhanced data
        """
        # Phase 1: Fast signature-based detection
        print(f"🔍 Phase 1: Fast signature detection on {host}...")
        apps = await self._signature_detection(
            host, ssh_user, ssh_password, ssh_key_path
        )
        
        print(f"   Found {len(apps)} applications")
        
        # Phase 2: Identify what needs enhancement
        if enhance_with_llm:
            needs_enhancement = [
                app for app in apps
                if app.get("confidence") in ["low", "uncertain"]
            ]
            
            if needs_enhancement:
                print(f"🤖 Phase 2: LLM enhancement for {len(needs_enhancement)} apps...")
                enhanced = await self._llm_enhancement(
                    host, ssh_user, ssh_password, ssh_key_path,
                    needs_enhancement
                )
                
                # Update apps with enhanced data
                for app in apps:
                    if app["name"] in enhanced:
                        app.update(enhanced[app["name"]])
        
        # Phase 3: Return complete results
        return {
            "host": host,
            "applications": apps,
            "total_count": len(apps),
            "high_confidence": len([a for a in apps if a.get("confidence") == "high"]),
            "enhanced_count": len(needs_enhancement) if enhance_with_llm else 0
        }
    
    async def _signature_detection(
        self,
        host: str,
        ssh_user: str,
        ssh_password: str = None,
        ssh_key_path: str = None
    ) -> List[Dict[str, Any]]:
        """Phase 1: Fast signature-based detection."""
        
        result = await self.mcp.call_tool(
            "discover_applications",
            {
                "host": host,
                "ssh_user": ssh_user,
                "ssh_password": ssh_password,
                "ssh_key_path": ssh_key_path
            }
        )
        
        # Parse result
        if result and result[0].content:
            data = json.loads(result[0].content[0].text)
            return data.get("applications", [])
        
        return []
    
    async def _llm_enhancement(
        self,
        host: str,
        ssh_user: str,
        ssh_password: str,
        ssh_key_path: str,
        apps_to_enhance: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Phase 2: LLM enhancement for ambiguous detections."""
        
        # Get raw server data
        raw_data = await self._get_raw_data(
            host, ssh_user, ssh_password, ssh_key_path
        )
        
        # Enhance each app with LLM
        enhanced = {}
        for app in apps_to_enhance:
            print(f"   Analyzing: {app['name']}...")
            
            enhanced_data = await self._llm_analyze_app(app, raw_data)
            enhanced[app["name"]] = enhanced_data
        
        return enhanced
    
    async def _get_raw_data(
        self,
        host: str,
        ssh_user: str,
        ssh_password: str,
        ssh_key_path: str
    ) -> Dict[str, Any]:
        """Get raw server data for LLM analysis."""
        
        result = await self.mcp.call_tool(
            "get_raw_server_data",
            {
                "host": host,
                "ssh_user": ssh_user,
                "ssh_password": ssh_password,
                "ssh_key_path": ssh_key_path,
                "collect_processes": True,
                "collect_ports": True,
                "collect_configs": False,
                "collect_packages": False,
                "collect_services": False
            }
        )
        
        if result and result[0].content:
            return json.loads(result[0].content[0].text)
        
        return {}
    
    async def _llm_analyze_app(
        self,
        app: Dict[str, Any],
        raw_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to analyze and enhance application detection."""
        
        prompt = f"""
Analyze this application detection and provide enhanced information:

Application: {app.get('name', 'Unknown')}
Current Confidence: {app.get('confidence', 'uncertain')}
Detection Methods: {app.get('detection_methods', [])}

Process Information:
{app.get('process_info', 'N/A')}

Port Information:
{app.get('port_info', 'N/A')}

Raw Server Data:
Processes: {raw_data.get('processes', 'N/A')[:500]}...
Ports: {raw_data.get('ports', 'N/A')[:500]}...

Please provide:
1. Confirmed application name and type
2. Version if detectable
3. Updated confidence level (high/medium/low/uncertain)
4. Brief reasoning for your conclusion

Return as JSON:
{{
  "name": "Application Name",
  "version": "X.Y.Z",
  "confidence": "high|medium|low|uncertain",
  "reasoning": "Brief explanation",
  "application_type": "database|web_server|app_server|etc"
}}
"""
        
        response = await self.llm.complete(prompt)
        
        try:
            # Parse LLM response
            enhanced = json.loads(response)
            return enhanced
        except:
            # Fallback if parsing fails
            return {
                "confidence": app.get("confidence"),
                "reasoning": "LLM analysis failed"
            }


# Example usage
async def main():
    """Example: Discover workloads with hybrid approach."""
    
    # Initialize clients
    mcp_client = MCPClient()
    llm_client = LLMClient()
    
    # Create agent
    agent = WorkloadDiscoveryAgent(mcp_client, llm_client)
    
    # Discover workloads
    results = await agent.discover_workloads(
        host="192.168.1.100",
        ssh_user="admin",
        ssh_password="secret",
        enhance_with_llm=True
    )
    
    # Display results
    print("\n" + "="*60)
    print("WORKLOAD DISCOVERY RESULTS")
    print("="*60)
    print(f"Host: {results['host']}")
    print(f"Total Applications: {results['total_count']}")
    print(f"High Confidence: {results['high_confidence']}")
    print(f"LLM Enhanced: {results['enhanced_count']}")
    print("\nApplications:")
    for app in results['applications']:
        print(f"  - {app['name']} ({app.get('version', 'unknown')})")
        print(f"    Confidence: {app['confidence']}")
        if app.get('reasoning'):
            print(f"    Reasoning: {app['reasoning']}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Phase 3: Testing

**File:** `python/cyberres-mcp/test_hybrid_approach.py` (NEW)

```python
"""
Test suite for hybrid detection approach.
"""

import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch


def test_raw_data_collector():
    """Test raw data collection."""
    from cyberres_mcp.plugins.workload_discovery.raw_data_collector import RawDataCollector
    
    # Mock SSH executor
    def mock_ssh_exec(cmd):
        if "ps aux" in cmd:
            return (0, "PID USER COMMAND\n1234 oracle ora_pmon_ORCL", "")
        elif "netstat" in cmd:
            return (0, "tcp 0 0 0.0.0.0:1521 LISTEN", "")
        return (1, "", "error")
    
    collector = RawDataCollector()
    result = collector.collect(mock_ssh_exec)
    
    assert "processes" in result
    assert "ports" in result
    assert "ora_pmon" in result["processes"]
    assert "1521" in result["ports"]
    
    print("✅ Raw data collector test passed")


async def test_hybrid_detection():
    """Test hybrid detection workflow."""
    
    # Mock MCP client
    mcp_mock = Mock()
    mcp_mock.call_tool = AsyncMock()
    
    # Mock signature detection response
    mcp_mock.call_tool.return_value = [
        Mock(content=[
            Mock(text=json.dumps({
                "applications": [
                    {
                        "name": "Oracle Database",
                        "confidence": "high",
                        "version": "19c"
                    },
                    {
                        "name": "Unknown Java App",
                        "confidence": "low",
                        "process_info": "java -jar custom.jar"
                    }
                ]
            }))
        ])
    ]
    
    # Mock LLM client
    llm_mock = Mock()
    llm_mock.complete = AsyncMock(return_value=json.dumps({
        "name": "Custom Business Application",
        "version": "2.1.0",
        "confidence": "medium",
        "reasoning": "Java application with custom JAR, likely internal tool"
    }))
    
    # Test agent
    from workload_discovery_agent import WorkloadDiscoveryAgent
    agent = WorkloadDiscoveryAgent(mcp_mock, llm_mock)
    
    results = await agent.discover_workloads(
        host="test-server",
        ssh_user="admin",
        ssh_password="secret"
    )
    
    assert results["total_count"] == 2
    assert results["high_confidence"] == 1
    assert results["enhanced_count"] == 1
    
    print("✅ Hybrid detection test passed")


if __name__ == "__main__":
    print("="*60)
    print("HYBRID APPROACH TEST SUITE")
    print("="*60)
    
    test_raw_data_collector()
    asyncio.run(test_hybrid_detection())
    
    print("\n🎉 All tests passed!")
```

---

## Implementation Timeline

### Week 1: MCP Server Enhancement
- [ ] Day 1-2: Implement `RawDataCollector` class
- [ ] Day 3: Add `get_raw_server_data` MCP tool
- [ ] Day 4: Write tests for raw data collection
- [ ] Day 5: Integration testing with MCP Inspector

### Week 2: Agent Enhancement Logic
- [ ] Day 1-2: Implement `WorkloadDiscoveryAgent` class
- [ ] Day 3: Add LLM enhancement logic
- [ ] Day 4: Write tests for agent workflow
- [ ] Day 5: End-to-end testing

### Week 3: Optimization & Documentation
- [ ] Day 1-2: Add caching for LLM responses
- [ ] Day 3: Performance optimization
- [ ] Day 4-5: Documentation and examples

---

## Success Criteria

### Functional Requirements ✅
- [ ] `get_raw_server_data` tool returns complete raw data
- [ ] Agent can call both tools in sequence
- [ ] LLM enhancement improves confidence scores
- [ ] Unknown applications get identified

### Performance Requirements ✅
- [ ] Known apps detected in <5 seconds
- [ ] LLM enhancement completes in <30 seconds
- [ ] Total time for 10 apps: <2 minutes

### Cost Requirements ✅
- [ ] 95% of apps use signatures (free)
- [ ] 5% of apps use LLM ($0.05 each)
- [ ] Average cost per server: <$0.10

### Quality Requirements ✅
- [ ] All tests passing (100%)
- [ ] Code coverage >80%
- [ ] Documentation complete
- [ ] Examples working

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Begin Week 1** implementation
3. **Test incrementally** after each component
4. **Document as we go** for future reference
5. **Prepare for Sprint 4** (container detection)

---

## Conclusion

The hybrid approach gives us:
- ✅ **Speed**: Fast signature detection for 95% of cases
- ✅ **Intelligence**: LLM enhancement for the remaining 5%
- ✅ **Cost**: Optimal balance ($7.50 vs $50 for 1000 servers)
- ✅ **Flexibility**: Agent can customize as needed
- ✅ **Scalability**: Works for 1 server or 10,000 servers

This is the production-ready architecture for enterprise workload discovery.