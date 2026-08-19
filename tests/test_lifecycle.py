import pytest
from memory.lifecycle import MemoryCheckpoint

def test_checkpoint_lifecycle():
    checkpoint = MemoryCheckpoint()
    assert checkpoint.get_checkpoint() == ""
    
    checkpoint.update_checkpoint(
        objective="Find the bug",
        constraints=["Do not change the API"],
        important_findings=["Bug is in line 42"],
        failed_attempts=["Tried changing line 40"],
        next_action="Fix line 42"
    )
    
    cp = checkpoint.get_checkpoint()
    assert "Find the bug" in cp
    assert "Do not change the API" in cp
    assert "Bug is in line 42" in cp
    assert "Tried changing line 40" in cp
    assert "Fix line 42" in cp
    
    # Update partial
    checkpoint.update_checkpoint(next_action="Run tests")
    cp = checkpoint.get_checkpoint()
    assert "Run tests" in cp
    assert "Fix line 42" not in cp
    assert "Find the bug" in cp
    
    checkpoint.clear_checkpoint()
    assert checkpoint.get_checkpoint() == ""

def test_checkpoint_size_limit():
    checkpoint = MemoryCheckpoint()
    long_string = "a" * 2000
    checkpoint.update_checkpoint(objective=long_string)
    cp = checkpoint.get_checkpoint()
    assert len(cp) <= checkpoint.max_chars
