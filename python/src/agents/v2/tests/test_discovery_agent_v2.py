"""
Test Suite for Discovery Agent V2

This module provides comprehensive tests for the Discovery Agent V2 implementation,
validating the RequirementAgent pattern and artifact handoff.

Test Categories:
- Basic functionality tests
- Artifact storage tests
- Error handling tests
- Performance tests
- Integration tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path

# Import components to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agents.v2.discovery_agent_v2 import DiscoveryAgentV2, DiscoveryError
from agents.v2.artifact_store import ArtifactStore
from agents.v2.artifacts.discovery_artifact import DiscoveryArtifact
from models import (
    VMResourceInfo,
    OracleDBResourceInfo,
    PortInfo,
    ProcessInfo,
    ApplicationDetection
)


# Fixtures

@pytest.fixture
def artifact_store():
    """Provide clean artifact store for each test."""
    return ArtifactStore()


@pytest.fixture
def mock_mcp_tools():
    """Provide mock MCP tools for testing."""
    tools = []
    for tool_name in ["scan_ports", "scan_processes", "detect_applications"]:
        tool = Mock()
        tool.name = tool_name
        tools.append(tool)
    return tools


@pytest.fixture
def sample_vm_resource():
    """Sample VM resource for testing."""
    return VMResourceInfo(
        resource_id="vm-test-01",
        resource_type="vm",
        hostname="test-vm.example.com",
        ip_address="192.168.1.100",
        ssh_credentials={"username": "admin", "password": "test123"}
    )


@pytest.fixture
def sample_discovery_artifact():
    """Sample discovery artifact for testing."""
    return DiscoveryArtifact(
        resource_id="vm-test-01",
        resource_type="vm",
        open_ports=[
            PortInfo(port=80, protocol="tcp", service="http", state="open"),
            PortInfo(port=443, protocol="tcp", service="https", state="open")
        ],
        running_processes=[
            ProcessInfo(
                pid=1234,
                name="nginx",
                command="/usr/sbin/nginx -g daemon off;",
                user="www-data"
            )
        ],
        detected_applications=[
            ApplicationDetection(
                name="nginx",
                version="1.18.0",
                confidence=0.95,
                detection_method="port_analysis",
                evidence=["Port 80 open", "Port 443 open"]
            )
        ],
        discovery_method="full",
        confidence_score=0.92,
        discovery_reasoning="Performed comprehensive scan",
        findings_summary="Web server running nginx 1.18.0",
        scan_completeness=1.0,
        data_quality="high"
    )


# Basic Functionality Tests

@pytest.mark.asyncio
async def test_discovery_agent_v2_basic(
    artifact_store,
    mock_mcp_tools,
    sample_vm_resource,
    sample_discovery_artifact
):
    """Test basic discovery agent V2 functionality."""
    
    agent = DiscoveryAgentV2(
        llm_model="ollama:llama3.2",
        mcp_tools=mock_mcp_tools,
        artifact_store=artifact_store
    )
    
    with patch.object(agent._agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_result = Mock()
        mock_result.final_answer = sample_discovery_artifact
        mock_run.return_value = mock_result
        
        result = await agent.discover(sample_vm_resource)
        
        assert isinstance(result, DiscoveryArtifact)
        assert result.resource_id == "vm-test-01"
        assert result.confidence_score == 0.92


@pytest.mark.asyncio
async def test_artifact_storage(
    artifact_store,
    mock_mcp_tools,
    sample_vm_resource,
    sample_discovery_artifact
):
    """Test artifact storage."""
    
    agent = DiscoveryAgentV2(
        llm_model="ollama:llama3.2",
        mcp_tools=mock_mcp_tools,
        artifact_store=artifact_store
    )
    
    with patch.object(agent._agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_result = Mock()
        mock_result.final_answer = sample_discovery_artifact
        mock_run.return_value = mock_result
        
        await agent.discover(sample_vm_resource, save_artifact=True)
        
        artifact_key = f"discovery_{sample_vm_resource.resource_id}"
        assert artifact_store.exists(artifact_key)


@pytest.mark.asyncio
async def test_error_handling(
    artifact_store,
    mock_mcp_tools,
    sample_vm_resource
):
    """Test error handling."""
    
    agent = DiscoveryAgentV2(
        llm_model="ollama:llama3.2",
        mcp_tools=mock_mcp_tools,
        artifact_store=artifact_store
    )
    
    with patch.object(agent._agent, 'run', new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = Exception("LLM error")
        
        with pytest.raises(DiscoveryError):
            await agent.discover(sample_vm_resource)

# Made with Bob
