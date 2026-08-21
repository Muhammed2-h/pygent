from core.loop_guard import LoopGuard
from models import ToolCall


def test_loop_guard_basic():
    guard = LoopGuard()
    
    tc1 = [ToolCall(id="1", name="test", arguments={"a": 1})]
    
    # 1st step
    guard.add_step(tc1, [""], ["result1"])
    assert guard.get_repetition_count() == 0
    
    # 2nd step (1st repeat)
    guard.add_step(tc1, [""], ["result1"])
    assert guard.get_repetition_count() == 1
    
    # 3rd step (2nd repeat)
    guard.add_step(tc1, [""], ["result1"])
    assert guard.get_repetition_count() == 2
    
    # 4th step (3rd repeat)
    guard.add_step(tc1, [""], ["result1"])
    assert guard.get_repetition_count() == 3

def test_loop_guard_different_args():
    guard = LoopGuard()
    
    tc1 = [ToolCall(id="1", name="test", arguments={"a": 1})]
    tc2 = [ToolCall(id="2", name="test", arguments={"a": 2})]
    
    guard.add_step(tc1, [""], ["result1"])
    guard.add_step(tc1, [""], ["result1"])
    assert guard.get_repetition_count() == 1
    
    guard.add_step(tc2, [""], ["result1"])
    assert guard.get_repetition_count() == 0

def test_loop_guard_different_results():
    guard = LoopGuard()
    
    tc1 = [ToolCall(id="1", name="test", arguments={"a": 1})]
    
    guard.add_step(tc1, [""], ["result1"])
    guard.add_step(tc1, [""], ["result1"])
    assert guard.get_repetition_count() == 1
    
    guard.add_step(tc1, [""], ["result2"])
    assert guard.get_repetition_count() == 0

