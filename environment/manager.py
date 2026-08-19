import subprocess
from typing import Dict, Optional, Callable, Any

from models import EnvironmentCapability
from .probe import probe_all


class EnvironmentManager:
    """
    Manages environment capabilities, orchestrating probes, repairs, and persisting facts.
    """

    def __init__(self, confirmation_callback: Optional[Callable[[str], bool]] = None, memory_store: Any = None):
        """
        Initialize the EnvironmentManager.
        
        Args:
            confirmation_callback: A function that takes a prompt string and returns True if confirmed.
                                   If None, all system changes are denied by default.
            memory_store: A memory storage instance to persist facts (e.g. MemoryStore).
        """
        # Default to denying system changes if no callback is provided
        self.confirmation_callback = confirmation_callback or (lambda prompt: False)
        self.memory_store = memory_store

    def check_capabilities(self) -> Dict[str, EnvironmentCapability]:
        """Run all probes and return current capabilities."""
        return probe_all()

    def get_capability(self, name: str) -> Optional[EnvironmentCapability]:
        """Get a specific capability by name."""
        capabilities = self.check_capabilities()
        return capabilities.get(name)

    def _requires_confirmation(self, command: str, reason: str = "") -> bool:
        """
        Check if an action requires explicit user confirmation.
        Requires confirmation for:
        sudo, apt, system packages, driver installs, browser modifications.
        """
        sensitive_keywords = [
            "sudo", 
            "apt", "apt-get", "dpkg", "snap", "flatpak", "yum", "dnf", "pacman", # system packages
            "driver", "modprobe", "insmod",                                      # driver installs
            "browser", "chrome", "firefox", "chromium", "extensions"             # browser modifications
        ]
        
        text_to_check = f"{command} {reason}".lower()
        return any(keyword in text_to_check for keyword in sensitive_keywords)

    def repair_or_install(self, name: str, install_command: str, reason: str = "") -> bool:
        """
        Attempt to repair or install a capability.
        Requires confirmation for system-level changes.
        """
        if self._requires_confirmation(install_command, reason):
            prompt = (
                f"System change requested for '{name}'.\n"
                f"Command: {install_command}\n"
                f"Do you allow this system modification? (y/N)"
            )
            if not self.confirmation_callback(prompt):
                return False
                
        try:
            subprocess.run(
                install_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def verify_and_persist(self, name: str) -> bool:
        """
        Verify that a capability is available and persist the fact.
        """
        cap = self.get_capability(name)
        if cap and cap.available:
            self.persist_fact(
                title=f"Capability: {name}",
                content=f"Capability '{name}' is available and verified."
            )
            return True
        return False

    def persist_fact(self, title: str, content: str) -> None:
        """Persist a fact using the memory store if available."""
        if self.memory_store and hasattr(self.memory_store, "add_memory"):
            # Using mem_type="fact" as implied by the task description
            self.memory_store.add_memory(content=content, mem_type="fact", title=title)

    def ensure_capability(self, name: str, install_command: Optional[str] = None, reason: str = "") -> bool:
        """
        Orchestrate the full workflow:
        probe -> capability missing? -> repair/install -> verify -> persist fact
        """
        cap = self.get_capability(name)
        
        # 1. & 2. Probe and check if available
        if cap and cap.available:
            # Already available, just verify and persist
            self.verify_and_persist(name)
            return True
            
        # 3. Capability missing
        if not install_command:
            return False
            
        # 4. Repair/install
        success = self.repair_or_install(name, install_command, reason)
        if success:
            # 5. Verify & 6. Persist fact
            return self.verify_and_persist(name)
            
        return False
