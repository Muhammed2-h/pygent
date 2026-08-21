# Pygent

A production-quality, browser-control Python AI agent with persistent memory — built with boring, readable, maintainable Python.

No LangChain. No CrewAI. No AutoGen. Just clean code.

## Features

- **Browser Control** — Autonomous web interaction driven by OpenAI
- **Persistent Memory** — SQLite FTS5 full-text search for long-term observation storage across sessions
- **Privacy Scrubbing** — Automatically redacts API keys and secrets before storing to memory
- **Tool Use** — Safe built-in tools (calculator, time, environment info) with an extensible registry
- **Conversational Context** — Maintains conversation history within a session and augments prompts with relevant memory
- **Minimal Dependencies** — Built primarily on `openai`, `pydantic`, and `python-dotenv`

## Architecture

```
main.py              → CLI entry point, REPL loop, diagnostics
├── config.py        → Pydantic config from .env
├── models.py        → Normalized Message, ToolCall, AgentResponse
├── agent.py         → Core agent loop (prompt → tool calls → results → repeat)
├── tools.py         → ToolRegistry + safe built-in tools
├── providers/
│   ├── base.py      → Abstract BaseProvider interface
│   └── openai_provider.py → OpenAI Chat Completions adapter
└── memory/
    ├── storage.py   → SQLite FTS5 MemoryStore
    ├── privacy.py   → PrivacyFilter (regex-based secret scrubbing)
    └── service.py   → MemoryService (orchestrates storage + privacy)
```

## Requirements

- **Python 3.11+**
- An OpenAI API key

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Muhammed2-h/pygent.git
cd pygent
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and add your API key(s):

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
OPENAI_API_KEY=sk-your-key-here
DEFAULT_MODEL=gpt-4o
MAX_AGENT_STEPS=8
```

> **Important:** Never commit your `.env` file. It is already in `.gitignore`.

### 5. Verify Installation

Run the built-in diagnostics to confirm everything is configured:

```bash
python main.py --check
```

Expected output:

```
Checking Configuration...
OpenAI Key: Present
Checking Database...
Database OK at ~/.agent_memory.db
```

## Usage

### Interactive Chat

Start the agent in interactive mode:

```bash
python main.py
```

```
Pygent started. Type /quit to exit.
> What time is it?
AI: The current time is 2026-08-19T22:00:00.
> Calculate 42 * 17
AI: 42 * 17 = 714.
> /quit
```

### Memory Demo

Test the persistent memory system:

```bash
python main.py --memory-demo
```

This stores a test observation and retrieves it via full-text search.

### Diagnostics

Check your configuration and database:

```bash
python main.py --check
```

## Built-in Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_time` | Returns current ISO timestamp | "What time is it?" |
| `calculate` | Safe arithmetic evaluation (no `eval`) | "What is 123 * 456?" |
| `env_info` | Reads an environment variable | "What is the HOME variable?" |

### Adding Custom Tools

Register new tools in [`tools.py`](tools.py):

```python
# 1. Define the function
def tool_weather(city: str) -> str:
    # Your implementation here
    return f"Weather in {city}: Sunny, 25°C"

# 2. Register in ToolRegistry.__init__
self.tools["weather"] = tool_weather

# 3. Add schema in get_tool_schemas()
{
    "type": "function",
    "function": {
        "name": "weather",
        "description": "Get weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}
```

## Memory System

Pygent uses **SQLite FTS5** for persistent, provider-independent memory:

- **Observations** are stored automatically after each user turn
- **Privacy filter** scrubs API keys (OpenAI `sk-*`) before storage
- **Full-text search** retrieves relevant context and injects it into the system prompt
- **Supersede support** allows marking old memories as outdated
- Database stored at `~/.agent_memory.db` (outside the repo)

## Adding a New Provider

Implement the [`BaseProvider`](providers/base.py) interface:

```python
from providers.base import BaseProvider
from models import AgentResponse, Message

class MyProvider(BaseProvider):
    def complete(self, messages, model, tools=None) -> AgentResponse:
        # Translate messages to your API format
        # Call your API
        # Translate response back to AgentResponse
        ...
```

## Running Tests

```bash
pytest -v
```

All 34 tests cover:
- Configuration loading and edge cases
- Normalized model creation
- Provider message translation and tool call parsing
- Tool registry execution and safety
- Agent loop (simple, tool calls, multi-tool, max steps)
- CLI modes (check, memory-demo, interactive, missing keys, EOF)
- Memory storage, FTS search, privacy scrubbing, service orchestration

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `DEFAULT_MODEL` | `gpt-4o` | Which model to use |
| `MAX_AGENT_STEPS` | `8` | Max tool-use loop iterations per turn |

## License

MIT — see [LICENSE](LICENSE) for details.
