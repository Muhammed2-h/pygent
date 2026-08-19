from typing import List
from models import Message
from providers.base import BaseProvider
from tools import ToolRegistry


class Agent:
    def __init__(self, provider: BaseProvider, tools: ToolRegistry, model: str, max_steps: int = 8):
        self.provider = provider
        self.tools = tools
        self.model = model
        self.max_steps = max_steps

    def run(self, system_prompt: str, user_input: str) -> List[Message]:
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_input),
        ]

        for step in range(self.max_steps):
            response = self.provider.complete(
                messages, model=self.model, tools=self.tools.get_tool_schemas()
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

            if step == self.max_steps - 1:
                messages.append(Message(role="system", content="Max steps reached. Please summarize the final result without calling any more tools."))
                final_response = self.provider.complete(messages, model=self.model, tools=[])
                messages.append(final_response.messages[0])

        return messages
