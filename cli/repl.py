from core.agent import Agent
from core.memory_service import MemoryService

from config import load_config
from memory.privacy import PrivacyFilter
from memory.storage import MemoryStore
from providers.factory import create_provider
from tools import ToolRegistry


def start_repl(db_path: str, skills_dir: str):
    config = load_config()
    try:
        provider = create_provider(config)
    except ValueError as e:
        print(f"Error: {e}")
        return

    tools = ToolRegistry()
    memory_store = MemoryStore(db_path, skills_dir=skills_dir)
    memory_svc = MemoryService(memory_store, PrivacyFilter())

    agent = Agent(provider, tools, config.default_model, config.max_agent_steps, memory_service=memory_svc)

    print("Pygent started. Type /quit to exit.")
    try:
        while True:
            try:
                user_in = input("> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if user_in.strip() == "/quit":
                break

            context = memory_svc.get_context_for(user_in)
            sys_prompt = "You are a helpful AI."
            if context:
                sys_prompt += "\n" + context

            messages = agent.run(sys_prompt, user_in)
            for msg in messages:
                if msg.role == "assistant" and msg.content:
                    print(f"AI: {msg.content}")

            memory_svc.add(f"User observation: {user_in}")
    finally:
        memory_store.close()
