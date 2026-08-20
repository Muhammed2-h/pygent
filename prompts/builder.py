import os
from pathlib import Path
from typing import Optional, Set
from tools.registry import ToolRegistry

class PromptBuilder:
    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent
        self.prompts_dir = Path(prompts_dir)
        
    def build(self, tools: Optional[ToolRegistry] = None, **kwargs) -> str:
        parts = []
        
        system_path = self.prompts_dir / "system.md"
        if system_path.exists():
            parts.append(system_path.read_text().strip())
            
        categories: Set[str] = set()
        if tools is not None:
            for tool in tools.tools.values():
                if hasattr(tool, 'category') and tool.category:
                    categories.add(tool.category)
                    
        # Check specific domains
        if "browser" in categories:
            browser_path = self.prompts_dir / "browser.md"
            if browser_path.exists():
                parts.append(browser_path.read_text().strip())
                
        if "memory" in categories:
            memory_path = self.prompts_dir / "memory.md"
            if memory_path.exists():
                parts.append(memory_path.read_text().strip())
                
        if "evolution" in categories:
            evo_path = self.prompts_dir / "evolution.md"
            if evo_path.exists():
                parts.append(evo_path.read_text().strip())
                
        return "\n\n".join(parts)
