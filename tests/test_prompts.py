import pytest
from pathlib import Path
from tools.registry import ToolRegistry, tool, _global_tools
from prompts.builder import PromptBuilder

@pytest.fixture(autouse=True)
def preserve_global_tools():
    saved = _global_tools.copy()
    yield
    _global_tools.clear()
    _global_tools.update(saved)

@pytest.fixture
def temp_prompts(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "system.md").write_text("System Base")
    (prompts_dir / "browser.md").write_text("Browser Instructions")
    (prompts_dir / "memory.md").write_text("Memory Instructions")
    (prompts_dir / "evolution.md").write_text("Evolution Instructions")
    return prompts_dir

def test_prompt_builder_all(temp_prompts):
    _global_tools.clear()
    
    @tool("browse", "browse", category="browser")
    def browse_tool(): pass
    
    @tool("mem", "mem", category="memory")
    def mem_tool(): pass
    
    @tool("evo", "evo", category="evolution")
    def evo_tool(): pass
    
    registry = ToolRegistry()
    
    builder = PromptBuilder(prompts_dir=str(temp_prompts))
    result = builder.build(tools=registry)
    
    assert "System Base" in result
    assert "Browser Instructions" in result
    assert "Memory Instructions" in result
    assert "Evolution Instructions" in result

def test_prompt_builder_some(temp_prompts):
    _global_tools.clear()
    
    @tool("browse", "browse", category="browser")
    def browse_tool(): pass
    
    registry = ToolRegistry()
    
    builder = PromptBuilder(prompts_dir=str(temp_prompts))
    result = builder.build(tools=registry)
    
    assert "System Base" in result
    assert "Browser Instructions" in result
    assert "Memory Instructions" not in result
    assert "Evolution Instructions" not in result
    
def test_prompt_builder_missing_files(tmp_path):
    _global_tools.clear()
    registry = ToolRegistry()
    builder = PromptBuilder(prompts_dir=str(tmp_path))
    result = builder.build(tools=registry)
    assert result == ""
