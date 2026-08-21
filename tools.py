# This module is retained for backward compatibility with external scripts.
import warnings
warnings.warn("tools.py is deprecated, use the 'tools' package instead", DeprecationWarning, stacklevel=2)

from tools.registry import ToolRegistry, tool
from tools.builtin import eval_expr, tool_get_time, tool_calculate, tool_env_info

__all__ = ["ToolRegistry", "tool", "eval_expr", "tool_get_time", "tool_calculate", "tool_env_info"]
