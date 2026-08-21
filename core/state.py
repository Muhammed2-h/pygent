import time
from typing import List, Optional
from models import Message, ToolCall
from core.loop_guard import LoopGuard

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
        
        from memory.lifecycle import MemoryCheckpoint
        self.checkpoint = MemoryCheckpoint()
        self.loop_guard = LoopGuard()

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

class ExecutionState:
    def __init__(self, task_id: str, session_id: str):
        self.task_id: str = task_id
        self.session_id: str = session_id
        self.turn: int = 0
        self.current_goal: Optional[str] = None
        self.current_step: Optional[str] = None
        self.constraints: List[str] = []
        self.observations: List[str] = []
        self.failures: List[str] = []
        self.last_action: Optional[dict] = None
        self.last_result: Optional[dict] = None
        self.working_memory: dict = {}
        self.browser_state: dict = {}
        self.environment_state: dict = {}
