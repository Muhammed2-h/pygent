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
        self.state.messages = self.context.build_context(system_prompt, user_input)
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
                
            cp = self.state.checkpoint.get_checkpoint()
            messages_to_send = self.state.messages.copy()
            if cp:
                messages_to_send.append(Message(role="system", content=cp))
                
            self.events.emit(LLMRequestEvent(messages=messages_to_send))
            
            response = self.provider.complete(
                messages_to_send, model=current_model, tools=self.tools.get_tool_schemas()
            )
            new_msg = response.messages[0]
            
            self.events.emit(LLMResponseEvent(message=new_msg))
            
            self.state.messages.append(new_msg)
            self.state.new_messages.append(new_msg)
            
            if not new_msg.tool_calls:
                break
                
            current_tool_calls = new_msg.tool_calls
            current_errors = []
            current_results = []
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
                    
                current_results.append(result)
                self.events.emit(ToolResultEvent(tool_call_id=tc.id, result=result, is_error=is_error))
                
                tool_msg = Message(role="tool", content=result, tool_call_id=tc.id)
                self.state.messages.append(tool_msg)
                self.state.new_messages.append(tool_msg)
                executed_tool_calls.append(tc)

            if len(executed_tool_calls) < len(new_msg.tool_calls):
                new_msg.tool_calls = executed_tool_calls

            page_id = self._get_page_context()
            self.state.loop_guard.add_step(
                tool_calls=executed_tool_calls,
                errors=current_errors,
                results=current_results,
                page_id=page_id
            )
            
            rep_count = self.state.loop_guard.get_repetition_count()
            if rep_count == 2:
                warning_msg = Message(
                    role="system",
                    content="Warning: You are repeating the exact same tool calls and getting the same results. Please consider a different approach."
                )
                self.state.messages.append(warning_msg)
                self.state.new_messages.append(warning_msg)
            elif rep_count == 3:
                self.state.strategy = "fallback"
            elif rep_count >= 4:
                from tools.human import tool_ask_user
                try:
                    ans = tool_ask_user(
                        question="I am stuck in an infinite loop repeating the same actions. How should I proceed?",
                        choices=["continue", "abort"],
                        risk="high",
                        reason="Infinite loop detected."
                    )
                    if ans.lower() == "abort":
                        self._terminate_loop_with_summary("User aborted due to infinite loop.")
                        break
                    else:
                        user_msg = Message(role="user", content=f"User responded to loop guard: {ans}")
                        self.state.messages.append(user_msg)
                        self.state.new_messages.append(user_msg)
                except Exception as e:
                    self._terminate_loop_with_summary("Infinite loop detected and ask_user failed.")
                    break

            # check limit after step
            limit_reason = None
            if self.state.turns >= self.state.max_turns - 1:
                limit_reason = "Max steps reached."
            elif self.state.tool_calls_count >= self.state.max_tool_calls:
                limit_reason = "Max tool calls reached."
            elif self.state.get_wall_time() >= self.state.max_wall_time:
                limit_reason = "Max wall time reached."

            if limit_reason:
                self._terminate_loop_with_summary(limit_reason)
                break

            self.state.turns += 1

        return self.state.new_messages

    def _terminate_loop_with_summary(self, reason: str):
        limit_msg = Message(role="system", content=f"{reason} Please summarize the final result without calling any more tools.")
        self.state.messages.append(limit_msg)
        self.state.new_messages.append(limit_msg)
        
        final_messages_to_send = self.state.messages.copy()
        final_cp = self.state.checkpoint.get_checkpoint()
        if final_cp:
            final_messages_to_send.append(Message(role="system", content=final_cp))
            
        final_response = self.provider.complete(final_messages_to_send, model=self.model, tools=[])
        final_msg = final_response.messages[0]
        self.state.messages.append(final_msg)
        self.state.new_messages.append(final_msg)

    def _get_page_context(self) -> str:
        try:
            import sys
            if "tools.browser" in sys.modules:
                browser = sys.modules["tools.browser"]
                if hasattr(browser, "_session_manager") and browser._session_manager:
                    active_tab = browser._session_manager.active_tab_id
                    if active_tab:
                        sessions = browser._session_manager.find_session(tab_id=active_tab)
                        if sessions:
                            return sessions[0].url
        except Exception:
            pass
        return ""
