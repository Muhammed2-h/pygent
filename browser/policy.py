from enum import Enum

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

    def evaluate_js(self, script: str) -> RiskLevel:
        script_lower = script.lower()
        for kw in self.dangerous_keywords:
            if kw in script_lower:
                return RiskLevel.DANGEROUS
        for kw in self.sensitive_keywords:
            if kw in script_lower:
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
            params_str = str(params).lower()
            for kw in self.dangerous_keywords:
                if kw in params_str:
                    return RiskLevel.DANGEROUS
            for kw in self.sensitive_keywords:
                if kw in params_str:
                    return RiskLevel.SENSITIVE
                    
        return RiskLevel.SAFE
