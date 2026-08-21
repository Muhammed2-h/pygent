import inspect
from collections.abc import Callable
from typing import Any, Literal

from pydantic import create_model

from .types import Tool

_global_tools: dict[str, Tool] = {}

_main_loop = None

def set_main_loop(loop):
    global _main_loop
    _main_loop = loop

import time

from core.logger import tools_logger


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = _global_tools.copy()

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def execute(self, name: str, args: dict[str, Any]) -> str:
        start_time = time.time()
        if name not in self.tools:
            duration = time.time() - start_time
            tools_logger.error(f"Tool {name} not found", extra={"tool": name, "status": "error", "duration": duration, "error": "Not found"})
            return f"Error: tool {name} not found"
        try:
            res = self.tools[name].executor(**args)
            if inspect.iscoroutine(res):
                import asyncio
                

                if _main_loop is not None and _main_loop.is_running():
                    current_loop = None
                    try:
                        current_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        pass
                        
                    if current_loop is not None and current_loop is _main_loop:
                        raise RuntimeError("Cannot execute async tool synchronously from within the main event loop thread")
                    
                    future = asyncio.run_coroutine_threadsafe(res, _main_loop)
                    res = future.result()
                else:
                    res = asyncio.run(res)
            
            duration = time.time() - start_time
            tools_logger.info(f"Tool {name} executed", extra={"tool": name, "status": "success", "duration": duration, "error": None})
            return str(res)
        except Exception as e:
            duration = time.time() - start_time
            err_msg = str(e)
            tools_logger.error(f"Tool {name} execution failed", extra={"tool": name, "status": "error", "duration": duration, "error": err_msg})
            return f"Error executing tool {name}: {e}"

    def get_tool_schemas(self) -> list[dict]:
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

def generate_schema(func: Callable) -> dict[str, Any] | None:
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
    schema: dict[str, Any] | None = None
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
