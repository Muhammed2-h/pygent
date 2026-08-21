from core.state import ExecutionState


def test_execution_state_initialization():
    state = ExecutionState(task_id="task-123", session_id="session-456")
    assert state.task_id == "task-123"
    assert state.session_id == "session-456"
    assert state.turn == 0
    assert state.current_goal is None
    assert state.current_step is None
    assert state.constraints == []
    assert state.observations == []
    assert state.failures == []
    assert state.last_action is None
    assert state.last_result is None
    assert state.working_memory == {}
    assert state.browser_state == {}
    assert state.environment_state == {}

def test_execution_state_mutations():
    state = ExecutionState(task_id="task-123", session_id="session-456")
    
    state.current_goal = "Find the button"
    state.current_step = "Click the button"
    state.turn += 1
    state.constraints.append("Do not use external APIs")
    state.observations.append("Button is visible")
    state.failures.append("Timeout on first click")
    state.last_action = {"action": "click", "target": "button"}
    state.last_result = {"status": "success"}
    state.working_memory["button_id"] = "btn-submit"
    state.browser_state["url"] = "https://example.com"
    state.environment_state["os"] = "linux"
    
    assert state.current_goal == "Find the button"
    assert state.current_step == "Click the button"
    assert state.turn == 1
    assert state.constraints == ["Do not use external APIs"]
    assert state.observations == ["Button is visible"]
    assert state.failures == ["Timeout on first click"]
    assert state.last_action == {"action": "click", "target": "button"}
    assert state.last_result == {"status": "success"}
    assert state.working_memory == {"button_id": "btn-submit"}
    assert state.browser_state == {"url": "https://example.com"}
    assert state.environment_state == {"os": "linux"}
