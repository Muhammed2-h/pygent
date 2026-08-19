from enum import Enum

class MemoryType(str, Enum):
    FACT = "fact"
    ENVIRONMENT = "environment"
    PREFERENCE = "preference"
    LESSON = "lesson"
    SKILL = "skill"
    SESSION = "session"
    SYSTEM = "system"
    INDEX = "index"

class MemoryLayer(int, Enum):
    L0 = 0  # system rules
    L1 = 1  # memory index
    L2 = 2  # environment facts
    L3 = 3  # skills and SOPs
    L4 = 4  # session archives
