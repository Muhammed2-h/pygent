import argparse
import os
from pathlib import Path
from config import load_config, setup_data_directory
from providers.factory import create_provider
from tools import ToolRegistry
from agent import Agent
from memory.storage import MemoryStore
from memory.privacy import PrivacyFilter
from memory.service import MemoryService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Run diagnostics")
    parser.add_argument("--memory-demo", action="store_true", help="Demo memory")
    args = parser.parse_args()

    config = load_config()
    setup_data_directory(config)
    
    base_dir = Path(config.data_dir)
    db_path = base_dir / "memory" / "memory.db"
    skills_dir = base_dir / "skills"

    if args.check:
        print("Checking Configuration...")
        if config.openai_api_key:
            print("OpenAI Key: Present")
        print("Checking Database...")
        store = MemoryStore(str(db_path), skills_dir=skills_dir)
        store.close()
        print(f"Database OK at {db_path}")
        return

    if args.memory_demo:
        store = MemoryStore(str(db_path), skills_dir=skills_dir)
        svc = MemoryService(store, PrivacyFilter())
        svc.add("The user loves Python and SQLite.")
        print(svc.get_context_for("What does the user love?"))
        store.close()
        return

    try:
        provider = create_provider(config)
    except ValueError as e:
        print(f"Error: {e}")
        return
    tools = ToolRegistry()
    memory_store = MemoryStore(str(db_path), skills_dir=skills_dir)
    memory_svc = MemoryService(memory_store, PrivacyFilter())

    agent = Agent(provider, tools, config.default_model, config.max_agent_steps, memory_service=memory_svc)

    print("Pygent started. Type /quit to exit.")
    try:
        while True:
            try:
                user_in = input("> ")
            except (EOFError, KeyboardInterrupt):
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


if __name__ == "__main__":
    main()
