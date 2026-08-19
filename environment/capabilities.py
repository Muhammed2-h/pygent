from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Capability(BaseModel):
    available: bool = False
    configured: bool = False
    verified: bool = False
    version: Optional[str] = None
    last_checked: Optional[str] = None

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
    
    def update_from_probes(self, probes: Dict[str, Any]):
        """
        Update the capability registry based on probe results.
        `probes` is expected to be a dictionary mapping probe names to EnvironmentCapability or similar objects.
        """
        # Map python
        if "python" in probes:
            self.python.available = probes["python"].available
            self.python.verified = probes["python"].verified
            self.python.version = probes["python"].version
            self.python.last_checked = probes["python"].last_checked
            if self.python.available:
                self.python.configured = True
                
        # Map git
        if "git" in probes:
            self.git.available = probes["git"].available
            self.git.verified = probes["git"].verified
            self.git.version = probes["git"].version
            self.git.last_checked = probes["git"].last_checked
            if self.git.available:
                self.git.configured = True
                
        # Map browser from chrome
        if "chrome" in probes:
            self.browser.available = probes["chrome"].available
            self.browser.verified = probes["chrome"].verified
            self.browser.version = probes["chrome"].version
            self.browser.last_checked = probes["chrome"].last_checked
            if self.browser.available:
                self.browser.configured = True
                
        # Map browser_extension from chrome_extension
        if "chrome_extension" in probes:
            self.browser_extension.available = probes["chrome_extension"].available
            self.browser_extension.verified = probes["chrome_extension"].verified
            self.browser_extension.version = probes["chrome_extension"].version
            self.browser_extension.last_checked = probes["chrome_extension"].last_checked
            if self.browser_extension.available:
                self.browser_extension.configured = True

        # Map cdp from websocket_port / http_bridge
        if "websocket_port" in probes:
            self.cdp.available = probes["websocket_port"].available
            self.cdp.verified = probes["websocket_port"].verified
            self.cdp.version = probes["websocket_port"].version
            self.cdp.last_checked = probes["websocket_port"].last_checked
            if self.cdp.available:
                self.cdp.configured = True
                
        # Map filesystem
        if "filesystem" in probes:
            self.filesystem.available = probes["filesystem"].available
            self.filesystem.verified = probes["filesystem"].verified
            self.filesystem.version = probes["filesystem"].version
            self.filesystem.last_checked = probes["filesystem"].last_checked
            if self.filesystem.available:
                self.filesystem.configured = True

        # Map shell from os (as a fallback since os represents basic shell/OS capabilities)
        if "os" in probes:
            self.shell.available = probes["os"].available
            self.shell.verified = probes["os"].verified
            self.shell.version = probes["os"].version
            self.shell.last_checked = probes["os"].last_checked
            if self.shell.available:
                self.shell.configured = True

