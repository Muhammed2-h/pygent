import re
from .storage import MemoryStore
from .privacy import PrivacyFilter


class MemoryService:
    def __init__(self, store: MemoryStore, privacy: PrivacyFilter):
        self.store = store
        self.privacy = privacy

    def add(self, content: str, mem_type: str = "semantic"):
        clean_content = self.privacy.scrub(content)
        self.store.add_memory(clean_content, mem_type)

    def get_context_for(self, query: str) -> str:
        words = [w for w in re.findall(r"\w+", query) if len(w) > 3]
        if not words:
            return ""
        fts_query = " OR ".join(f'"{w}"' for w in words[:5])

        try:
            results = self.store.search(fts_query)
        except Exception:
            return ""

        if not results:
            return ""

        context = "Relevant Context:\n"
        for r in results[:5]:
            context += f"- {r['content']}\n"
        return context
