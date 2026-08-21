from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from memory.privacy import PrivacyFilter

_privacy_filter = PrivacyFilter()

class BrowserState(BaseModel):
    """Holds the current state of the browser."""
    model_config = {"validate_assignment": True}
    
    active_tab: int | None = None
    tabs: list[int] = Field(default_factory=list)
    current_url: str | None = None
    title: str | None = None
    page_signature: str | None = None
    last_action: dict[str, Any] | None = None
    last_result: dict[str, Any] | None = None
    navigation: list[str] = Field(default_factory=list)
    new_tabs: list[int] = Field(default_factory=list)

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
