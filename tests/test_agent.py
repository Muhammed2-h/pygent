from typing import List, Optional
from agent import Agent
from models import AgentResponse, Message, ToolCall
from providers.base import BaseProvider
from tools import ToolRegistry


class DummyProvider(BaseProvider):
    def __init__(self, responses: Optional[List[AgentResponse]] = None):
        self.responses = responses or [
            AgentResponse(messages=[Message(role="assistant", content="dummy response")])
        ]
        self.call_count = 0
        self.calls: List[dict] = []

    def complete(
        self,
        messages: List[Message],
        model: str,
        tools: Optional[List[dict]] = None,
    ) -> AgentResponse:
        self.calls.append({"messages": list(messages), "model": model, "tools": tools})
        resp = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1
        return resp


def test_agent_run_simple():
    provider = DummyProvider()
    tools = ToolRegistry()
    agent = Agent(provider, tools, model="test-model", max_steps=1)
    result = agent.run("You are an AI.", "Hello")

    assert len(result) == 1
    assert result[0].role == "assistant"
    assert result[0].content == "dummy response"
    assert provider.call_count == 1


def test_agent_run_with_single_tool_call():
    tool_call = ToolCall(id="call_calc_1", name="calculate", arguments={"expression": "10 * 5"})
    msg_step1 = Message(role="assistant", tool_calls=[tool_call])
    msg_step2 = Message(role="assistant", content="10 * 5 is 50")

    provider = DummyProvider(
        responses=[
            AgentResponse(messages=[msg_step1]),
            AgentResponse(messages=[msg_step2]),
        ]
    )
    tools = ToolRegistry()
    agent = Agent(provider, tools, model="test-model", max_steps=5)

    result = agent.run("You are a calculator.", "What is 10 * 5?")

    assert len(result) == 3
    # Message 0: assistant with tool_calls
    assert result[0].role == "assistant"
    assert result[0].tool_calls == [tool_call]
    # Message 1: tool result
    assert result[1].role == "tool"
    assert result[1].content == "50"
    assert result[1].tool_call_id == "call_calc_1"
    # Message 2: assistant final response
    assert result[2].role == "assistant"
    assert result[2].content == "10 * 5 is 50"
    assert provider.call_count == 2


def test_agent_run_with_multiple_tool_calls_in_one_step():
    tc1 = ToolCall(id="call_1", name="calculate", arguments={"expression": "2 + 2"})
    tc2 = ToolCall(id="call_2", name="calculate", arguments={"expression": "3 * 3"})
    msg_step1 = Message(role="assistant", tool_calls=[tc1, tc2])
    msg_step2 = Message(role="assistant", content="2+2=4 and 3*3=9")

    provider = DummyProvider(
        responses=[
            AgentResponse(messages=[msg_step1]),
            AgentResponse(messages=[msg_step2]),
        ]
    )
    tools = ToolRegistry()
    agent = Agent(provider, tools, model="test-model", max_steps=5)

    result = agent.run("You are an assistant.", "Calculate 2+2 and 3*3")

    assert len(result) == 4
    assert result[0].tool_calls == [tc1, tc2]
    assert result[1].role == "tool"
    assert result[1].content == "4"
    assert result[1].tool_call_id == "call_1"
    assert result[2].role == "tool"
    assert result[2].content == "9"
    assert result[2].tool_call_id == "call_2"
    assert result[3].role == "assistant"
    assert result[3].content == "2+2=4 and 3*3=9"


def test_agent_run_respects_max_steps():
    # Provider always asks for calculation
    tc = ToolCall(id="loop_call", name="calculate", arguments={"expression": "1 + 1"})
    looping_response = AgentResponse(
        messages=[Message(role="assistant", tool_calls=[tc])]
    )
    provider = DummyProvider(responses=[looping_response])
    tools = ToolRegistry()
    agent = Agent(provider, tools, model="test-model", max_steps=3)

    result = agent.run("System", "User")

    # max_steps is 3
    # Step 1: assistant tool call + tool result (2 messages added)
    # Step 2: assistant tool call + tool result (2 messages added)
    # At end of Step 2, same_action triggers strategy switch
    # Step 3: strategy warning (1 message added) + assistant tool call + tool result + max step msg + final response (4 messages added)
    # Total new_messages: 2 + 2 + 1 + 4 = 9
    assert len(result) == 9
    assert result[4].role == "system"
    assert "rethink your strategy" in result[4].content
    assert provider.call_count == 4


def test_agent_passes_schemas_and_model_to_provider():
    provider = DummyProvider()
    tools = ToolRegistry()
    agent = Agent(provider, tools, model="test-model", max_steps=1)
    agent.run("sys prompt", "user query")

    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["model"] == "test-model"
    assert call["tools"] == tools.get_tool_schemas()
    assert len(call["messages"]) == 2
