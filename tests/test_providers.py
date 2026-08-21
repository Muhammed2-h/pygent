import json
from unittest.mock import MagicMock
import pytest
from models import Message, ToolCall, AgentResponse
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
