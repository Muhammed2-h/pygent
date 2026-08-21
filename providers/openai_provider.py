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


        while True:
            max_retries = 3
            retry_delay = 1
            success = False
            caught_e = None
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(**kwargs)
                    success = True
                    break
                except (openai.RateLimitError, openai.APIConnectionError) as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(retry_delay)
                    retry_delay *= 2
                except openai.BadRequestError as e:
                    if "context_length_exceeded" in str(e) or (hasattr(e, "code") and e.code == "context_length_exceeded"):
                        caught_e = e
                        success = False
                        break
                    else:
                        raise

            if success:
                break
                
            if caught_e:
                removed = False
                first_non_system_idx = -1
                for i, msg in enumerate(kwargs["messages"]):
                    if msg["role"] != "system":
                        first_non_system_idx = i
                        break
                
                if first_non_system_idx != -1:
                    msg_to_drop = kwargs["messages"][first_non_system_idx]
                    dropped_tool_call_ids = set()
                    if "tool_calls" in msg_to_drop and msg_to_drop["tool_calls"]:
                        for tc in msg_to_drop["tool_calls"]:
                            dropped_tool_call_ids.add(tc["id"])
                    
                    kwargs["messages"].pop(first_non_system_idx)
                    removed = True
                    
                    if dropped_tool_call_ids:
                        new_messages = []
                        for msg in kwargs["messages"]:
                            if msg["role"] == "tool" and msg.get("tool_call_id") in dropped_tool_call_ids:
                                continue
                            new_messages.append(msg)
                        kwargs["messages"] = new_messages
                        
                if not removed:
                    raise caught_e
            else:
                # Should not reach here because network errors raise on exhaustion
                raise RuntimeError("Failed to get response")

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
