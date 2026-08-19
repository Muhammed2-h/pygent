from typing import List
from models import Message

class ContextBuilder:
    def __init__(self):
        self.messages: List[Message] = []

    def build(self, system_prompt: str, user_input: str) -> List[Message]:
        if not self.messages:
            self.messages.append(Message(role="system", content=system_prompt))
        else:
            if self.messages[0].role == "system":
                self.messages[0].content = system_prompt
            else:
                self.messages.insert(0, Message(role="system", content=system_prompt))
                
        self.messages.append(Message(role="user", content=user_input))
        return self.messages
