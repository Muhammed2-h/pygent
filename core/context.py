import json
from typing import List, Optional, Any
from models import Message

def truncate_dict_strings(d: Any, max_len: int = 2000) -> Any:
    if isinstance(d, dict):
        return {k: truncate_dict_strings(v, max_len) for k, v in d.items()}
    elif isinstance(d, list):
        if len(d) > 20:
            d = d[:20] + ["... [truncated list]"]
        return [truncate_dict_strings(v, max_len) for v in d]
    elif isinstance(d, str):
        if len(d) > max_len:
            return d[:max_len] + "... [truncated]"
    return d
class ContextBuilder:
    def __init__(
        self,
        prompt_builder=None,
        environment_manager=None,
        memory_service=None
    ):
        self.messages: List[Message] = []
        self.prompt_builder = prompt_builder
        self.environment_manager = environment_manager
        self.memory_service = memory_service
        
    def build_context(
        self, 
        system_prompt: str, 
        user_input: str,
        checkpoint: Optional[str] = None,
        history: Optional[List[Message]] = None,
        max_history: int = 10,
        browser_state: Optional[Any] = None
    ) -> List[Message]:
        """
        Builds the context dynamically according to:
        1. system rules
        2. environment facts
        3. top skills
        4. working checkpoint
        5. recent browser state
        6. recent conversation
        7. recent tool results
        """
        parts = []
        
        # 1. System rules
        if self.prompt_builder:
            rules = self.prompt_builder.build()
            parts.append(system_prompt + "\n\n" + rules if rules else system_prompt)
        else:
            parts.append(system_prompt)
            
        # 2. Environment facts
        if self.environment_manager and hasattr(self.environment_manager, 'check_capabilities'):
            caps = self.environment_manager.check_capabilities()
            fact_texts = []
            for name, cap in caps.items():
                if cap.available:
                    version = f" ({cap.version})" if getattr(cap, 'version', None) else ""
                    fact_texts.append(f"- {name}{version} is available")
            
            if fact_texts:
                parts.append("Environment Facts:\n" + "\n".join(fact_texts))
                
        # 3. Top skills
        if self.memory_service and hasattr(self.memory_service, 'get_relevant_skills'):
            skills = self.memory_service.get_relevant_skills(user_input)
            skill_texts = []
            for s in skills[:3]:
                if s.get('content'):
                    content = s.get('content')
                    if len(content) > 1000:
                        content = content[:1000] + "... [truncated]"
                    text = f"- {s.get('name', 'skill')}: {content}"
                    prereqs = s.get('prerequisites')
                    if prereqs:
                        text += f"\n  Prerequisites: {prereqs}"
                    skill_texts.append(text)
            if skill_texts:
                parts.append("Top Skills:\n" + "\n".join(skill_texts))
                
        # 4. Working checkpoint
        if checkpoint:
            parts.append(f"Working Checkpoint:\n{checkpoint}")
            
        # 5. Recent browser state
        if browser_state:
            state_dict = {}
            if hasattr(browser_state, 'model_dump'):
                state_dict = browser_state.model_dump()
            elif hasattr(browser_state, 'dict'):
                state_dict = browser_state.dict()
            elif isinstance(browser_state, dict):
                state_dict = browser_state
            
            truncated_state = truncate_dict_strings(state_dict)
            parts.append(f"Recent Browser State:\n{json.dumps(truncated_state, indent=2)}")

        final_system_prompt = "\n\n".join(parts).strip()
        system_msg = Message(role="system", content=final_system_prompt)
        
        context = [system_msg]
        
        # 6. Recent conversation & 7. Recent tool results
        if history:
            if max_history <= 0:
                pass # append nothing
            else:
                context.extend(history[-max_history:])
            
        if user_input:
            context.append(Message(role="user", content=user_input))
            
        return context

    # Keep build() for backward compatibility with older tests/usages
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
