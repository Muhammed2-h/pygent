import json
from typing import List, Optional, Any
from models import Message

class ContextBuilder:
    def __init__(
        self,
        prompt_builder=None,
        environment_manager=None,
        memory_service=None,
        browser_state=None
    ):
        self.messages: List[Message] = []
        self.prompt_builder = prompt_builder
        self.environment_manager = environment_manager
        self.memory_service = memory_service
        self.browser_state = browser_state
        
    def build_context(
        self, 
        system_prompt: str, 
        user_input: str,
        checkpoint: Optional[str] = None,
        history: Optional[List[Message]] = None,
        max_history: int = 10
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
        if self.memory_service and hasattr(self.memory_service, 'get_environment_facts'):
            facts = self.memory_service.get_environment_facts(user_input)
            fact_texts = [f"- {f.get('content')}" for f in facts[:5] if f.get('content')]
            if fact_texts:
                parts.append("Environment Facts:\n" + "\n".join(fact_texts))
                
        # 3. Top skills
        if self.memory_service and hasattr(self.memory_service, 'get_relevant_skills'):
            skills = self.memory_service.get_relevant_skills(user_input)
            skill_texts = [f"- {s.get('name', 'skill')}: {s.get('content')}" for s in skills[:3] if s.get('content')]
            if skill_texts:
                parts.append("Top Skills:\n" + "\n".join(skill_texts))
                
        # 4. Working checkpoint
        if checkpoint:
            parts.append(f"Working Checkpoint:\n{checkpoint}")
            
        # 5. Recent browser state
        if self.browser_state:
            state_dict = {}
            if hasattr(self.browser_state, 'model_dump'):
                state_dict = self.browser_state.model_dump()
            elif hasattr(self.browser_state, 'dict'):
                state_dict = self.browser_state.dict()
            elif isinstance(self.browser_state, dict):
                state_dict = self.browser_state
            
            parts.append(f"Recent Browser State:\n{json.dumps(state_dict, indent=2)}")

        final_system_prompt = "\n\n".join(parts).strip()
        system_msg = Message(role="system", content=final_system_prompt)
        
        context = [system_msg]
        
        # 6. Recent conversation & 7. Recent tool results
        # We group these together by taking the recent message history.
        if history:
            # slice the last N messages
            context.extend(history[-max_history:] if max_history > 0 else history)
            
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
