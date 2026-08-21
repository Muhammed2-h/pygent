# This module is retained for backward compatibility with external scripts.
import warnings
warnings.warn("memory.service is deprecated, use core.memory_service instead", DeprecationWarning, stacklevel=2)

from core.memory_service import MemoryService

__all__ = ["MemoryService"]
