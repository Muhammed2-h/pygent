from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from memory.privacy import PrivacyFilter

_privacy_filter = PrivacyFilter()

class BrowserState(BaseModel):
    """Holds the current state of the browser."""
    model_config = {"validate_assignment": True}
    
    active_tab: Optional[int] = None
    tabs: List[int] = Field(default_factory=list)
    current_url: Optional[str] = None
    title: Optional[str] = None
    page_signature: Optional[str] = None
    last_action: Optional[Dict[str, Any]] = None
    last_result: Optional[Dict[str, Any]] = None
    navigation: List[str] = Field(default_factory=list)
    new_tabs: List[int] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def scrub_init(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return _privacy_filter.scrub_object(data, abstract_login=True)
        return data
        
    @field_validator('*', mode='before')
    @classmethod
    def scrub_fields(cls, v: Any) -> Any:
        return _privacy_filter.scrub_object(v, abstract_login=True)

    def update(self, **kwargs: Any) -> None:
        """Update state attributes with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
