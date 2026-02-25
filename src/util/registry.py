import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints
from mcp.types import Tool
from pydantic import BaseModel, TypeAdapter

class ToolRegistry:
    def __init__(self):
        self._tools: List[Tool] = []
        self._handlers: Dict[str, Callable] = {}

    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """Decorator to register a function as an MCP tool."""
        def decorator(func: Callable):
            nonlocal name, description
            tool_name = name or func.__name__
            tool_doc = description or inspect.getdoc(func) or ""
            
            # Generate Input Schema from function signature
            sig = inspect.signature(func)
            type_hints = get_type_hints(func)
            
            schema_properties = {}
            schema_required = []
            schema_defs = None

            # If the function takes a single Pydantic model as argument (common pattern in this codebase)
            params = list(sig.parameters.values())
            
            if len(params) == 1 and issubclass(type_hints.get(params[0].name, object), BaseModel):
                # Pydantic Model case
                model_class = type_hints[params[0].name]
                json_schema = model_class.model_json_schema()
                schema_properties = json_schema.get("properties", {})
                schema_required = json_schema.get("required", [])
                # Preserve $defs for nested model references
                if "$defs" in json_schema:
                    schema_defs = json_schema["$defs"]
            else:
                # Simple arguments case
                for param in params:
                    if param.name == 'self': continue # Should not happen in standalone functions but good safety
                    
                    param_type = type_hints.get(param.name, Any)
                    
                    # Basic type mapping
                    if param_type == str:
                        prop_def = {"type": "string"}
                    elif param_type == int:
                        prop_def = {"type": "integer"}
                    elif param_type == float:
                         prop_def = {"type": "number"}
                    elif param_type == bool:
                        prop_def = {"type": "boolean"}
                    else:
                        # Fallback or complex type (could use TypeAdapter(param_type).json_schema())
                        try:
                            prop_def = TypeAdapter(param_type).json_schema()
                        except:
                            prop_def = {"type": "string", "description": "Complex type, verified at runtime"} 

                    # Add description if available (parsing docstring would be better but this is MVP)
                    
                    schema_properties[param.name] = prop_def
                    if param.default == inspect.Parameter.empty:
                        schema_required.append(param.name)

            input_schema = {
                "type": "object",
                "properties": schema_properties,
                "required": schema_required
            }
            if schema_defs:
                input_schema["$defs"] = schema_defs

            tool_def = Tool(
                name=tool_name,
                description=tool_doc,
                inputSchema=input_schema
            )
            
            self._tools.append(tool_def)
            self._handlers[tool_name] = func
            return func
        return decorator

    def get_tools(self) -> List[Tool]:
        return self._tools

    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        handler = self._handlers.get(name)
        if not handler:
            raise ValueError(f"Tool not found: {name}")
            
        if arguments is None:
            arguments = {}

        # Inspect handler to see if it expects a Pydantic model
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())
        type_hints = get_type_hints(handler)
        
        # Pydantic Unpacking Logic
        if len(params) == 1 and issubclass(type_hints.get(params[0].name, object), BaseModel):
            model_class = type_hints[params[0].name]
            try:
                model_inst = model_class(**arguments)
                if inspect.iscoroutinefunction(handler):
                    return await handler(model_inst)
                else:
                    return handler(model_inst)
            except Exception as e:
                # Fallback: maybe arguments *is* the model fields if flattened?
                # But the code above expects "arguments" to be the dict matching model fields
                raise ValueError(f"Argument validation failed for {name}: {e}")

        # Standard Argument Unpacking
        if inspect.iscoroutinefunction(handler):
            return await handler(**arguments)
        else:
            return handler(**arguments)

# Global Registry Instance
registry = ToolRegistry()
