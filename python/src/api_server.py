"""
FastAPI server for agentic validation workflow.
Exposes the ValidationOrchestrator as REST API endpoints.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
import logging

from agents.orchestrator import ValidationOrchestrator
from models import ValidationRequest, VMResourceInfo, ResourceType
from agents.telemetry import initialize_telemetry, flush_telemetry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize telemetry
initialize_telemetry(
    service_name="validation-api",
    phoenix_endpoint="http://localhost:6006/v1/traces"
)

# Create FastAPI app
app = FastAPI(
    title="Agentic Validation API",
    description="AI-powered infrastructure validation using IBM watsonx",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator: Optional[ValidationOrchestrator] = None

# In-memory job tracking
validation_jobs: Dict[str, Dict[str, Any]] = {}


# ── Request/Response Models ──────────────────────────────────────────────────

class ValidationJobRequest(BaseModel):
    """Request to start a validation job."""
    host: str = Field(..., description="Target host IP or hostname")
    resource_type: str = Field(default="vm", description="Resource type: vm, oracle_db, mongodb")
    ssh_user: Optional[str] = Field(None, description="SSH username")
    ssh_password: Optional[str] = Field(None, description="SSH password")
    credential_id: Optional[str] = Field(None, description="Credential ID from secrets.json")
    enable_discovery: bool = Field(default=True, description="Enable workload discovery")
    enable_evaluation: bool = Field(default=True, description="Enable AI evaluation")


class ValidationJobResponse(BaseModel):
    """Response with job ID for async tracking."""
    job_id: str
    status: str
    message: str
    created_at: str


class ValidationJobStatus(BaseModel):
    """Status of a validation job."""
    job_id: str
    status: str
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


# ── Startup/Shutdown ──────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup."""
    global orchestrator
    
    logger.info("🚀 Starting Agentic Validation API...")
    
    # Get absolute path to MCP server
    import os
    from pathlib import Path
    
    # MCP server is in python/cyberres-mcp relative to project root
    current_dir = Path(__file__).parent  # python/src
    mcp_server_path = current_dir.parent / "cyberres-mcp"  # python/cyberres-mcp
    
    logger.info(f"MCP server path: {mcp_server_path}")
    
    orchestrator = ValidationOrchestrator(
        llm_model="ibm/granite-13b-chat-v2",
        mcp_server_path=str(mcp_server_path)
    )
    
    await orchestrator.initialize()
    logger.info("✅ Orchestrator initialized and ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global orchestrator
    
    logger.info("🛑 Shutting down Agentic Validation API...")
    
    if orchestrator:
        await orchestrator.cleanup()
    
    flush_telemetry()
    logger.info("✅ Shutdown complete")


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Agentic Validation API",
        "status": "healthy",
        "version": "1.0.0",
        "orchestrator_ready": orchestrator is not None
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return {
        "status": "healthy",
        "orchestrator": "ready",
        "mcp_tools": len(orchestrator.get_available_mcp_tools()) if orchestrator._initialized else 0,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/validate", response_model=ValidationJobResponse)
async def start_validation(
    request: ValidationJobRequest,
    background_tasks: BackgroundTasks
):
    """Start an asynchronous validation job."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    job_id = str(uuid.uuid4())
    
    validation_request = ValidationRequest(
        resource=VMResourceInfo(
            host=request.host,
            resource_type=ResourceType(request.resource_type),
            ssh_user=request.ssh_user,
            ssh_password=request.ssh_password,
            credential_id=request.credential_id
        ),
        enable_discovery=request.enable_discovery,
        enable_evaluation=request.enable_evaluation
    )
    
    validation_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "request": request.dict(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    background_tasks.add_task(run_validation_job, job_id, validation_request)
    
    logger.info(f"Started validation job {job_id} for {request.host}")
    
    return ValidationJobResponse(
        job_id=job_id,
        status="pending",
        message=f"Validation job started for {request.host}",
        created_at=validation_jobs[job_id]["created_at"]
    )


@app.get("/validate/{job_id}", response_model=ValidationJobStatus)
async def get_validation_status(job_id: str):
    """Get the status and results of a validation job."""
    if job_id not in validation_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job = validation_jobs[job_id]
    
    return ValidationJobStatus(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error"),
        created_at=job["created_at"],
        updated_at=job["updated_at"]
    )


@app.post("/validate/sync")
async def validate_sync(request: ValidationJobRequest):
    """Synchronous validation endpoint (waits for completion)."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        validation_request = ValidationRequest(
            resource=VMResourceInfo(
                host=request.host,
                resource_type=ResourceType(request.resource_type),
                ssh_user=request.ssh_user,
                ssh_password=request.ssh_password,
                credential_id=request.credential_id
            ),
            enable_discovery=request.enable_discovery,
            enable_evaluation=request.enable_evaluation
        )
        
        logger.info(f"Starting sync validation for {request.host}")
        result = await orchestrator.execute_workflow(validation_request)
        
        return {
            "status": "completed",
            "host": request.host,
            "discovery": result.discovery_result.dict() if result.discovery_result else None,
            "plan": result.plan.dict() if result.plan else None,
            "validation": result.validation_result.dict() if result.validation_result else None,
            "evaluation": result.evaluation_result.dict() if result.evaluation_result else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_available_tools():
    """List all available MCP tools."""
    if not orchestrator or not orchestrator._initialized:
        return {"tools": []}
    
    return {
        "count": len(orchestrator.get_available_mcp_tools()),
        "tools": orchestrator.get_available_mcp_tools()
    }


# ── Background Job Execution ──────────────────────────────────────────────────

async def run_validation_job(job_id: str, request: ValidationRequest):
    """Execute validation job in background."""
    try:
        validation_jobs[job_id]["status"] = "running"
        validation_jobs[job_id]["progress"] = "Starting validation..."
        validation_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Executing validation job {job_id}")
        result = await orchestrator.execute_workflow(request)
        
        validation_jobs[job_id]["status"] = "completed"
        validation_jobs[job_id]["result"] = {
            "discovery": result.discovery_result.dict() if result.discovery_result else None,
            "plan": result.plan.dict() if result.plan else None,
            "validation": result.validation_result.dict() if result.validation_result else None,
            "evaluation": result.evaluation_result.dict() if result.evaluation_result else None,
        }
        validation_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Validation job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Validation job {job_id} failed: {e}", exc_info=True)
        validation_jobs[job_id]["status"] = "failed"
        validation_jobs[job_id]["error"] = str(e)
        validation_jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()


# ── Run Server ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )

# Made with Bob
