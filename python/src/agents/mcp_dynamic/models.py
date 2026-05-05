"""
Data models for dynamic MCP integration.

Defines schemas and metadata structures for runtime tool discovery and invocation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import json
import jsonschema


class ParameterType(Enum):
    """Parameter data types."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"


@dataclass
class ParameterInfo:
    """Information about a tool parameter."""
    name: str
    type: ParameterType
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    properties: Optional[Dict[str, 'ParameterInfo']] = None
    items: Optional['ParameterInfo'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.enum is not None:
            result["enum"] = self.enum
        if self.properties is not None:
            result["properties"] = {
                k: v.to_dict() for k, v in self.properties.items()
            }
        if self.items is not None:
            result["items"] = self.items.to_dict()
        return result


@dataclass
class ToolSchema:
    """
    Schema definition for an MCP tool.
    
    Represents the complete specification of a tool including its name,
    description, and parameter schema (JSON Schema format).
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    annotations: Optional[Dict[str, Any]] = None
    version: Optional[str] = None
    category: Optional[str] = None
    
    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate parameters against the input schema.
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            jsonschema.validate(instance=params, schema=self.input_schema)
            return True, None
        except jsonschema.ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_required_params(self) -> List[str]:
        """Get list of required parameter names."""
        return self.input_schema.get("required", [])
    
    def get_optional_params(self) -> List[str]:
        """Get list of optional parameter names."""
        all_params = set(self.input_schema.get("properties", {}).keys())
        required = set(self.get_required_params())
        return list(all_params - required)
    
    def get_parameter_info(self, param_name: str) -> Optional[ParameterInfo]:
        """Get detailed information about a specific parameter."""
        properties = self.input_schema.get("properties", {})
        if param_name not in properties:
            return None
        
        param_schema = properties[param_name]
        required_params = self.get_required_params()
        
        return ParameterInfo(
            name=param_name,
            type=ParameterType(param_schema.get("type", "string")),
            description=param_schema.get("description", ""),
            required=param_name in required_params,
            default=param_schema.get("default"),
            enum=param_schema.get("enum"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
        if self.annotations:
            result["annotations"] = self.annotations
        if self.version:
            result["version"] = self.version
        if self.category:
            result["category"] = self.category
        return result
    
    @classmethod
    def from_mcp_tool(cls, mcp_tool: Any) -> 'ToolSchema':
        """
        Create ToolSchema from MCP tool object.
        
        Args:
            mcp_tool: MCP tool object (from BeeAI MCPTool)
            
        Returns:
            ToolSchema instance
        """
        return cls(
            name=mcp_tool.name,
            description=getattr(mcp_tool, 'description', ''),
            input_schema=getattr(mcp_tool, 'input_schema', {}),
            annotations=getattr(mcp_tool, 'annotations', None),
        )


@dataclass
class ToolMetadata:
    """
    Metadata about a tool for LLM context.
    
    Provides a simplified view of tool information suitable for
    passing to LLMs for tool selection and usage.
    """
    name: str
    description: str
    category: Optional[str] = None
    parameters: List[ParameterInfo] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_llm_format(self) -> Dict[str, Any]:
        """
        Convert to format suitable for LLM tool descriptions.
        
        Returns:
            Dictionary in format expected by LLM frameworks
        """
        result = {
            "name": self.name,
            "description": self.description,
        }
        
        if self.category:
            result["category"] = self.category
        
        if self.parameters:
            result["parameters"] = {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type.value,
                        "description": p.description,
                    }
                    for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required],
            }
        
        if self.examples:
            result["examples"] = self.examples
        
        if self.tags:
            result["tags"] = self.tags
        
        return result
    
    @classmethod
    def from_schema(cls, schema: ToolSchema) -> 'ToolMetadata':
        """
        Create ToolMetadata from ToolSchema.
        
        Args:
            schema: ToolSchema instance
            
        Returns:
            ToolMetadata instance
        """
        parameters = []
        properties = schema.input_schema.get("properties", {})
        required_params = schema.get_required_params()
        
        for param_name, param_schema in properties.items():
            parameters.append(ParameterInfo(
                name=param_name,
                type=ParameterType(param_schema.get("type", "string")),
                description=param_schema.get("description", ""),
                required=param_name in required_params,
                default=param_schema.get("default"),
                enum=param_schema.get("enum"),
            ))
        
        return cls(
            name=schema.name,
            description=schema.description,
            category=schema.category,
            parameters=parameters,
        )


@dataclass
class ToolResult:
    """
    Result of a tool invocation.
    
    Encapsulates the outcome of executing a tool, including success status,
    result data, errors, and execution metadata.
    """
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }
    
    def __str__(self) -> str:
        """String representation."""
        if self.success:
            return f"ToolResult(tool={self.tool_name}, success=True, time={self.execution_time_ms}ms)"
        else:
            return f"ToolResult(tool={self.tool_name}, success=False, error={self.error})"


@dataclass
class ToolInvocation:
    """
    Represents a tool invocation request.
    
    Used for batching multiple tool calls.
    """
    tool_name: str
    parameters: Dict[str, Any]
    invocation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
        }
        if self.invocation_id:
            result["invocation_id"] = self.invocation_id
        return result


@dataclass
class ToolChange:
    """
    Represents a change in tool availability or schema.
    
    Used for hot-reload notifications.
    """
    change_type: str  # "added", "removed", "modified"
    tool_name: str
    old_schema: Optional[ToolSchema] = None
    new_schema: Optional[ToolSchema] = None
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "change_type": self.change_type,
            "tool_name": self.tool_name,
        }
        if self.old_schema:
            result["old_schema"] = self.old_schema.to_dict()
        if self.new_schema:
            result["new_schema"] = self.new_schema.to_dict()
        if self.timestamp:
            result["timestamp"] = self.timestamp
        return result


# Made with Bob