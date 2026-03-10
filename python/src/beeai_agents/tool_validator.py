"""
Tool argument validation using Pydantic models.

This module provides validation for MCP tool arguments against their input schemas.
BeeAI's MCPTool exposes input_schema as a Pydantic BaseModel, which we use for
automatic validation with clear error messages.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import ValidationError as PydanticValidationError
from beeai_framework.tools.mcp import MCPTool

logger = logging.getLogger(__name__)


class ValidationError:
    """Represents a single validation error."""
    
    def __init__(
        self,
        parameter: str,
        error: str,
        expected: Optional[str] = None,
        actual: Optional[Any] = None
    ):
        self.parameter = parameter
        self.error = error
        self.expected = expected
        self.actual = actual
    
    def __str__(self) -> str:
        """Format error as human-readable string."""
        msg = f"{self.parameter}: {self.error}"
        if self.expected:
            msg += f" (expected: {self.expected}"
            if self.actual is not None:
                msg += f", got: {self.actual}"
            msg += ")"
        return msg
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "parameter": self.parameter,
            "error": self.error,
            "expected": self.expected,
            "actual": self.actual
        }


class ValidationResult:
    """Result of tool argument validation."""
    
    def __init__(
        self,
        is_valid: bool,
        errors: Optional[List[ValidationError]] = None,
        warnings: Optional[List[str]] = None
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def __bool__(self) -> bool:
        """Allow using result in boolean context."""
        return self.is_valid
    
    def error_summary(self) -> str:
        """Get formatted error summary."""
        if not self.errors:
            return "No errors"
        return "; ".join(str(e) for e in self.errors)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings
        }


class ToolValidator:
    """Validates MCP tool arguments using Pydantic models.
    
    This validator uses BeeAI's built-in Pydantic models (exposed via
    tool.input_schema) to validate tool arguments before execution.
    
    Benefits:
    - Automatic type checking and coercion
    - Clear, structured error messages
    - Handles nested objects and complex types
    - No manual JSON Schema parsing needed
    
    Example:
        >>> validator = ToolValidator(mcp_tools)
        >>> result = validator.validate_tool_args("check_vm", {"host": "192.168.1.1"})
        >>> if not result.is_valid:
        ...     print(result.error_summary())
    """
    
    def __init__(self, mcp_tools: List[MCPTool]):
        """Initialize validator with available MCP tools.
        
        Args:
            mcp_tools: List of MCPTool instances from MCP server
        """
        self.mcp_tools = mcp_tools
        self._tool_map = {tool.name: tool for tool in mcp_tools}
        
        logger.info(f"Tool validator initialized with {len(mcp_tools)} tools")
    
    def validate_tool_args(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> ValidationResult:
        """Validate arguments against tool's Pydantic model.
        
        Args:
            tool_name: Name of the tool to validate
            args: Arguments to validate
        
        Returns:
            ValidationResult with validation status and any errors
        
        Example:
            >>> result = validator.validate_tool_args(
            ...     "vm_linux_uptime_load_mem",
            ...     {"host": "192.168.1.1", "username": "admin"}
            ... )
            >>> assert result.is_valid
        """
        # Check if tool exists
        tool = self._tool_map.get(tool_name)
        if not tool:
            logger.warning(f"Tool not found: {tool_name}")
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    parameter="tool",
                    error=f"Tool not found: {tool_name}",
                    expected="valid tool name",
                    actual=tool_name
                )]
            )
        
        try:
            # Get Pydantic model from tool
            InputModel = tool.input_schema
            
            # Validate arguments by instantiating model
            # This will raise ValidationError if arguments are invalid
            validated = InputModel(**args)
            
            logger.debug(
                f"Tool arguments validated successfully",
                extra={
                    "tool": tool_name,
                    "tool_args": args,  # Renamed from 'args' to avoid LogRecord conflict
                    "validated": validated.model_dump()
                }
            )
            
            return ValidationResult(is_valid=True)
        
        except PydanticValidationError as e:
            # Convert Pydantic errors to our ValidationError format
            errors = []
            for pydantic_error in e.errors():
                # Extract parameter path (e.g., ['host'] or ['config', 'timeout'])
                param_path = ".".join(str(x) for x in pydantic_error['loc'])
                
                # Get error details
                error_msg = pydantic_error['msg']
                error_type = pydantic_error.get('type', '')
                
                # Try to get actual value
                actual_value = None
                if len(pydantic_error['loc']) == 1:
                    param_name = pydantic_error['loc'][0]
                    actual_value = args.get(param_name)
                
                errors.append(ValidationError(
                    parameter=param_path,
                    error=error_msg,
                    expected=error_type,
                    actual=actual_value
                ))
            
            logger.warning(
                f"Tool argument validation failed",
                extra={
                    "tool": tool_name,
                    "tool_args": args,  # Renamed from 'args' to avoid LogRecord conflict
                    "errors": [e.to_dict() for e in errors]
                }
            )
            
            return ValidationResult(
                is_valid=False,
                errors=errors
            )
        
        except Exception as e:
            # Catch any unexpected errors
            logger.error(
                f"Unexpected error during validation",
                extra={
                    "tool": tool_name,
                    "tool_args": args,  # Renamed from 'args' to avoid LogRecord conflict
                    "error": str(e)
                },
                exc_info=True
            )
            
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    parameter="validation",
                    error=f"Unexpected validation error: {str(e)}"
                )]
            )
    
    def validate_tool_exists(self, tool_name: str) -> bool:
        """Check if a tool exists.
        
        Args:
            tool_name: Name of the tool to check
        
        Returns:
            True if tool exists, False otherwise
        """
        return tool_name in self._tool_map
    
    def get_tool_schema_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema information for a tool.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Dictionary with schema info, or None if tool not found
        """
        tool = self._tool_map.get(tool_name)
        if not tool:
            return None
        
        try:
            InputModel = tool.input_schema
            schema = InputModel.model_json_schema()
            
            return {
                "tool_name": tool_name,
                "description": tool.description,
                "schema": schema,
                "required_params": schema.get("required", []),
                "properties": schema.get("properties", {})
            }
        except Exception as e:
            logger.error(f"Failed to get schema info for {tool_name}: {e}")
            return None
    
    def list_available_tools(self) -> List[str]:
        """Get list of available tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tool_map.keys())


# Made with Bob