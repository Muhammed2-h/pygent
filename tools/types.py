from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class Tool:
    name: str
    description: str
    schema: dict[str, Any] | None
    executor: Callable[..., Any]
    risk_level: Literal["safe", "warn", "danger"]
    category: str
