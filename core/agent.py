from typing import List
from models import Message
from providers.base import BaseProvider
from tools import ToolRegistry
from core.state import AgentState
from core.context import ContextBuilder
from core.events import EventBus
from core.loop import AgentLoop

class Agent:
    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolRegistry,
        model: str,
        max_steps: int = 8,
        max_tool_calls: int = 100,
        max_wall_time: float = 3600.0,
    ):
        self.provider = provider
        self.tools = tools
        self.model = model
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.max_wall_time = max_wall_time
        
        self.context = ContextBuilder()
        self.events = EventBus()
        
    @property
    def messages(self) -> List[Message]:
        return self.context.messages
        
    @messages.setter
    def messages(self, val: List[Message]):
        self.context.messages = val

    def run(self, system_prompt: str, user_input: str) -> List[Message]:
        from prompts.builder import PromptBuilder
        builder = PromptBuilder()
        built_prompt = builder.build(tools=self.tools)
        
        final_system_prompt = system_prompt
        if built_prompt:
            final_system_prompt += "\n\n" + built_prompt
            
        # Reset state for each run if needed, but for now just create a new state
        state = AgentState(
            max_turns=self.max_steps,
            max_tool_calls=self.max_tool_calls,
            max_wall_time=self.max_wall_time,
        )
        loop = AgentLoop(
            provider=self.provider, 
            tools=self.tools, 
            model=self.model, 
            context=self.context, 
            state=state, 
            events=self.events
        )
        return loop.run(system_prompt, user_input)
