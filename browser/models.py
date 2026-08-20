import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ExtensionRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cmd: str
    tabId: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

class ExtensionResponse(BaseModel):
    id: str
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
