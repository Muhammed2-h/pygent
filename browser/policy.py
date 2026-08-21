from enum import Enum
from functools import total_ordering
import re
import json

@total_ordering
class RiskLevel(Enum):
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

def extract_words(text: str) -> set:
    text = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', text)
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
    return set(w.lower() for w in re.split(r'[^a-zA-Z0-9]+', s2) if w)

class BrowserPolicy:
    def __init__(self):
        self.dangerous_keywords = {"purchase", "buy", "pay", "transfer", "delete", "password", "credential"}
        self.sensitive_keywords = {"upload", "message", "send", "download", "submit", "post"}

    def evaluate_js(self, script: str) -> RiskLevel:
        words = extract_words(script)
        if self.dangerous_keywords & words:
            return RiskLevel.DANGEROUS
        if self.sensitive_keywords & words:
            return RiskLevel.SENSITIVE
        return RiskLevel.SAFE
        
    def evaluate_cdp(self, method: str, params: dict = None) -> RiskLevel:
        method_lower = method.lower()
        if "clear" in method_lower or "delete" in method_lower or "security." in method_lower:
            return RiskLevel.DANGEROUS
        if "input." in method_lower or "fetch." in method_lower or "network.set" in method_lower:
            return RiskLevel.SENSITIVE
        
        if params:
            try:
                params_str = json.dumps(params)
            except TypeError:
                params_str = str(params)
                
            words = extract_words(params_str)
            if self.dangerous_keywords & words:
                return RiskLevel.DANGEROUS
            if self.sensitive_keywords & words:
                return RiskLevel.SENSITIVE
                    
        return RiskLevel.SAFE
