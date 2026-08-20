from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class BrowserState(BaseModel):
    """Holds the current state of the browser."""
    active_tab: Optional[int] = None
    tabs: List[int] = Field(default_factory=list)
    current_url: Optional[str] = None
    title: Optional[str] = None
    page_signature: Optional[str] = None
    last_action: Optional[Dict[str, Any]] = None
    last_result: Optional[Dict[str, Any]] = None
    navigation: List[str] = Field(default_factory=list)
    new_tabs: List[int] = Field(default_factory=list)

    def update(self, **kwargs: Any) -> None:
        """Update state attributes with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
