import re


class PrivacyFilter:
    def __init__(self):
        self.patterns = [
            (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "[REDACTED_API_KEY]"),
            (re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"), "[REDACTED_GEMINI_KEY]"),
        ]

    def scrub(self, text: str) -> str:
        for pattern, replacement in self.patterns:
            text = pattern.sub(replacement, text)
        return text
