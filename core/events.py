from dataclasses import dataclass
from typing import List, Any
from models import Message, ToolCall

class Event:
    pass

@dataclass
class TurnStartEvent(Event):
    turn: int

@dataclass
class LLMRequestEvent(Event):
    messages: List[Message]

@dataclass
class LLMResponseEvent(Event):
    message: Message

@dataclass
class ToolExecutionEvent(Event):
    tool_call: ToolCall

@dataclass
class ToolResultEvent(Event):
    tool_call_id: str
    result: str
    is_error: bool

class EventBus:
    def __init__(self):
        self.listeners = []

    def subscribe(self, listener):
        self.listeners.append(listener)

    def emit(self, event: Event):
        for listener in self.listeners:
            listener(event)
