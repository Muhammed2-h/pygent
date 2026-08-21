from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class Message(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class AgentResponse(BaseModel):
    messages: list[Message]
    usage: dict[str, int] = Field(default_factory=dict)


class EnvironmentCapability(BaseModel):
    name: str
    available: bool
    version: str | None = None
    verified: bool = False
    last_checked: str | None = None
