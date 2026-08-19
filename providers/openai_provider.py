import json
from typing import List, Optional
from openai import OpenAI
from models import AgentResponse, Message, ToolCall
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def complete(
        self,
        messages: List[Message],
        model: str,
        tools: Optional[List[dict]] = None,
    ) -> AgentResponse:
        api_messages = []
        for m in messages:
            msg = {"role": m.role}
            if m.content is not None:
                msg["content"] = m.content
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id is not None:
                msg["tool_call_id"] = m.tool_call_id
            api_messages.append(msg)

        kwargs = {"model": model, "messages": api_messages}
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        parsed_tools = None
        if choice.message.tool_calls:
            parsed_tools = []
            for t in choice.message.tool_calls:
                try:
                    args = json.loads(t.function.arguments)
                    name = t.function.name
                except json.JSONDecodeError:
                    args = {"error": "Invalid JSON arguments"}
                    name = "error"
                parsed_tools.append(ToolCall(
                    id=t.id,
                    name=name,
                    arguments=args
                ))

        out_msg = Message(
            role="assistant",
            content=choice.message.content,
            tool_calls=parsed_tools,
        )
        usage = (
            {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }
            if response.usage
            else {}
        )
        return AgentResponse(messages=[out_msg], usage=usage)
