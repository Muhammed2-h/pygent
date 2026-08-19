from typing import List, Optional
from models import Message, ToolCall
from core.state import AgentState
from core.context import ContextBuilder
from core.events import EventBus, TurnStartEvent, LLMRequestEvent, LLMResponseEvent, ToolExecutionEvent, ToolResultEvent
from providers.base import BaseProvider
from tools import ToolRegistry

class AgentLoop:
    def __init__(self, provider: BaseProvider, tools: ToolRegistry, model: str, context: ContextBuilder, state: AgentState, events: EventBus):
        self.provider = provider
        self.tools = tools
        self.model = model
        self.context = context
        self.state = state
        self.events = events

    def run(self, system_prompt: str, user_input: str) -> List[Message]:
        self.state.messages = self.context.build(system_prompt, user_input)
        self.state.new_messages = []
        
        while not self.state.is_finished():
            self.events.emit(TurnStartEvent(turn=self.state.turns))
            
            current_model = self.model
            
            # strategy switching fallback
            if self.state.strategy == "fallback":
                warning_msg = Message(
                    role="system",
                    content="You are repeating the exact same tool calls or getting the exact same errors. Please rethink your strategy."
                )
                self.state.messages.append(warning_msg)
                self.state.new_messages.append(warning_msg)
                self.state.strategy = "default"
                
            self.events.emit(LLMRequestEvent(messages=self.state.messages))
            
            response = self.provider.complete(
                self.state.messages, model=current_model, tools=self.tools.get_tool_schemas()
            )
            new_msg = response.messages[0]
            
            self.events.emit(LLMResponseEvent(message=new_msg))
            
            self.state.messages.append(new_msg)
            self.state.new_messages.append(new_msg)
            
            if not new_msg.tool_calls:
                break
                
            current_tool_calls = new_msg.tool_calls
            if self._is_same_action(current_tool_calls, self.state.last_tool_calls):
                self.state.strategy = "fallback"
                
            self.state.last_tool_calls = current_tool_calls
            current_errors = []
            executed_tool_calls = []

            for tc in new_msg.tool_calls:
                if self.state.tool_calls_count >= self.state.max_tool_calls:
                    break
                    
                self.events.emit(ToolExecutionEvent(tool_call=tc))
                self.state.tool_calls_count += 1
                
                try:
                    result = self.tools.execute(tc.name, tc.arguments)
                    is_error = False
                except Exception as e:
                    result = str(e)
                    is_error = True
                    current_errors.append(result)
                    
                self.events.emit(ToolResultEvent(tool_call_id=tc.id, result=result, is_error=is_error))
                
                tool_msg = Message(role="tool", content=result, tool_call_id=tc.id)
                self.state.messages.append(tool_msg)
                self.state.new_messages.append(tool_msg)
                executed_tool_calls.append(tc)

            if len(executed_tool_calls) < len(new_msg.tool_calls):
                new_msg.tool_calls = executed_tool_calls

            if self._is_same_error(current_errors, self.state.last_errors) and current_errors:
                self.state.strategy = "fallback"
                
            self.state.last_errors = current_errors

            # check limit after step
            limit_reason = None
            if self.state.turns >= self.state.max_turns - 1:
                limit_reason = "Max steps reached."
            elif self.state.tool_calls_count >= self.state.max_tool_calls:
                limit_reason = "Max tool calls reached."
            elif self.state.get_wall_time() >= self.state.max_wall_time:
                limit_reason = "Max wall time reached."

            if limit_reason:
                limit_msg = Message(role="system", content=f"{limit_reason} Please summarize the final result without calling any more tools.")
                self.state.messages.append(limit_msg)
                self.state.new_messages.append(limit_msg)
                
                final_response = self.provider.complete(self.state.messages, model=current_model, tools=[])
                final_msg = final_response.messages[0]
                self.state.messages.append(final_msg)
                self.state.new_messages.append(final_msg)
                break

            self.state.turns += 1

        return self.state.new_messages

    def _is_same_action(self, current: List[ToolCall], last: List[ToolCall]) -> bool:
        if not current or not last:
            return False
        if len(current) != len(last):
            return False
        for c, l in zip(current, last):
            if c.name != l.name or c.arguments != l.arguments:
                return False
        return True
        
    def _is_same_error(self, current: List[str], last: List[str]) -> bool:
        if not current or not last:
            return False
        return current == last
