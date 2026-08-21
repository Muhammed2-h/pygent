import ast
import datetime
import operator
import os

from tools.registry import tool

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
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

@tool(
    name="get_time",
    description="Get current time",
    risk_level="safe",
    category="system",
)
def tool_get_time() -> str:
    return datetime.datetime.now().isoformat()

@tool(
    name="calculate",
    description="Calculate math expression",
    risk_level="safe",
    category="system",
)
def tool_calculate(expression: str) -> str:
    try:
        return str(eval_expr(expression))
    except Exception as e:
        return f"Error: {e}"

@tool(
    name="env_info",
    description="Get environment variable",
    risk_level="safe",
    category="system",
)
def tool_env_info(variable: str) -> str:
    return os.getenv(variable, "Not found")
