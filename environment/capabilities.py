from pydantic import BaseModel, Field


class Capability(BaseModel):
    available: bool = False
    configured: bool = False
    verified: bool = False
    version: str | None = None
    last_checked: str | None = None

class CapabilityRegistry(BaseModel):
    browser: Capability = Field(default_factory=Capability)
    browser_extension: Capability = Field(default_factory=Capability)
    cdp: Capability = Field(default_factory=Capability)
    filesystem: Capability = Field(default_factory=Capability)
    python: Capability = Field(default_factory=Capability)
    shell: Capability = Field(default_factory=Capability)
    git: Capability = Field(default_factory=Capability)
    ocr: Capability = Field(default_factory=Capability)
    vision: Capability = Field(default_factory=Capability)
    desktop: Capability = Field(default_factory=Capability)

