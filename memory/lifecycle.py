import json
from typing import Dict, Any, Optional, List

class MemoryCheckpoint:
    def __init__(self, max_tokens: int = 300, chars_per_token: int = 4):
        self._checkpoint: Dict[str, Any] = {}
        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token
        self.max_chars = max_tokens * chars_per_token
        self.max_list_items = 3

    def update_checkpoint(
        self,
        objective: Optional[str] = None,
        constraints: Optional[List[str]] = None,
        important_findings: Optional[List[str]] = None,
        failed_attempts: Optional[List[str]] = None,
        next_action: Optional[str] = None
    ) -> None:
        if objective is not None:
            self._checkpoint["objective"] = objective
        if constraints is not None:
            # Keep first constraints (fundamental rules)
            self._checkpoint["constraints"] = constraints[:self.max_list_items]
        if important_findings is not None:
            # Keep latest findings
            self._checkpoint["important_findings"] = important_findings[-self.max_list_items:]
        if failed_attempts is not None:
            # Keep latest failed attempts
            self._checkpoint["failed_attempts"] = failed_attempts[-self.max_list_items:]
        if next_action is not None:
            self._checkpoint["next_action"] = next_action

    def get_checkpoint(self) -> str:
        if not self._checkpoint:
            return ""
        
        formatted = "=== WORKING MEMORY CHECKPOINT ===\n"
        for key, value in self._checkpoint.items():
            if value:
                formatted += f"{key.replace('_', ' ').title()}:\n"
                if isinstance(value, list):
                    for item in value:
                        formatted += f"- {item}\n"
                else:
                    formatted += f"{value}\n"
                formatted += "\n"
        
        formatted = formatted.strip()
        if len(formatted) > self.max_chars:
            return formatted[:self.max_chars - 3] + "..."
        return formatted

    def clear_checkpoint(self) -> None:
        self._checkpoint.clear()
