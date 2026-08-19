from abc import ABC, abstractmethod
from typing import List, Optional
from models import Message, AgentResponse


class BaseProvider(ABC):
    @abstractmethod
    def complete(
        self,
        messages: List[Message],
        model: str,
        tools: Optional[List[dict]] = None,
    ) -> AgentResponse:
        pass
