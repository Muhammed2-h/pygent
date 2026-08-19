import time
from typing import List, Optional
from models import Message, ToolCall

class AgentState:
    def __init__(self, max_turns: int = 8, max_tool_calls: int = 100, max_wall_time: float = 3600.0):
        self.turns: int = 0
        self.tool_calls_count: int = 0
        self.start_time: float = time.time()
        self.messages: List[Message] = []
        self.new_messages: List[Message] = []
        
        self.max_turns: int = max_turns
        self.max_tool_calls: int = max_tool_calls
        self.max_wall_time: float = max_wall_time
        
        self.last_tool_calls: List[ToolCall] = []
        self.last_errors: List[str] = []
        
        self.strategy: str = "default"

    def get_wall_time(self) -> float:
        return time.time() - self.start_time

    def is_finished(self) -> bool:
        if self.turns >= self.max_turns:
            return True
        if self.tool_calls_count >= self.max_tool_calls:
            return True
        if self.get_wall_time() >= self.max_wall_time:
            return True
        return False
