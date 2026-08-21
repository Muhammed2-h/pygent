import time
from datetime import datetime, timezone

from core.logger import memory_logger
from memory.privacy import PrivacyFilter
from memory.storage import MemoryStore


class MemoryService:
    def __init__(self, store: MemoryStore, privacy: PrivacyFilter):
        self.store = store
        self.privacy = privacy

    def add(self, content: str, mem_type: str = "semantic"):
        
        
        start = time.time()
        try:
            clean_content = self.privacy.scrub(content)
            self.store.add_memory(clean_content, mem_type)
            duration = time.time() - start
            memory_logger.info("Memory added", extra={"tool": "memory.add", "status": "success", "duration": duration, "error": None})
        except Exception as e:
            duration = time.time() - start
            memory_logger.error("Memory add failed", extra={"tool": "memory.add", "status": "error", "duration": duration, "error": str(e)})
            raise

    def _build_fts_query(self, query: str) -> str:
        stop_words = {"a", "an", "the", "and", "or", "but", "is", "are", "was", "were", "in", "on", "at", "to", "for", "with", "about", "please", "help", "me", "write", "function", "that", "can", "you", "could", "would", "how", "do", "i"}
        raw_tokens = [t.strip('.,;!?()[]{}') for t in query.split()]
        tokens = [t for t in raw_tokens if t and t.lower() not in stop_words]
        
        # Keep it simple but grab more keywords (up to 10)
        # Quote tokens and replace double quotes to prevent FTS syntax errors
        safe_tokens = [t.replace('"', '') for t in tokens[:10]]
        safe_tokens = [t for t in safe_tokens if t]
        
        if not safe_tokens:
            return ""
        return " OR ".join(f'"{t}"' for t in safe_tokens)

    def get_context_for(self, query: str) -> str:
        
        
        start = time.time()
        fts_query = self._build_fts_query(query)
        if not fts_query:
            duration = time.time() - start
            memory_logger.info("Empty fts query", extra={"tool": "memory.get_context_for", "status": "success", "duration": duration, "error": None})
            return ""

        try:
            results = self.store.search(fts_query)
            duration = time.time() - start
            memory_logger.info("Search success", extra={"tool": "memory.get_context_for", "status": "success", "duration": duration, "error": None})
        except Exception as e:
            duration = time.time() - start
            memory_logger.error("Search failed", extra={"tool": "memory.get_context_for", "status": "error", "duration": duration, "error": str(e)})
            return ""

        if not results:
            return ""

        context = "Relevant Context:\n"
        for r in results[:5]:
            context += f"- {r['content']}\n"
        return context

    def get_relevant_skills(self, task: str) -> list[dict]:
        
        
        start = time.time()
        fts_query = self._build_fts_query(task)
        if not fts_query:
            duration = time.time() - start
            memory_logger.info("Empty fts query", extra={"tool": "memory.get_relevant_skills", "status": "success", "duration": duration, "error": None})
            return []

        try:
            results = self.store.search_skills(fts_query)
            duration = time.time() - start
            memory_logger.info("Search skills success", extra={"tool": "memory.get_relevant_skills", "status": "success", "duration": duration, "error": None})
        except Exception as e:
            duration = time.time() - start
            memory_logger.error("Search skills failed", extra={"tool": "memory.get_relevant_skills", "status": "error", "duration": duration, "error": str(e)})
            return []
            
        if not results:
            return []

        def calculate_score(skill: dict, rank_index: int) -> float:
            # 1. Task similarity (1.0 for top match, decreasing by 0.1)
            similarity = max(0.0, 1.0 - (rank_index * 0.1))
            
            # 2. Confidence
            confidence = skill.get('confidence', 0.5)
            
            # 3. Success rate
            success = skill.get('success_count', 0)
            failure = skill.get('failure_count', 0)
            total = success + failure
            success_rate = success / total if total > 0 else 0.5
            
            # 4. Recency
            recency = 0.0
            last_used = skill.get('last_used')
            if last_used:
                try:
                    last = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    days_ago = (now - last).days
                    recency = max(0.0, 1.0 - (days_ago / 30.0))  # decay over 30 days
                except Exception:
                    pass
            
            # Combine scores (weights could be adjusted, using arbitrary reasonable weights)
            return (similarity * 0.4) + (confidence * 0.3) + (success_rate * 0.2) + (recency * 0.1)

        scored_skills = []
        for i, skill in enumerate(results):
            score = calculate_score(skill, i)
            # Map procedure to content for ContextBuilder
            skill['content'] = skill.get('procedure', '')
            skill['score'] = score
            scored_skills.append(skill)
            
        scored_skills.sort(key=lambda x: x['score'], reverse=True)
        return scored_skills[:5]
