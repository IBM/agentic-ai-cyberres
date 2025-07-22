from pydantic import BaseModel
from typing import Dict, Any, List

class ValidationRequest(BaseModel):
    protocol_version: str
    event_type: str
    resource_type: str
    resource_id: str
    recovery_metadata: Dict[str, Any]

class ValidationResult(BaseModel):
    protocol_version: str
    resource_id: str
    resource_type: str
    validation_status: str
    checks: List[Dict[str, str]]
    details: Dict[str, Any]

class MCPMessage(BaseModel):
    protocol_version: str
    message_type: str
    source_agent: str
    target_agent: str
    context: Dict[str, Any]
