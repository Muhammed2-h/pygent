from models import AgentResponse, Message, ToolCall


def test_message_creation():
    tc = ToolCall(id="1", name="calc", arguments={"expr": "1+1"})
    msg = Message(role="assistant", tool_calls=[tc])
    resp = AgentResponse(messages=[msg], usage={"prompt_tokens": 10})
    assert resp.messages[0].tool_calls[0].name == "calc"
    assert resp.usage["prompt_tokens"] == 10


def test_message_defaults():
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.tool_calls is None
    assert msg.tool_call_id is None


def test_agent_response_default_usage():
    msg = Message(role="assistant", content="Hi there!")
    resp = AgentResponse(messages=[msg])
    assert resp.messages == [msg]
    assert resp.usage == {}


def test_tool_call_message():
    tc = ToolCall(id="call_123", name="weather", arguments={"city": "London"})
    assert tc.id == "call_123"
    assert tc.name == "weather"
    assert tc.arguments == {"city": "London"}

    tool_msg = Message(role="tool", content="20C", tool_call_id="call_123")
    assert tool_msg.role == "tool"
    assert tool_msg.content == "20C"
    assert tool_msg.tool_call_id == "call_123"
