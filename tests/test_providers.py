import json
from unittest.mock import MagicMock, patch

import pytest

from models import AgentResponse, Message, ToolCall
from providers.base import BaseProvider
from providers.openai_provider import OpenAIProvider


def test_base_provider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseProvider()


def test_openai_provider_init():
    provider = OpenAIProvider("fake_key")
    assert provider.client.api_key == "fake_key"


def test_openai_provider_complete_text():
    provider = OpenAIProvider("fake_key")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello there!"
    mock_choice.message.tool_calls = None
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    provider.client.chat.completions.create = MagicMock(return_value=mock_response)

    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hi"),
    ]

    result = provider.complete(messages=messages, model="gpt-4o")

    assert isinstance(result, AgentResponse)
    assert len(result.messages) == 1
    assert result.messages[0].role == "assistant"
    assert result.messages[0].content == "Hello there!"
    assert result.messages[0].tool_calls is None
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}

    provider.client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hi"},
        ],
    )


def test_openai_provider_complete_with_tool_call_response():
    provider = OpenAIProvider("fake_key")

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.function.name = "get_weather"
    mock_tool_call.function.arguments = json.dumps({"location": "San Francisco"})

    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_choice.message.tool_calls = [mock_tool_call]

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 25
    mock_response.usage.completion_tokens = 12

    provider.client.chat.completions.create = MagicMock(return_value=mock_response)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for location",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                },
            },
        }
    ]

    messages = [Message(role="user", content="What's the weather in SF?")]
    result = provider.complete(messages=messages, model="gpt-4o", tools=tools)

    assert isinstance(result, AgentResponse)
    assert len(result.messages) == 1
    msg = result.messages[0]
    assert msg.role == "assistant"
    assert msg.content is None
    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].id == "call_123"
    assert msg.tool_calls[0].name == "get_weather"
    assert msg.tool_calls[0].arguments == {"location": "San Francisco"}

    provider.client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=[{"role": "user", "content": "What's the weather in SF?"}],
        tools=tools,
    )


def test_openai_provider_translates_message_history_with_tool_calls_and_tool_results():
    provider = OpenAIProvider("fake_key")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "It is sunny in SF."
    mock_choice.message.tool_calls = None
    mock_response.choices = [mock_choice]
    mock_response.usage = None

    provider.client.chat.completions.create = MagicMock(return_value=mock_response)

    messages = [
        Message(role="user", content="What's the weather?"),
        Message(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_abc",
                    name="get_weather",
                    arguments={"location": "SF"},
                )
            ],
        ),
        Message(
            role="tool",
            content="72 degrees and sunny",
            tool_call_id="call_abc",
        ),
    ]

    result = provider.complete(messages=messages, model="gpt-4o")

    assert result.messages[0].content == "It is sunny in SF."
    assert result.usage == {}

    provider.client.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "What's the weather?"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "SF"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": "72 degrees and sunny",
                "tool_call_id": "call_abc",
            },
        ],
    )

from config import Config
from providers.factory import create_provider


def test_create_provider_openai():
    config = Config(provider="openai", openai_api_key="test-key")
    provider = create_provider(config)
    assert isinstance(provider, OpenAIProvider)
    assert provider.client.api_key == "test-key"

