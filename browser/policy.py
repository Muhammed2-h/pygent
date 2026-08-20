from enum import Enum
import re
import json

class RiskLevel(str, Enum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    DANGEROUS = "dangerous"
    
    @property
    def _order(self):
        return {"safe": 0, "sensitive": 1, "dangerous": 2}[self.value]

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self._order < other._order
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self._order <= other._order
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self._order > other._order
        return NotImplemented

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self._order >= other._order
        return NotImplemented

class BrowserPolicy:
    def __init__(self):
        self.dangerous_keywords = ["purchase", "buy", "pay", "transfer", "delete", "remove", "password", "credential"]
        self.sensitive_keywords = ["upload", "message", "send", "download", "submit", "post"]
        
        # Compile word-boundary regexes
        self.dangerous_regex = re.compile(r'\b(?:' + '|'.join(map(re.escape, self.dangerous_keywords)) + r')\b', re.IGNORECASE)
        self.sensitive_regex = re.compile(r'\b(?:' + '|'.join(map(re.escape, self.sensitive_keywords)) + r')\b', re.IGNORECASE)

    def evaluate_js(self, script: str) -> RiskLevel:
        if self.dangerous_regex.search(script):
            return RiskLevel.DANGEROUS
        if self.sensitive_regex.search(script):
            return RiskLevel.SENSITIVE
        return RiskLevel.SAFE
        
    def evaluate_cdp(self, method: str, params: dict = None) -> RiskLevel:
        method_lower = method.lower()
        if "clear" in method_lower or "delete" in method_lower or "security." in method_lower:
            return RiskLevel.DANGEROUS
        if "input." in method_lower or "fetch." in method_lower or "network.set" in method_lower:
            return RiskLevel.SENSITIVE
        
        # Also check params if any
        if params:
            try:
                params_str = json.dumps(params).lower()
            except TypeError:
                params_str = str(params).lower()
                
            if self.dangerous_regex.search(params_str):
                return RiskLevel.DANGEROUS
            if self.sensitive_regex.search(params_str):
                return RiskLevel.SENSITIVE
                    
        return RiskLevel.SAFE
