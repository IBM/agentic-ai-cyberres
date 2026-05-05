"""
Agent Communication Protocol (ACP) for Inter-Container Communication

Implements HTTP-based communication between containerized agents with:
- Request/response patterns
- Trace context propagation
- Health checks
- Error handling and retries
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
import httpx

from agents.observability import get_observability, trace_span

logger = logging.getLogger(__name__)


class ACPMessageType(str, Enum):
    """ACP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    HEALTH_CHECK = "health_check"


class ACPMessage(BaseModel):
    """Base ACP message structure."""
    message_id: str = Field(..., description="Unique message identifier")
    message_type: ACPMessageType = Field(..., description="Message type")
    sender: str = Field(..., description="Sender agent identifier")
    recipient: str = Field(..., description="Recipient agent identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    trace_context: Dict[str, str] = Field(default_factory=dict, description="OpenTelemetry trace context")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")


class ACPRequest(BaseModel):
    """ACP request message."""
    operation: str = Field(..., description="Operation to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, description="Request timeout")


class ACPResponse(BaseModel):
    """ACP response message."""
    success: bool = Field(..., description="Operation success status")
    result: Optional[Dict[str, Any]] = Field(None, description="Operation result")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_seconds: float = Field(..., description="Execution time")


class ACPHealthStatus(BaseModel):
    """Agent health status."""
    agent_name: str
    status: str  # healthy, degraded, unhealthy
    uptime_seconds: float
    last_operation: Optional[str] = None
    operations_count: int = 0
    error_count: int = 0


class ACPServer:
    """
    ACP server for receiving agent requests.
    
    Runs as FastAPI application in each agent container.
    
    Example:
        >>> server = ACPServer(agent_name="discovery-agent")
        >>> server.register_operation("discover", discovery_handler)
        >>> await server.start(port=8001)
    """
    
    def __init__(self, agent_name: str, port: int = 8000):
        self.agent_name = agent_name
        self.port = port
        self.app = FastAPI(title=f"{agent_name} ACP Server")
        self.operations: Dict[str, Any] = {}
        self.start_time = datetime.now()
        self.stats = {
            "operations_count": 0,
            "error_count": 0,
            "last_operation": None
        }
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            # Determine health status
            error_rate = (
                self.stats["error_count"] / self.stats["operations_count"]
                if self.stats["operations_count"] > 0
                else 0
            )
            
            if error_rate > 0.5:
                status = "unhealthy"
            elif error_rate > 0.2:
                status = "degraded"
            else:
                status = "healthy"
            
            return ACPHealthStatus(
                agent_name=self.agent_name,
                status=status,
                uptime_seconds=uptime,
                last_operation=self.stats["last_operation"],
                operations_count=self.stats["operations_count"],
                error_count=self.stats["error_count"]
            )
        
        @self.app.post("/invoke")
        async def invoke_operation(request: Request):
            """Invoke agent operation."""
            try:
                # Parse ACP message
                body = await request.json()
                acp_request = ACPRequest(**body)
                
                # Get observability instance
                obs = get_observability()
                
                # Inject trace context if available
                if obs and "trace_context" in body:
                    obs.inject_trace_context(body["trace_context"])
                
                # Find operation handler
                if acp_request.operation not in self.operations:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Operation not found: {acp_request.operation}"
                    )
                
                handler = self.operations[acp_request.operation]
                
                # Execute operation with tracing
                with trace_span(
                    f"acp.{acp_request.operation}",
                    {"agent": self.agent_name, "operation": acp_request.operation}
                ):
                    import time
                    start_time = time.time()
                    
                    result = await handler(**acp_request.parameters)
                    
                    execution_time = time.time() - start_time
                
                # Update stats
                self.stats["operations_count"] += 1
                self.stats["last_operation"] = acp_request.operation
                
                # Return response
                return ACPResponse(
                    success=True,
                    result=result,
                    execution_time_seconds=execution_time
                )
                
            except Exception as e:
                logger.error(f"Operation failed: {e}", exc_info=True)
                self.stats["error_count"] += 1
                
                return ACPResponse(
                    success=False,
                    error=str(e),
                    execution_time_seconds=0
                )
    
    def register_operation(self, operation_name: str, handler):
        """
        Register an operation handler.
        
        Args:
            operation_name: Name of the operation
            handler: Async function to handle the operation
        """
        self.operations[operation_name] = handler
        logger.info(f"Registered operation: {operation_name}")
    
    async def start(self):
        """Start the ACP server."""
        import uvicorn
        
        logger.info(f"Starting ACP server: {self.agent_name} on port {self.port}")
        
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


class ACPClient:
    """
    ACP client for sending requests to other agents.
    
    Example:
        >>> client = ACPClient("http://discovery-agent:8001")
        >>> result = await client.invoke("discover", {"host": "192.168.1.100"})
    """
    
    def __init__(
        self,
        agent_url: str,
        timeout: int = 300,
        max_retries: int = 3
    ):
        self.agent_url = agent_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def invoke(
        self,
        operation: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Invoke operation on remote agent.
        
        Args:
            operation: Operation name
            parameters: Operation parameters
            timeout: Request timeout (overrides default)
        
        Returns:
            Operation result
        
        Raises:
            ACPError: If operation fails
        """
        request_timeout = timeout or self.timeout
        
        # Get trace context
        obs = get_observability()
        trace_context = obs.get_trace_context() if obs else {}
        
        # Build request
        acp_request = ACPRequest(
            operation=operation,
            parameters=parameters or {},
            timeout_seconds=request_timeout
        )
        
        # Add trace context
        request_body = acp_request.model_dump()
        request_body["trace_context"] = trace_context
        
        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                with trace_span(
                    f"acp.client.{operation}",
                    {"target_url": self.agent_url, "attempt": attempt + 1}
                ):
                    response = await self.client.post(
                        f"{self.agent_url}/invoke",
                        json=request_body,
                        timeout=request_timeout
                    )
                    response.raise_for_status()
                    
                    acp_response = ACPResponse(**response.json())
                    
                    if not acp_response.success:
                        raise ACPError(f"Operation failed: {acp_response.error}")
                    
                    return acp_response.result or {}
            
            except Exception as e:
                last_error = e
                logger.warning(
                    f"ACP request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise ACPError(f"ACP request failed after {self.max_retries} attempts: {last_error}")
    
    async def health_check(self) -> ACPHealthStatus:
        """Check agent health."""
        try:
            response = await self.client.get(f"{self.agent_url}/health")
            response.raise_for_status()
            return ACPHealthStatus(**response.json())
        except Exception as e:
            raise ACPError(f"Health check failed: {e}")
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()


class ACPError(Exception):
    """ACP communication error."""
    pass


# Convenience functions for creating ACP servers/clients

def create_acp_server(agent_name: str, port: int = 8000) -> ACPServer:
    """Create ACP server for an agent."""
    return ACPServer(agent_name=agent_name, port=port)


def create_acp_client(agent_url: str, timeout: int = 300) -> ACPClient:
    """Create ACP client for communicating with an agent."""
    return ACPClient(agent_url=agent_url, timeout=timeout)

# Made with Bob