def test_create_provider_openai_missing_key():
    config = Config(provider="openai", openai_api_key=None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY must be set when using openai provider"):
        create_provider(config)

def test_create_provider_unsupported():
    config = Config(provider="unsupported_provider", openai_api_key="test-key")
    with pytest.raises(ValueError, match="Unsupported provider: unsupported_provider"):
        create_provider(config)

import openai

import tools.registry


def test_openai_provider_empty_response():
    provider = OpenAIProvider("fake_key")
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = ""
    mock_choice.message.tool_calls = None
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 0
    provider.client.chat.completions.create = MagicMock(return_value=mock_response)

    result = provider.complete(messages=[Message(role="user", content="Hi")], model="gpt-4o")
    assert result.messages[0].content == ""
    assert result.messages[0].tool_calls is None

def test_openai_provider_malformed_json_tool_call():
    provider = OpenAIProvider("fake_key")
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_bad"
    mock_tool_call.function.name = "get_weather"
    mock_tool_call.function.arguments = "{bad json"
    
    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_choice.message.tool_calls = [mock_tool_call]
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    provider.client.chat.completions.create = MagicMock(return_value=mock_response)
    
    result = provider.complete(messages=[Message(role="user", content="Hi")], model="gpt-4o")
    tc = result.messages[0].tool_calls[0]
    assert tc.name == "error"
    assert tc.arguments == {"error": "Invalid JSON arguments"}

@patch("time.sleep")
def test_openai_provider_retries_on_rate_limit(mock_sleep):
    provider = OpenAIProvider("fake_key")
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Success!"
    mock_choice.message.tool_calls = None
    mock_response.choices = [mock_choice]
    
    mock_create = MagicMock(side_effect=[
        openai.RateLimitError(message="Rate limited", response=MagicMock(), body=None),
        mock_response
    ])
    provider.client.chat.completions.create = mock_create
    
    result = provider.complete(messages=[Message(role="user", content="Hi")], model="gpt-4o")
    assert result.messages[0].content == "Success!"
    assert mock_create.call_count == 2


def test_openai_provider_context_overflow_truncation():
    provider = OpenAIProvider("fake_key")
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Truncated Success"
    mock_choice.message.tool_calls = None
    mock_response.choices = [mock_choice]
    
    def side_effect(*args, **kwargs):
        if len(kwargs["messages"]) > 2:
            raise openai.BadRequestError(message="context_length_exceeded", response=MagicMock(), body=None)
        return mock_response
        
    mock_create = MagicMock(side_effect=side_effect)
    provider.client.chat.completions.create = mock_create
    
    messages = [
        Message(role="assistant", tool_calls=[ToolCall(id="call_abc", name="func", arguments={"a": 1})]),
        Message(role="tool", content="tool result", tool_call_id="call_abc"),
        Message(role="user", content="New message")
    ]
    result = provider.complete(messages=messages, model="gpt-4o")
    
    assert result.messages[0].content == "Truncated Success"
    # Should drop both the assistant tool call and the tool result
    assert mock_create.call_count == 2
    assert len(mock_create.call_args[1]["messages"]) == 1
    assert mock_create.call_args[1]["messages"][0]["content"] == "New message"

from tools.registry import ToolRegistry, tool


def test_openai_provider_valid_tool_call_parsing():
    provider = OpenAIProvider("fake_key")
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_valid"
    mock_tool_call.function.name = "get_weather"
    mock_tool_call.function.arguments = '{"location": "Tokyo"}'
    
    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_choice.message.tool_calls = [mock_tool_call]
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    provider.client.chat.completions.create = MagicMock(return_value=mock_response)
    
    result = provider.complete(messages=[Message(role="user", content="Hi")], model="gpt-4o")
    tc = result.messages[0].tool_calls[0]
    assert tc.id == "call_valid"
    assert tc.name == "get_weather"
    assert tc.arguments == {"location": "Tokyo"}

def test_openai_provider_tool_schema_generation():
    @tool(name="test_tool", description="A test tool")
    def test_tool(param1: str, param2: int = 5):
        return "test"
        
    registry = ToolRegistry()
    registry.tools['test_tool'] = tools.registry._global_tools['test_tool']
    schemas = registry.get_tool_schemas()
    
    provider = OpenAIProvider("fake_key")
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Tool info"
    mock_choice.message.tool_calls = None
    mock_response.choices = [mock_choice]
    
    provider.client.chat.completions.create = MagicMock(return_value=mock_response)
    
    provider.complete(messages=[Message(role="user", content="Hi")], model="gpt-4o", tools=schemas)
    
    call_args = provider.client.chat.completions.create.call_args[1]
    assert "tools" in call_args
    passed_tools = call_args["tools"]
    
    test_tool_schema = next((t for t in passed_tools if t["function"]["name"] == "test_tool"), None)
    assert test_tool_schema is not None
    assert test_tool_schema["type"] == "function"

    assert test_tool_schema["function"]["name"] == "test_tool"
    assert "param1" in test_tool_schema["function"]["parameters"]["properties"]

