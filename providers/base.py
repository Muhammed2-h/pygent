from abc import ABC, abstractmethod

from models import AgentResponse, Message


class BaseProvider(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        model: str,
        tools: list[dict] | None = None,
    ) -> AgentResponse:
        pass
