import os
from pathlib import Path
from tools.registry import tool

def normalize_and_check_path(filepath: str, allowed_root: str = None) -> Path:
    p = Path(filepath).resolve()
    root = allowed_root or os.getenv("AGENT_WORKSPACE", None)
    if root:
        root_p = Path(root).resolve()
        # In Python 3.9+, is_relative_to is available
        if not p.is_relative_to(root_p):
            raise ValueError(f"Access denied: Path {filepath} is outside allowed root {root_p}")
    return p

@tool(
    name="file_read",
    description="Read the contents of a file.",
    category="filesystem",
    risk_level="safe"
)
def file_read(filepath: str) -> str:
    try:
        path = normalize_and_check_path(filepath)
    except ValueError as e:
        return str(e)

    if not path.exists():
        return f"Error: File {filepath} does not exist."
    if not path.is_file():
        return f"Error: Path {filepath} is not a file."
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file {filepath}: {e}"

@tool(
    name="file_write",
    description="Write content to a file, completely overwriting it if it exists.",
    category="filesystem",
    risk_level="warn"
)
def file_write(filepath: str, content: str) -> str:
    try:
        path = normalize_and_check_path(filepath)
    except ValueError as e:
        return str(e)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {filepath}."
    except Exception as e:
        return f"Error writing file {filepath}: {e}"

@tool(
    name="file_patch",
    description="Patch a file by replacing a unique occurrence of 'find' with 'replace'. Prefer small patches.",
    category="filesystem",
    risk_level="warn"
)
def file_patch(filepath: str, find: str, replace: str) -> str:
    try:
        path = normalize_and_check_path(filepath)
    except ValueError as e:
        return str(e)

    if not path.exists():
        return f"Error: File {filepath} does not exist."
    if not path.is_file():
        return f"Error: Path {filepath} is not a file."
    
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file {filepath}: {e}"

    if find not in content:
        return "Error: The exact text to find was not found in the file."
    
    occurrences = content.count(find)
    if occurrences > 1:
        return f"Error: The text to find occurs {occurrences} times in the file. Unique replacement required. Please provide a more specific 'find' block."
    
    new_content = content.replace(find, replace, 1)
    
    try:
        path.write_text(new_content, encoding="utf-8")
        return f"Successfully patched {filepath}."
    except Exception as e:
        return f"Error writing patched file {filepath}: {e}"
