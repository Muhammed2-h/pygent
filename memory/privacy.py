import re


class PrivacyFilter:
    def __init__(self):
        self.patterns = [
            (re.compile(r"sk-ant-[a-zA-Z0-9\-_]{20,}"), "[REDACTED_ANTHROPIC_KEY]"),
            (re.compile(r"sk-(proj-)?[a-zA-Z0-9\-_]{20,}"), "[REDACTED_API_KEY]"),
            (re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"), "[REDACTED_GEMINI_KEY]"),
            (re.compile(r"(?i)bearer\s+[a-zA-Z0-9\-\._~+/]+=*"), "[REDACTED_BEARER_TOKEN]"),
            (re.compile(r"(?i)(['\"]?)(cookie|set-cookie)\1\s*([=:]\s*)(?:([\"'])(.*?)\4|([^\n&,\]\}]+))"), r"\1\2\1\3\4[REDACTED_COOKIE]\4"),
            (re.compile(r"(?i)(['\"]?)(session[-_]?token|session[-_]?id)\1\s*([=:]\s*)(?:([\"'])(.*?)\4|([^\s\n&,\]\}]+))"), r"\1\2\1\3\4[REDACTED_SESSION_TOKEN]\4"),
            (re.compile(r"(?i)(['\"]?)authorization\1\s*([=:]\s*)(?:([\"'])(.*?)\3|([^\n&,\]\}]+))"), r"\1Authorization\1\2\3[REDACTED_AUTH_HEADER]\3"),
            (re.compile(r"(?i)(['\"]?)(password|passwd|pwd)\1\s*([=:]\s*)(?:([\"'])(.*?)\4|([^\s\n&,\]\}]+))"), r"\1\2\1\3\4[REDACTED_PASSWORD]\4"),
            (re.compile(r"(https?://)[^:\s]+:[^@\s]+@"), r"\1[REDACTED_CREDENTIALS]@"),
        ]

    def scrub(self, text: str) -> str:
        for pattern, replacement in self.patterns:
            text = pattern.sub(replacement, text)
        return text
