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
        self.messages: List[Message] = []

    def run(self, system_prompt: str, user_input: str) -> List[Message]:
        if not self.messages:
            self.messages.append(Message(role="system", content=system_prompt))
        else:
            if self.messages[0].role == "system":
                self.messages[0].content = system_prompt
            else:
                self.messages.insert(0, Message(role="system", content=system_prompt))
                
        self.messages.append(Message(role="user", content=user_input))
        new_messages = []

        for step in range(self.max_steps):
            response = self.provider.complete(
                self.messages, model=self.model, tools=self.tools.get_tool_schemas()
            )
            new_msg = response.messages[0]
            self.messages.append(new_msg)
            new_messages.append(new_msg)

            if not new_msg.tool_calls:
                break

            for tc in new_msg.tool_calls:
                result = self.tools.execute(tc.name, tc.arguments)
                tool_msg = Message(role="tool", content=result, tool_call_id=tc.id)
                self.messages.append(tool_msg)
                new_messages.append(tool_msg)

            if step == self.max_steps - 1:
                limit_msg = Message(role="system", content="Max steps reached. Please summarize the final result without calling any more tools.")
                self.messages.append(limit_msg)
                new_messages.append(limit_msg)
                final_response = self.provider.complete(self.messages, model=self.model, tools=[])
                final_msg = final_response.messages[0]
                self.messages.append(final_msg)
                new_messages.append(final_msg)

        return new_messages
