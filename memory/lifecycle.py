import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from memory.storage import MemoryStore
from memory.types import MemoryType

logger = logging.getLogger(__name__)

class MemoryCheckpoint:
    def __init__(self, max_tokens: int = 300, chars_per_token: int = 4):
        self._checkpoint: Dict[str, Any] = {}
        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token
        self.max_chars = max_tokens * chars_per_token
        self.max_list_items = 3

    def update_checkpoint(
        self,
        objective: Optional[str] = None,
        constraints: Optional[List[str]] = None,
        important_findings: Optional[List[str]] = None,
        failed_attempts: Optional[List[str]] = None,
        next_action: Optional[str] = None
    ) -> None:
        if objective is not None:
            self._checkpoint["objective"] = objective
        if constraints is not None:
            # Keep first constraints (fundamental rules)
            self._checkpoint["constraints"] = constraints[:self.max_list_items]
        if important_findings is not None:
            # Keep latest findings
            self._checkpoint["important_findings"] = important_findings[-self.max_list_items:]
        if failed_attempts is not None:
            # Keep latest failed attempts
            self._checkpoint["failed_attempts"] = failed_attempts[-self.max_list_items:]
        if next_action is not None:
            self._checkpoint["next_action"] = next_action

    def get_checkpoint(self) -> str:
        if not self._checkpoint:
            return ""
        
        formatted = "=== WORKING MEMORY CHECKPOINT ===\n"
        for key, value in self._checkpoint.items():
            if value:
                formatted += f"{key.replace('_', ' ').title()}:\n"
                if isinstance(value, list):
                    for item in value:
                        formatted += f"- {item}\n"
                else:
                    formatted += f"{value}\n"
                formatted += "\n"
        
        formatted = formatted.strip()
        if len(formatted) > self.max_chars:
            return formatted[:self.max_chars - 3] + "..."
        return formatted

    def clear_checkpoint(self) -> None:
        self._checkpoint.clear()


# ---------------------------------------------------------------------------
# Long-Term Memory Finalization (Task 9)
# ---------------------------------------------------------------------------

@dataclass
class ExtractedFact:
    """A fact extracted from execution history."""
    content: str
    source: str = ""
    entry_type: str = ""
    confidence: float = 0.5
    verified: bool = False


@dataclass
class ExtractedProcedure:
    """A successful procedure / SOP extracted from execution history."""
    name: str
    description: str
    procedure: str
    trigger: str = ""
    prerequisites: str = ""
    verification: str = ""
    confidence: float = 0.5


@dataclass
class FinalizationResult:
    """Summary of what was persisted during finalization."""
    facts_persisted: int = 0
    procedures_persisted: int = 0
    items_rejected: int = 0
    details: List[str] = field(default_factory=list)


# Patterns that indicate content should be rejected
_TEMP_VAR_PATTERNS = re.compile(
    r"(?:^tmp_|^temp_|^_tmp|^_temp|^\$\{|^var\d+|^[ijx]\s*=\s*\d)",
    re.IGNORECASE,
)
_REASONING_MARKERS = [
    "let me think",
    "i think",
    "maybe",
    "perhaps",
    "i'm not sure",
    "let's try",
    "hmm",
    "wait,",
    "actually,",
    "on second thought",
    "i wonder",
    "step 1:",
    "step 2:",
    "first,",
    "next,",
    "then,",
    "finally,",
]
_GENERIC_KNOWLEDGE = [
    "python is a programming language",
    "html is a markup language",
    "css is used for styling",
    "javascript runs in the browser",
    "http is a protocol",
    "sql is used for databases",
    "git is version control",
    "linux is an operating system",
]


def _is_temporary_variable(text: str) -> bool:
    """Check if text looks like a temporary variable assignment."""
    return bool(_TEMP_VAR_PATTERNS.search(text.strip()))


def _is_unverified_claim(fact: ExtractedFact) -> bool:
    """Reject facts with low confidence that are not verified."""
    return not fact.verified and fact.confidence < 0.3


def _is_reasoning_chain(text: str) -> bool:
    """Check if text is internal reasoning rather than a fact."""
    lower = text.lower().strip()
    return any(lower.startswith(marker) for marker in _REASONING_MARKERS)


def _is_generic_knowledge(text: str) -> bool:
    """Check if text is commonly known and not worth persisting."""
    lower = text.lower().strip().rstrip(".")
    return any(lower == gk for gk in _GENERIC_KNOWLEDGE)


def _is_failed_experiment(entry: Dict[str, Any]) -> bool:
    """Check if an execution entry represents a failed experiment."""
    if entry.get("success") is False or entry.get("ok") is False:
        return True
    error = entry.get("error")
    if error and str(error).strip():
        return True
    return False


def _deduplicate_facts(
    facts: List[ExtractedFact], store: MemoryStore
) -> List[ExtractedFact]:
    """Remove facts that already exist in the store."""
    unique: List[ExtractedFact] = []
    seen_contents: set = set()
    for fact in facts:
        normalised = fact.content.strip().lower()
        if normalised in seen_contents:
            continue
        seen_contents.add(normalised)

        # Check store for duplicates via FTS
        try:
            existing = store.search(fact.content)
            if any(
                e["content"].strip().lower() == normalised for e in existing
            ):
                continue
        except Exception:
            # If search fails, keep the fact to be safe
            pass
        unique.append(fact)
    return unique


