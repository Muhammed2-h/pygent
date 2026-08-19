from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal, Optional

@dataclass
class Tool:
    name: str
    description: str
    schema: Optional[Dict[str, Any]]
    executor: Callable[..., Any]
    risk_level: Literal["safe", "warn", "danger"]
    category: str
