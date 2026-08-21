import logging
from typing import Optional
from .registry import tool
from .human import tool_ask_user
from environment.manager import EnvironmentManager
from config import load_config
from pathlib import Path

logger = logging.getLogger(__name__)

def confirmation_callback(prompt: str) -> bool:
    response = tool_ask_user(
        question=prompt,
        choices=["y", "n"],
        risk="medium",
        reason="System modification requested."
    )
    return response.strip().lower() == "y"

@tool(
    name="env_expand",
    description="Expand the agent's environment by installing missing dependencies (e.g. pip package, browser extension, CLI tools).",
    category="environment"
)
def tool_env_expand(name: str, install_command: str, reason: str = "") -> str:
    """
    Expand the agent's environment capabilities by installing dependencies.
    """
    # Try to initialize MemoryStore for persistence
    memory_store = None
    try:
        from memory.storage import MemoryStore
        config = load_config()
        if config and hasattr(config, "data_dir") and config.data_dir:
            base_dir = Path(config.data_dir)
            db_path = base_dir / "memory" / "memory.db"
            skills_dir = base_dir / "skills"
            memory_store = MemoryStore(str(db_path), skills_dir=skills_dir)
    except Exception as e:
        logger.debug(f"Failed to initialize MemoryStore for env_expand: {e}")

    manager = EnvironmentManager(confirmation_callback=confirmation_callback, memory_store=memory_store)
    
    try:
        success, message = manager.ensure_capability(name, install_command, reason)
    except Exception as e:
        success = False
        message = str(e)
    finally:
        if memory_store:
            try:
                memory_store.close()
            except:
                pass
                
    if success:
        return f"Successfully expanded environment with capability '{name}'.\nDetails:\n{message}"
    else:
        return f"Failed to expand environment with capability '{name}'.\nError Details:\n{message}"
