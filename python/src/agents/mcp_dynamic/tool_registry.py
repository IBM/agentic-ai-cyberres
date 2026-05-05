"""
Tool Registry

Stores and manages tool schemas, validates parameters, and provides
tool metadata for LLM context.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .models import ToolSchema, ToolMetadata, ParameterInfo

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of parameter validation."""
    is_valid: bool
    error_message: Optional[str] = None
    missing_required: List[str] = None
    invalid_params: List[str] = None
    
    def __post_init__(self):
        if self.missing_required is None:
            self.missing_required = []
        if self.invalid_params is None:
            self.invalid_params = []


class ToolRegistry:
    """
    Registry for managing tool schemas and metadata.
    
    Features:
    - Store and retrieve tool schemas
    - Validate parameters against schemas
    - Generate LLM-friendly tool descriptions
    - Track tool versions and updates
    - Provide tool categorization
    
    Example:
        >>> registry = ToolRegistry()
        >>> registry.register_tool(schema)
        >>> 
        >>> # Validate parameters
        >>> result = registry.validate_parameters("discover_workload", params)
        >>> if not result.is_valid:
        ...     print(f"Validation failed: {result.error_message}")
        >>> 
        >>> # Get LLM descriptions
        >>> tools = registry.get_llm_tool_descriptions()
    """
    
    def __init__(self):
        """Initialize tool registry."""
        # Tool schemas: tool_name -> ToolSchema
        self._schemas: Dict[str, ToolSchema] = {}
        
        # Tool metadata: tool_name -> ToolMetadata
        self._metadata: Dict[str, ToolMetadata] = {}
        
        # Tool categories: category -> List[tool_name]
        self._categories: Dict[str, List[str]] = {}
        
        logger.info("Tool registry initialized")
    
    def register_tool(self, schema: ToolSchema) -> None:
        """
        Register a tool with its schema.
        
        Args:
            schema: Tool schema to register
        """
        tool_name = schema.name
        
        # Check if tool already exists
        if tool_name in self._schemas:
            logger.info(f"Updating existing tool: {tool_name}")
        else:
            logger.info(f"Registering new tool: {tool_name}")
        
        # Store schema
        self._schemas[tool_name] = schema
        
        # Generate and store metadata
        metadata = ToolMetadata.from_schema(schema)
        self._metadata[tool_name] = metadata
        
        # Update category index
        if schema.category:
            if schema.category not in self._categories:
                self._categories[schema.category] = []
            if tool_name not in self._categories[schema.category]:
                self._categories[schema.category].append(tool_name)
        
        logger.debug(f"Tool {tool_name} registered successfully")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
            
        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name not in self._schemas:
            logger.warning(f"Tool {tool_name} not found in registry")
            return False
        
        # Get schema for category cleanup
        schema = self._schemas[tool_name]
        
        # Remove from schemas and metadata
        del self._schemas[tool_name]
        del self._metadata[tool_name]
        
        # Remove from category index
        if schema.category and schema.category in self._categories:
            if tool_name in self._categories[schema.category]:
                self._categories[schema.category].remove(tool_name)
                # Clean up empty categories
                if not self._categories[schema.category]:
                    del self._categories[schema.category]
        
        logger.info(f"Tool {tool_name} unregistered")
        return True
    
    def get_tool(self, tool_name: str) -> Optional[ToolSchema]:
        """
        Get tool schema by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            ToolSchema or None if not found
        """
        return self._schemas.get(tool_name)
    
    def get_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """
        Get tool metadata by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            ToolMetadata or None if not found
        """
        return self._metadata.get(tool_name)
    
    def list_tools(self) -> List[ToolMetadata]:
        """
        List all registered tools.
        
        Returns:
            List of tool metadata
        """
        return list(self._metadata.values())
    
    def list_tool_names(self) -> List[str]:
        """
        List all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._schemas.keys())
    
    def get_tools_by_category(self, category: str) -> List[ToolMetadata]:
        """
        Get tools in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of tool metadata in category
        """
        tool_names = self._categories.get(category, [])
        return [self._metadata[name] for name in tool_names if name in self._metadata]
    
    def get_categories(self) -> List[str]:
        """
        Get list of all categories.
        
        Returns:
            List of category names
        """
        return list(self._categories.keys())
    
    def validate_parameters(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate parameters against tool schema.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters to validate
            
        Returns:
            ValidationResult with validation status and details
        """
        # Check if tool exists
        schema = self._schemas.get(tool_name)
        if not schema:
            return ValidationResult(
                is_valid=False,
                error_message=f"Tool {tool_name} not found in registry"
            )
        
        # Validate using schema
        is_valid, error_msg = schema.validate_parameters(parameters)
        
        if not is_valid:
            # Extract more details about validation failure
            required_params = schema.get_required_params()
            provided_params = set(parameters.keys())
            schema_params = set(schema.input_schema.get("properties", {}).keys())
            
            missing_required = [p for p in required_params if p not in provided_params]
            invalid_params = [p for p in provided_params if p not in schema_params]
            
            return ValidationResult(
                is_valid=False,
                error_message=error_msg,
                missing_required=missing_required,
                invalid_params=invalid_params
            )
        
        return ValidationResult(is_valid=True)
    
    def get_llm_tool_descriptions(self) -> List[Dict[str, Any]]:
        """
        Get tool descriptions in format suitable for LLM.
        
        Returns:
            List of tool descriptions for LLM context
        """
        descriptions = []
        
        for metadata in self._metadata.values():
            descriptions.append(metadata.to_llm_format())
        
        logger.debug(f"Generated LLM descriptions for {len(descriptions)} tools")
        return descriptions
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive information about a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary with tool information or None if not found
        """
        schema = self._schemas.get(tool_name)
        metadata = self._metadata.get(tool_name)
        
        if not schema or not metadata:
            return None
        
        return {
            "name": schema.name,
            "description": schema.description,
            "category": schema.category,
            "version": schema.version,
            "required_parameters": schema.get_required_params(),
            "optional_parameters": schema.get_optional_params(),
            "parameter_details": [
                p.to_dict() for p in metadata.parameters
            ],
            "input_schema": schema.input_schema,
        }
    
    def search_tools(self, query: str) -> List[ToolMetadata]:
        """
        Search tools by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching tool metadata
        """
        query_lower = query.lower()
        matches = []
        
        for metadata in self._metadata.values():
            if (query_lower in metadata.name.lower() or
                query_lower in metadata.description.lower()):
                matches.append(metadata)
        
        logger.debug(f"Found {len(matches)} tools matching '{query}'")
        return matches
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_tools = len(self._schemas)
        total_categories = len(self._categories)
        
        # Count parameters
        total_params = sum(
            len(schema.input_schema.get("properties", {}))
            for schema in self._schemas.values()
        )
        
        # Count required vs optional
        total_required = sum(
            len(schema.get_required_params())
            for schema in self._schemas.values()
        )
        total_optional = total_params - total_required
        
        return {
            "total_tools": total_tools,
            "total_categories": total_categories,
            "total_parameters": total_params,
            "required_parameters": total_required,
            "optional_parameters": total_optional,
            "tools_by_category": {
                cat: len(tools) for cat, tools in self._categories.items()
            }
        }
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._schemas.clear()
        self._metadata.clear()
        self._categories.clear()
        logger.info("Tool registry cleared")
    
    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._schemas)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._schemas
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ToolRegistry(tools={len(self._schemas)}, categories={len(self._categories)})"


# Made with Bob