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


class ToolResult(BaseModel):
    ok: bool
    data: Any = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    name: str
    description: str
    schema_def: Dict[str, Any]
    risk_level: str
    category: str


class BrowserResult(ToolResult):
    state_changed: bool = False
    url: Optional[str] = None
    new_tabs: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionEvent(BaseModel):
    type: str
    timestamp: str
    data: Dict[str, Any]


class BrowserTab(BaseModel):
    tab_id: int
    url: str
    title: str
    active: bool = False


class BrowserSession(BaseModel):
    session_id: str
    active_tab_id: Optional[int] = None
    tabs: List[BrowserTab] = Field(default_factory=list)
    connected: bool = False


class MemoryRecord(BaseModel):
    id: Optional[int] = None
    type: str
    title: str
    content: str
    source: Optional[str] = None
    confidence: float = 0.5
    verified: bool = False
    superseded_by: Optional[int] = None
    created_at: str
    updated_at: str


class SkillRecord(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    trigger: Optional[str] = None
    procedure: str
    prerequisites: Optional[str] = None
    verification: Optional[str] = None
    confidence: float = 0.5
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[str] = None
    created_at: str
    updated_at: str


class EnvironmentCapability(BaseModel):
    name: str
    available: bool
    version: Optional[str] = None
    verified: bool = False
    last_checked: Optional[str] = None
