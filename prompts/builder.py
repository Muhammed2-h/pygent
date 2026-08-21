from pathlib import Path

from tools.registry import ToolRegistry


class PromptBuilder:
    def __init__(self, prompts_dir: str | None = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent
        self.prompts_dir = Path(prompts_dir)
        
    def build(self, tools: ToolRegistry | None = None, **kwargs) -> str:
        parts = []
        
        system_path = self.prompts_dir / "system.md"
        if system_path.exists():
            parts.append(system_path.read_text().strip())
            
        evolution_path = self.prompts_dir / "evolution.md"
        if evolution_path.exists():
            parts.append(evolution_path.read_text().strip())
            
        categories: set[str] = set()
        if tools is not None:
            for tool in tools.tools.values():
                if hasattr(tool, 'category') and tool.category:
                    categories.add(tool.category)
                    
        # Check all available category prompts dynamically
        for category in sorted(categories):
            cat_path = self.prompts_dir / f"{category}.md"
            if cat_path.exists():
                parts.append(cat_path.read_text().strip())
                
        return "\n\n".join(parts)
