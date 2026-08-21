import json
import time
import openai
from typing import List, Optional
from openai import OpenAI
from models import AgentResponse, Message, ToolCall
from providers.base import BaseProvider


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
                            "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments,
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

        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                break
            except (openai.RateLimitError, openai.APIConnectionError) as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                retry_delay *= 2
            except openai.BadRequestError as e:
                if "context_length_exceeded" in str(e) or (hasattr(e, "code") and e.code == "context_length_exceeded"):
                    removed = False
                    for i, msg in enumerate(kwargs["messages"]):
                        if msg["role"] != "system":
                            kwargs["messages"].pop(i)
                            removed = True
                            break
                    if not removed:
                        raise e
                    continue
                else:
                    raise

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
            if hasattr(response, "usage") and response.usage
            else {}
        )
        return AgentResponse(messages=[out_msg], usage=usage)
