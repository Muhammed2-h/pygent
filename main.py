import argparse
import os
from config import load_config
from providers.openai_provider import OpenAIProvider
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
    db_path = os.path.expanduser("~/.agent_memory.db")

    if args.check:
        print("Checking Configuration...")
        if config.openai_api_key:
            print("OpenAI Key: Present")
        print("Checking Database...")
        MemoryStore(db_path)
        print(f"Database OK at {db_path}")
        return

    if args.memory_demo:
        store = MemoryStore(db_path)
        svc = MemoryService(store, PrivacyFilter())
        svc.add("The user loves Python and SQLite.")
        print(svc.get_context_for("What does the user love?"))
        return

    if not config.openai_api_key:
        print("Error: OPENAI_API_KEY not found in .env")
        return

    provider = OpenAIProvider(config.openai_api_key)
    tools = ToolRegistry()
    memory_store = MemoryStore(db_path)
    memory_svc = MemoryService(memory_store, PrivacyFilter())

    agent = Agent(provider, tools, config.max_agent_steps)

    print("Agent started. Type /quit to exit.")
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


if __name__ == "__main__":
    main()
