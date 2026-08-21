
import pytest

from prompts.builder import PromptBuilder
from tools.registry import ToolRegistry, _global_tools, tool


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
    assert "Evolution Instructions" in result
    
def test_prompt_builder_missing_files(tmp_path):
    _global_tools.clear()
    registry = ToolRegistry()
    builder = PromptBuilder(prompts_dir=str(tmp_path))
    result = builder.build(tools=registry)
    assert result == ""

def test_real_system_prompt_exists():
    from prompts.builder import PromptBuilder
    builder = PromptBuilder() # default dir
    system_path = builder.prompts_dir / "system.md"
    assert system_path.exists()
    content = system_path.read_text()
    assert "Identity" in content
    assert "Tool Policy" in content
    assert "Safety Policy" in content

def test_real_browser_prompt_exists():
    from prompts.builder import PromptBuilder
    builder = PromptBuilder()
    browser_path = builder.prompts_dir / "browser.md"
    assert browser_path.exists()
    content = browser_path.read_text().lower()
    assert "observe before acting" in content
    assert "prefer precise js" in content
    assert "avoid unnecessary dom dumps" in content
    assert "never guess selectors" in content
    assert "separate navigation" in content
    assert "verify actions" in content
    assert "use cdp for difficult cases" in content
    assert "switch strategies" in content
    assert "ask user when blocked" in content

def test_real_memory_prompt_exists():
    from prompts.builder import PromptBuilder
    builder = PromptBuilder()
    memory_path = builder.prompts_dir / "memory.md"
    assert memory_path.exists()
    content = memory_path.read_text().lower()
    assert "store verified information" in content
    assert "prefer reusable procedures" in content
    assert "avoid temporary reasoning" in content
    assert "deduplicate memories" in content
    assert "update stale skills" in content
    assert "preserve environment facts" in content
    assert "record failure lessons" in content


def test_real_evolution_prompt_exists():
    from prompts.builder import PromptBuilder
    builder = PromptBuilder()
    evolution_path = builder.prompts_dir / "evolution.md"
    assert evolution_path.exists()
    content = evolution_path.read_text().lower()
    assert "discover" in content
    assert "execute" in content
    assert "verify" in content
    assert "repair" in content
    assert "crystallize" in content
    assert "reuse" in content
    assert "task" in content
    assert "candidate skill" in content
    assert "verification" in content
    assert "persistence" in content
    assert "revalidation" in content
