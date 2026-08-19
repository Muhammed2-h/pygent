import ast
import datetime
import operator
import os
from typing import Any, Dict, List

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.BitXor: operator.xor,
    ast.USub: operator.neg,
}


def eval_expr(expr: str):
    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            return _OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return _OPERATORS[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(node)

    return _eval(ast.parse(expr, mode="eval").body)


def tool_get_time() -> str:
    return datetime.datetime.now().isoformat()


def tool_calculate(expression: str) -> str:
    try:
        return str(eval_expr(expression))
    except Exception as e:
        return f"Error: {e}"


def tool_env_info(variable: str) -> str:
    return os.getenv(variable, "Not found")


class ToolRegistry:
    def __init__(self):
        self.tools = {
            "get_time": tool_get_time,
            "calculate": tool_calculate,
            "env_info": tool_env_info,
        }

    def execute(self, name: str, args: Dict[str, Any]) -> str:
        if name not in self.tools:
            return f"Error: tool {name} not found"
        return str(self.tools[name](**args))

    def get_tool_schemas(self) -> List[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": "Get current time",
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Calculate math expression",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"},
                        },
                        "required": ["expression"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "env_info",
                    "description": "Get environment variable",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "variable": {"type": "string"},
                        },
                        "required": ["variable"],
                    },
                },
            },
        ]
