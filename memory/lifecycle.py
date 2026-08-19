import json
from typing import Dict, Any, Optional, List

_checkpoint: Dict[str, Any] = {}
# Rough token approximation: 1 token ~= 4 chars. 300 tokens ~= 1200 chars.
# We will truncate long strings and keep lists short.
MAX_FIELD_LENGTH = 300
MAX_LIST_ITEMS = 3

def _truncate(value: str) -> str:
    if len(value) > MAX_FIELD_LENGTH:
        return value[:MAX_FIELD_LENGTH] + "..."
    return value

def update_checkpoint(
    objective: Optional[str] = None,
    constraints: Optional[List[str]] = None,
    important_findings: Optional[List[str]] = None,
    failed_attempts: Optional[List[str]] = None,
    next_action: Optional[str] = None
) -> None:
    global _checkpoint
    if objective is not None:
        _checkpoint["objective"] = _truncate(objective)
    if constraints is not None:
        _checkpoint["constraints"] = [_truncate(c) for c in constraints][-MAX_LIST_ITEMS:]
    if important_findings is not None:
        _checkpoint["important_findings"] = [_truncate(f) for f in important_findings][-MAX_LIST_ITEMS:]
    if failed_attempts is not None:
        _checkpoint["failed_attempts"] = [_truncate(f) for f in failed_attempts][-MAX_LIST_ITEMS:]
    if next_action is not None:
        _checkpoint["next_action"] = _truncate(next_action)

def get_checkpoint() -> str:
    global _checkpoint
    if not _checkpoint:
        return ""
    
    formatted = "=== WORKING MEMORY CHECKPOINT ===\n"
    for key, value in _checkpoint.items():
        if value:
            formatted += f"{key.replace('_', ' ').title()}:\n"
            if isinstance(value, list):
                for item in value:
                    formatted += f"- {item}\n"
            else:
                formatted += f"{value}\n"
            formatted += "\n"
    
    return formatted.strip()

def clear_checkpoint() -> None:
    global _checkpoint
    _checkpoint.clear()
