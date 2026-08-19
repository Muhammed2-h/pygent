from typing import List
from models import Message
from providers.base import BaseProvider
from tools import ToolRegistry


class Agent:
    def __init__(self, provider: BaseProvider, tools: ToolRegistry, max_steps: int = 8):
        self.provider = provider
        self.tools = tools
        self.max_steps = max_steps

    def run(self, system_prompt: str, user_input: str) -> List[Message]:
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_input),
        ]

        for _ in range(self.max_steps):
            response = self.provider.complete(
                messages, model="default", tools=self.tools.get_tool_schemas()
            )
            new_msg = response.messages[0]
            messages.append(new_msg)

            if not new_msg.tool_calls:
                break

            for tc in new_msg.tool_calls:
                result = self.tools.execute(tc.name, tc.arguments)
                messages.append(
                    Message(role="tool", content=result, tool_call_id=tc.id)
                )

        return messages
