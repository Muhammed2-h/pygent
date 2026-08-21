# This module is retained for backward compatibility with external scripts.
import warnings
warnings.warn("tools.py is deprecated, use the 'tools' package instead", DeprecationWarning, stacklevel=2)

from tools.registry import ToolRegistry, tool

__all__ = ["ToolRegistry", "tool"]
