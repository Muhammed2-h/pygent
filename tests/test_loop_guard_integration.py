import pytest

from core.context import ContextBuilder
from core.events import EventBus
from core.loop import AgentLoop
from core.state import AgentState
from models import AgentResponse, Message, ToolCall
from providers.base import BaseProvider
from tools.registry import ToolRegistry, tool


class DummyProvider(BaseProvider):
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    def complete(self, messages, model=None, tools=None, temperature=None):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
        else:
            resp = self.responses[-1]
        self.call_count += 1
        return AgentResponse(messages=[resp], raw=None)

@pytest.fixture
def dummy_tools():
    @tool(name="dummy_tool", description="A dummy tool")
    def dummy_tool(x: int) -> str:
        return f"result {x}"
        
    return ToolRegistry()

def test_loop_guard_integration(dummy_tools):
    repeated_msg = Message(role="assistant", content="calling tool", tool_calls=[
        ToolCall(id="tc_1", name="dummy_tool", arguments={"x": 1})
    ])
    
    provider = DummyProvider(responses=[repeated_msg] * 10)
    state = AgentState()
    context = ContextBuilder()
    events = EventBus()
    
    loop = AgentLoop(
        provider=provider,
        tools=dummy_tools,
        model="dummy-model",
        context=context,
        state=state,
        events=events
    )
    
    import tools.human
    original_ask_user = tools.human.tool_ask_user
    
    try:
        def mock_ask_user(question, choices=None, risk=None, reason=None):
            return "abort"
            
        tools.human.tool_ask_user = mock_ask_user
        
        loop.run("sys prompt", "user input")
        
        # Check that it aborted
        assert state.turns == 4, f"Expected 4 turns, got {state.turns}"
        assert any("User aborted due to infinite loop" in msg.content for msg in state.messages if msg.role == "system")
        assert any("consider a different approach" in msg.content for msg in state.messages if msg.role == "system")
        assert state.strategy == "default"
        
    finally:
        tools.human.tool_ask_user = original_ask_user

def test_loop_guard_integration_continue(dummy_tools):
    repeated_msg = Message(role="assistant", content="calling tool", tool_calls=[
        ToolCall(id="tc_1", name="dummy_tool", arguments={"x": 1})
    ])
    
    provider = DummyProvider(responses=[repeated_msg] * 10)
    state = AgentState(max_turns=6)
    context = ContextBuilder()
    events = EventBus()
    
    loop = AgentLoop(
        provider=provider,
        tools=dummy_tools,
        model="dummy-model",
        context=context,
        state=state,
        events=events
    )
    
    import tools.human
    original_ask_user = tools.human.tool_ask_user
    
    try:
        def mock_ask_user(question, choices=None, risk=None, reason=None):
            return "continue"
            
        tools.human.tool_ask_user = mock_ask_user
        
        loop.run("sys prompt", "user input")
        
        assert state.turns == 5
        assert any("User responded to loop guard: continue" in msg.content for msg in state.messages if msg.role == "user")
        
    finally:
        tools.human.tool_ask_user = original_ask_user
