import pytest
from memory.lifecycle import update_checkpoint, get_checkpoint, clear_checkpoint

def test_checkpoint_lifecycle():
    clear_checkpoint()
    assert get_checkpoint() == ""
    
    update_checkpoint(
        objective="Find the bug",
        constraints=["Do not change the API"],
        important_findings=["Bug is in line 42"],
        failed_attempts=["Tried changing line 40"],
        next_action="Fix line 42"
    )
    
    cp = get_checkpoint()
    assert "Find the bug" in cp
    assert "Do not change the API" in cp
    assert "Bug is in line 42" in cp
    assert "Tried changing line 40" in cp
    assert "Fix line 42" in cp
    
    # Update partial
    update_checkpoint(next_action="Run tests")
    cp = get_checkpoint()
    assert "Run tests" in cp
    assert "Fix line 42" not in cp
    assert "Find the bug" in cp
    
    clear_checkpoint()
    assert get_checkpoint() == ""

def test_checkpoint_size_limit():
    clear_checkpoint()
    long_string = "a" * 2000
    update_checkpoint(objective=long_string)
    cp = get_checkpoint()
    assert len(cp) < 1500 # rough approximation for 300 tokens