def _deduplicate_procedures(
    procedures: List[ExtractedProcedure], store: MemoryStore
) -> List[ExtractedProcedure]:
    """Remove procedures whose name already exists in the skills table."""
    unique: List[ExtractedProcedure] = []
    seen_names: set = set()
    for proc in procedures:
        norm_name = proc.name.strip().lower()
        if norm_name in seen_names:
            continue
        seen_names.add(norm_name)
        # Existing skills with same name will be updated (upsert), so keep them
        unique.append(proc)
    return unique


def _extract_facts(history: List[Dict[str, Any]]) -> List[ExtractedFact]:
    """Extract verified facts from execution history entries."""
    facts: List[ExtractedFact] = []
    for entry in history:
        if _is_failed_experiment(entry):
            continue

        # Entries with type "fact" or "observation" or "environment"
        entry_type = entry.get("type", "")
        content = entry.get("content", "")
        if not content or not isinstance(content, str):
            continue

        if _is_temporary_variable(content):
            continue
        if _is_reasoning_chain(content):
            continue
        if _is_generic_knowledge(content):
            continue

        if entry_type in ("fact", "observation", "environment", "finding"):
            fact = ExtractedFact(
                content=content,
                source=entry.get("source", ""),
                entry_type=entry_type,
                confidence=float(entry.get("confidence", 0.5)),
                verified=bool(entry.get("verified", False)),
            )
            if _is_unverified_claim(fact):
                continue
            facts.append(fact)
    return facts


def _extract_procedures(
    history: List[Dict[str, Any]],
) -> List[ExtractedProcedure]:
    """Extract successful procedures from execution history entries."""
    procedures: List[ExtractedProcedure] = []
    for entry in history:
        if _is_failed_experiment(entry):
            continue

        entry_type = entry.get("type", "")
        if entry_type not in ("procedure", "skill", "sop"):
            continue

        name = entry.get("name", "")
        procedure_text = entry.get("procedure", "") or entry.get("content", "")
        if not name or not procedure_text:
            continue

        if _is_reasoning_chain(procedure_text):
            continue

        proc = ExtractedProcedure(
            name=name,
            description=entry.get("description", name),
            procedure=procedure_text,
            trigger=entry.get("trigger", ""),
            prerequisites=entry.get("prerequisites", ""),
            verification=entry.get("verification", ""),
            confidence=float(entry.get("confidence", 0.5)),
        )
        procedures.append(proc)
    return procedures


def finalize_task_memory(
    history: List[Dict[str, Any]],
    store: MemoryStore,
) -> FinalizationResult:
    """Inspect completed-task execution history and persist useful info.

    Workflow:
        completed task → inspect execution history → find verified facts
        → find successful procedures → remove temporary details
        → deduplicate → update L2 → update L3

    Persists:
        • L2 (environment facts): verified facts, observations,
          environment details.
        • L3 (skills / SOPs): successful procedures, learned skills.

    Rejects:
        temporary variables, unverified claims, reasoning chains,
        generic knowledge, duplicate facts, failed experiments.
    """
    result = FinalizationResult()

    if not history:
        result.details.append("Empty execution history; nothing to finalize.")
        return result

    # --- Extract ---------------------------------------------------------
    raw_facts = _extract_facts(history)
    raw_procedures = _extract_procedures(history)

    rejected_count = len(history) - len(raw_facts) - len(raw_procedures)

    # --- Deduplicate -----------------------------------------------------
    facts = _deduplicate_facts(raw_facts, store)
    procedures = _deduplicate_procedures(raw_procedures, store)

    rejected_count += (len(raw_facts) - len(facts))
    rejected_count += (len(raw_procedures) - len(procedures))
    result.items_rejected = max(rejected_count, 0)

    # --- Persist L2 (environment facts) ----------------------------------
    for fact in facts:
        try:
            if fact.entry_type == "environment" or "environment" in fact.source.lower():
                mem_type = MemoryType.ENVIRONMENT
            else:
                mem_type = MemoryType.FACT
        except Exception:
            mem_type = MemoryType.FACT
        try:
            store.add_memory(
                content=fact.content,
                mem_type=mem_type,
                title=fact.content[:80],
            )
            result.facts_persisted += 1
            logger.debug("Persisted L2 fact: %s", fact.content[:60])
        except Exception as exc:
            logger.warning("Failed to persist fact: %s", exc)
            result.details.append(f"Failed to persist fact: {exc}")

    # --- Persist L3 (skills / SOPs) --------------------------------------
    for proc in procedures:
        try:
            store.add_skill(
                name=proc.name,
                description=proc.description,
                procedure=proc.procedure,
                trigger=proc.trigger,
                prerequisites=proc.prerequisites,
                verification=proc.verification,
                confidence=proc.confidence,
            )
            result.procedures_persisted += 1
            logger.debug("Persisted L3 skill: %s", proc.name)
        except Exception as exc:
            logger.warning("Failed to persist skill: %s", exc)
            result.details.append(f"Failed to persist skill: {exc}")

    result.details.append(
        f"Finalized: {result.facts_persisted} facts, "
        f"{result.procedures_persisted} procedures persisted, "
        f"{result.items_rejected} items rejected."
    )
    return result
