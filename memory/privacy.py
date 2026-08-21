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

    def scrub_object(self, obj: any, abstract_login: bool = False) -> any:
        if isinstance(obj, str):
            scrubbed = self.scrub(obj)
            return scrubbed
        elif isinstance(obj, dict):
            new_dict = {}
            has_auth = False
            for k, v in obj.items():
                new_v = self.scrub_object(v, abstract_login)
                new_dict[k] = new_v
                if isinstance(v, str) and new_v != v:
                    if any(x in new_v for x in ["[REDACTED_COOKIE]", "[REDACTED_SESSION_TOKEN]", "[REDACTED_AUTH_HEADER]", "[REDACTED_CREDENTIALS]", "[REDACTED_PASSWORD]"]):
                        has_auth = True
            if abstract_login and has_auth:
                new_dict["_auth_status"] = {
                    "authenticated": True,
                    "site": "example.com",
                    "status": "login workflow verified"
                }
            return new_dict
        elif isinstance(obj, list):
            return [self.scrub_object(v, abstract_login) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(self.scrub_object(v, abstract_login) for v in obj)
        elif isinstance(obj, set):
            return set(self.scrub_object(v, abstract_login) for v in obj)
        return obj
