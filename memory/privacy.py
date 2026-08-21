import re


class PrivacyFilter:
    def __init__(self):
        self.patterns = [
            (re.compile(r"sk-ant-[a-zA-Z0-9\-_]{20,}"), "[REDACTED_ANTHROPIC_KEY]"),
            (re.compile(r"sk-(proj-)?[a-zA-Z0-9\-_]{20,}"), "[REDACTED_API_KEY]"),
            (re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"), "[REDACTED_GEMINI_KEY]"),
            (re.compile(r"(?i)bearer\s+[a-zA-Z0-9\-\._~+/]+=*"), "[REDACTED_BEARER_TOKEN]"),
            (re.compile(r"(?i)(cookie|set-cookie):\s*[^\n]+"), r"\1: [REDACTED_COOKIE]"),
            (re.compile(r"(?i)(session[-_]?token|session[-_]?id)(\s*[=:]\s*)[a-zA-Z0-9\-\._]+"), r"\1\2[REDACTED_SESSION_TOKEN]"),
            (re.compile(r"(?i)authorization:\s*[^\n]+"), "Authorization: [REDACTED_AUTH_HEADER]"),
            (re.compile(r"(?i)(password|passwd|pwd)(\s*[=:]\s*)[^\s\n&]+"), r"\1\2[REDACTED_PASSWORD]"),
            (re.compile(r"(https?://)[^:\s]+:[^@\s]+@"), r"\1[REDACTED_CREDENTIALS]@"),
        ]

    def scrub(self, text: str) -> str:
        for pattern, replacement in self.patterns:
            text = pattern.sub(replacement, text)
        return text
