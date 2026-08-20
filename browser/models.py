import uuid
from typing import Any
from pydantic import BaseModel, Field

class ExtensionRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cmd: str
    tabId: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

class ExtensionResponse(BaseModel):
    id: str
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None
