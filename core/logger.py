import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

SENSITIVE_KEYS = {
    "api_key", "apikey", "password", "pwd", "secret", "token", "auth",
    "authorization", "cookie", "cookies", "session", "credit_card",
    "private", "private_form_value"
}

SECRET_REGEXES = [
    re.compile(r"Bearer\s+[\w\-.]+"),
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),
]

def _redact_string(val: str) -> str:
    for regex in SECRET_REGEXES:
        val = regex.sub("***REDACTED***", val)
    return val

def redact(data: Any) -> Any:
    if isinstance(data, dict):
        redacted_dict = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(sensitive in k_lower for sensitive in SENSITIVE_KEYS):
                redacted_dict[k] = "***REDACTED***"
            else:
                redacted_dict[k] = redact(v)
        return redacted_dict
    elif isinstance(data, list) or isinstance(data, tuple):
        return [redact(item) for item in data]
    elif isinstance(data, str):
        return _redact_string(data)
    else:
        return data

class JSONLFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "task_id": getattr(record, "task_id", None),
            "turn": getattr(record, "turn", None),
            "tool": getattr(record, "tool", None),
            "status": getattr(record, "status", None),
            "duration": getattr(record, "duration", None),
            "error": getattr(record, "error", None)
        }
        
        redacted_obj = redact(log_obj)
        return json.dumps(redacted_obj)

def get_logger(name: str) -> logging.Logger:
    data_dir_raw = os.getenv("PYGENT_DATA_DIR", "~/.pygent")
    log_dir = Path(data_dir_raw).expanduser() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = name.split(".")[-1] if "." in name else name
    log_file = log_dir / f"{base_name}.jsonl"
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    if not logger.handlers:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(JSONLFormatter())
        logger.addHandler(handler)
        
    return logger

agent_logger = get_logger("agent")
browser_logger = get_logger("browser")
tools_logger = get_logger("tools")
memory_logger = get_logger("memory")
