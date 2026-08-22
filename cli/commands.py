import argparse
from pathlib import Path

from core.memory_service import MemoryService

from config import load_config, setup_data_directory
from memory.privacy import PrivacyFilter
from memory.storage import MemoryStore

from .repl import start_repl


def handle_check(db_path: str, skills_dir: str, config):
    print("Checking Configuration...")
    print(f"Provider: {config.provider}")
    print(f"Model: {config.default_model}")
    print(f"Base URL: {config.base_url or 'Default'}")
    if config.api_key:
        print("API Key: Present")
    else:
        print("API Key: MISSING")
    print("Checking Database...")
    store = MemoryStore(db_path, skills_dir=skills_dir)
    store.close()
    print(f"Database OK at {db_path}")

def handle_memory_demo(db_path: str, skills_dir: str):
    store = MemoryStore(db_path, skills_dir=skills_dir)
    svc = MemoryService(store, PrivacyFilter())
    svc.add("The user loves Python and SQLite.")
    print(svc.get_context_for("What does the user love?"))
    store.close()

def execute(args_list=None):
    parser = argparse.ArgumentParser(description="Pygent - AI Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # chat
    subparsers.add_parser("chat", help="Start the interactive chat REPL")
    
    # browser
    browser_parser = subparsers.add_parser("browser", help="Browser automation tools")
    browser_parser.add_argument("--managed", action="store_true", help="Start a managed browser with a dedicated profile")
    browser_subparsers = browser_parser.add_subparsers(dest="browser_command")
    browser_subparsers.add_parser("setup", help="Setup browser extension")
    
    # check
    subparsers.add_parser("check", help="Run diagnostics")
    
    # memory
    memory_parser = subparsers.add_parser("memory", help="Memory management")
    memory_parser.add_argument("--demo", action="store_true", help="Run memory demo")
    
    # skills
    subparsers.add_parser("skills", help="Skills management")
    
    # environment
    subparsers.add_parser("environment", help="Environment management")
    
    args = parser.parse_args(args_list)
    
    config = load_config()
    setup_data_directory(config)
    
    base_dir = Path(config.data_dir)
    db_path = str(base_dir / "memory" / "memory.db")
    skills_dir = str(base_dir / "skills")

    if args.command == "check":
        handle_check(db_path, skills_dir, config)
    elif args.command == "memory":
        if getattr(args, "demo", False):
            handle_memory_demo(db_path, skills_dir)
        else:
            print("Memory command executed.")
    elif args.command == "chat" or args.command is None:
        start_repl(db_path, skills_dir)
    elif args.command == "browser":
        if getattr(args, "browser_command", None) == "setup":
            from .browser_setup import handle_browser_setup
            handle_browser_setup()
        else:
            from .browser_repl import handle_browser
            handle_browser(db_path, skills_dir, managed=getattr(args, "managed", False))
    elif args.command == "skills":
        print("Skills command executed.")
    elif args.command == "environment":
        print("Environment command executed.")
