import inspect
from typing import Any, Callable, Dict, List, Literal, Optional
from pydantic import create_model

from .types import Tool

_global_tools: Dict[str, Tool] = {}

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = _global_tools.copy()

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def execute(self, name: str, args: Dict[str, Any]) -> str:
        if name not in self.tools:
            return f"Error: tool {name} not found"
        try:
            res = self.tools[name].executor(**args)
            if inspect.iscoroutine(res):
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    # if we are in an event loop, we can't use asyncio.run
                    # wait, if we are in a running loop, this is tricky. 
                    # But core/loop.py is fully synchronous, so there should be no running loop here.
                    res = asyncio.run(res)
                except RuntimeError:
                    res = asyncio.run(res)
            return str(res)
        except Exception as e:
            return f"Error executing tool {name}: {e}"

    def get_tool_schemas(self) -> List[dict]:
        schemas = []
        for name, tool in self.tools.items():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                }
            }
            if tool.schema is not None and (tool.schema.get("properties") or tool.schema.get("required")):
                schema["function"]["parameters"] = tool.schema
            else:
                # If there are no properties, we can provide an empty object or omit it.
                # In previous schema for get_time, it was omitted.
                pass
            schemas.append(schema)
        return schemas

def generate_schema(func: Callable) -> Optional[Dict[str, Any]]:
    sig = inspect.signature(func)
    fields = {}
    for param_name, param in sig.parameters.items():
        annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
        default = param.default if param.default != inspect.Parameter.empty else ...
        fields[param_name] = (annotation, default)
    
    if not fields:
        return None
        
    model = create_model(f"{func.__name__}_model", **fields)
    schema = model.model_json_schema()
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return schema

def tool(
    name: str, 
    description: str, 
    risk_level: Literal["safe", "warn", "danger"] = "safe", 
    category: str = "general",
    schema: Optional[Dict[str, Any]] = None
):
    def decorator(func: Callable[..., Any]):
        tool_schema = schema if schema is not None else generate_schema(func)
        t = Tool(
            name=name,
            description=description,
            schema=tool_schema,
            executor=func,
            risk_level=risk_level,
            category=category
        )
        _global_tools[t.name] = t
        return func
    return decorator
