import subprocess
import shlex
import re
import logging
from typing import Dict, Optional, Callable, Any, Tuple

from models import EnvironmentCapability
from .probe import probe_all, probe_capability

logger = logging.getLogger(__name__)

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
        """Get a specific capability by name using targeted probe."""
        return probe_capability(name)

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
        for keyword in sensitive_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_to_check):
                return True
        return False

    def repair_or_install(self, name: str, install_command: str, reason: str = "") -> Tuple[bool, str]:
        """
        Attempt to repair or install a capability.
        Requires confirmation for system-level changes.
        Returns (success, message).
        """
        if self._requires_confirmation(install_command, reason):
            prompt = (
                f"System change requested for '{name}'.\n"
                f"Command: {install_command}\n"
                f"Do you allow this system modification? (y/N)"
            )
            if not self.confirmation_callback(prompt):
                return False, "Installation denied by user."
                
        try:
            # Use shlex.split to avoid shell=True injection risks
            cmd_args = shlex.split(install_command)
            result = subprocess.run(
                cmd_args,
                shell=False,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"Command failed with code {e.returncode}.\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        except FileNotFoundError as e:
            return False, f"Command not found: {e}"
        except Exception as e:
            return False, str(e)

    def verify_and_persist(self, name: str) -> Tuple[bool, str]:
        """
        Verify that a capability is available and persist the fact.
        Returns (success, message).
        """
        cap = self.get_capability(name)
        if cap and cap.available:
            self.persist_fact(
                title=f"Capability: {name}",
                content=f"Capability '{name}' is available and verified."
            )
            return True, f"Capability '{name}' verified successfully."
        return False, f"Capability '{name}' verification failed after installation."

    def persist_fact(self, title: str, content: str) -> None:
        """Persist a fact using the memory store if available."""
        if self.memory_store and hasattr(self.memory_store, "add_memory"):
            # Using mem_type="fact" as implied by the task description
            self.memory_store.add_memory(content=content, mem_type="fact", title=title)
        else:
            logger.debug(f"persist_fact called but memory_store is None (title: '{title}')")

    def ensure_capability(self, name: str, install_command: Optional[str] = None, reason: str = "") -> Tuple[bool, str]:
        """
        Orchestrate the full workflow:
        probe -> capability missing? -> repair/install -> verify -> persist fact
        Returns (success, message).
        """
        cap = self.get_capability(name)
        
        # 1. & 2. Probe and check if available
        if cap and cap.available:
            # Already available, just verify and persist
            return self.verify_and_persist(name)
            
        # 3. Capability missing
        if not install_command:
            return False, f"Capability '{name}' is missing and no install command provided."
            
        # 4. Repair/install
        success, message = self.repair_or_install(name, install_command, reason)
        if success:
            # 5. Verify & 6. Persist fact
            v_success, v_message = self.verify_and_persist(name)
            if v_success:
                return True, f"Installation output: {message}\nVerification: {v_message}"
            else:
                return False, f"Installation output: {message}\nVerification failed: {v_message}"
            
        return False, f"Installation failed:\n{message}"
