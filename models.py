from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]


class Message(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None


class AgentResponse(BaseModel):
    messages: List[Message]
    usage: Dict[str, int] = Field(default_factory=dict)
