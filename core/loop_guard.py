
from models import ToolCall


class LoopGuard:
    """Detects infinite loops in agent execution."""
    
    def __init__(self):
        self.history = []
        
    def add_step(self, tool_calls: list[ToolCall], errors: list[str], results: list[str], page_id: str = ""):
        """Records a step in the execution history."""
        self.history.append({
            "tool_calls": tool_calls,
            "errors": errors,
            "results": results,
            "page_id": page_id
        })

    def get_repetition_count(self) -> int:
        """Returns how many times the exact same step has been repeated at the end of the history."""
        if not self.history:
            return 0
            
        last_step = self.history[-1]
        count = 0
        
        for i in range(len(self.history) - 2, -1, -1):
            step = self.history[i]
            if self._is_same_step(step, last_step):
                count += 1
            else:
                break
                
        return count
        
    def _is_same_step(self, step1: dict, step2: dict) -> bool:
        # Check page context
        if step1.get("page_id", "") != step2.get("page_id", ""):
            return False

        # Check tool calls
        tc1 = step1["tool_calls"]
        tc2 = step2["tool_calls"]
        if not self._is_same_tool_calls(tc1, tc2):
            return False
            
        # Check errors
        if step1["errors"] != step2["errors"]:
            return False
            
        # Check results
        if step1["results"] != step2["results"]:
            return False
            
        return True

    def _is_same_tool_calls(self, current: list[ToolCall], last: list[ToolCall]) -> bool:
        if not current and not last:
            return True
        if not current or not last:
            return False
        if len(current) != len(last):
            return False
        for c, l in zip(current, last):
            if c.name != l.name or c.arguments != l.arguments:
                return False
        return True
