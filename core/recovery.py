"""Loop recovery: failure classification and recovery strategies.

Classifies failures into categories and recommends concrete recovery
actions that the agent loop can use to self-heal.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------

class FailureType(str, Enum):
    """Exhaustive failure categories."""
    TRANSIENT = "transient"
    SELECTOR = "selector"
    NAVIGATION = "navigation"
    PERMISSION = "permission"
    ENVIRONMENT = "environment"
    AUTHENTICATION = "authentication"
    UNSUPPORTED = "unsupported"
    JAVASCRIPT = "javascript"
    UNKNOWN = "unknown"


# Ordered list – first match wins
_CLASSIFICATION_RULES: List[tuple] = [
    # (FailureType, compiled regex pattern applied to the error string)
    (FailureType.TRANSIENT, re.compile(
        r"(timeout|timed?\s*out|ETIMEDOUT|ECONNRESET|ECONNREFUSED"
        r"|rate.limit|429|503|502|504|retry|temporary\s*failure"
        r"|network\s*(error|unreachable)|connection\s*(reset|refused|closed))",
        re.IGNORECASE,
    )),
    (FailureType.AUTHENTICATION, re.compile(
        r"(auth(entication|orization)?\s*(fail|error|required|denied|expired)"
        r"|401|403\s*forbidden|login\s*required|session\s*expired"
        r"|invalid\s*(token|credential|api.key)|unauthenticated"
        r"|access\s*denied)",
        re.IGNORECASE,
    )),
    (FailureType.PERMISSION, re.compile(
        r"(permission\s*denied|not\s*permitted|EACCES|EPERM"
        r"|insufficient\s*privilege|operation\s*not\s*allowed"
        r"|read.only\s*file.system|cannot\s*write)",
        re.IGNORECASE,
    )),
    (FailureType.SELECTOR, re.compile(
        r"(no\s*such\s*element|element\s*not\s*(found|visible|interactable)"
        r"|selector\s*(not\s*found|invalid|failed)|stale\s*element"
        r"|NoSuchElementException|ElementNotInteractableException"
        r"|could\s*not\s*(find|locate)\s*(element|selector|button|link|input)"
        r"|xpath\s*(error|invalid)|css\s*selector\s*(error|invalid))",
        re.IGNORECASE,
    )),
    (FailureType.NAVIGATION, re.compile(
        r"(navigation\s*(fail|error)|page\s*not\s*found|404"
        r"|ERR_NAME_NOT_RESOLVED|ERR_CONNECTION|net::ERR_"
        r"|invalid\s*url|cannot\s*navigate|about:blank"
        r"|ERR_CERT|SSL_ERROR|redirect\s*loop|url\s*(error|invalid))",
        re.IGNORECASE,
    )),
    (FailureType.ENVIRONMENT, re.compile(
        r"(ModuleNotFoundError|ImportError|No\s*module\s*named"
        r"|command\s*not\s*found|missing\s*package|pip\s*install"
        r"|npm\s*(ERR|error)|FileNotFoundError|No\s*such\s*file"
        r"|executable\s*not\s*found|ENOENT"
        r"|environment\s*(error|not\s*configured))",
        re.IGNORECASE,
    )),
    (FailureType.UNSUPPORTED, re.compile(
        r"(not\s*supported|unsupported|not\s*implemented"
        r"|NotImplementedError|UnsupportedOperationException"
        r"|deprecated|unavailable\s*feature|cannot\s*perform"
        r"|browser\s*does\s*not\s*support)",
        re.IGNORECASE,
    )),
    (FailureType.JAVASCRIPT, re.compile(
        r"(EvaluationError|JavaScript\s*error|CSP|CDP\s*error|unsafe-eval)",
        re.IGNORECASE,
    )),
]


@dataclass
class ClassifiedFailure:
    """A failure with its classified type and original error text."""
    failure_type: FailureType
    error_text: str
    pattern_matched: str = ""


class FailureClassifier:
    """Classify an error string into a ``FailureType``."""

    def classify(self, error_text: str) -> ClassifiedFailure:
        """Return a *ClassifiedFailure* for the given error text.

        The classifier walks ``_CLASSIFICATION_RULES`` in order and returns
        the first match.  If nothing matches, ``FailureType.UNKNOWN`` is
        returned.
        """
        if not error_text:
            return ClassifiedFailure(
                failure_type=FailureType.UNKNOWN,
                error_text=error_text,
            )

        for ftype, pattern in _CLASSIFICATION_RULES:
            m = pattern.search(error_text)
            if m:
                return ClassifiedFailure(
                    failure_type=ftype,
                    error_text=error_text,
                    pattern_matched=m.group(0),
                )

        return ClassifiedFailure(
            failure_type=FailureType.UNKNOWN,
            error_text=error_text,
        )


# ---------------------------------------------------------------------------
# Recovery strategies
# ---------------------------------------------------------------------------

class RecoveryAction(str, Enum):
    """Concrete action the agent loop can execute."""
    RETRY = "retry"
    RESCAN_SELECTORS = "rescan_selectors"
    INSPECT_URL = "inspect_url"
    USE_CDP = "use_cdp"
    INSTALL_PACKAGE = "install_package"
    ASK_USER = "ask_user"
    CHECKPOINT_AND_CHANGE_STRATEGY = "checkpoint_and_change_strategy"
    RE_AUTHENTICATE = "re_authenticate"
    SKIP = "skip"


@dataclass
class RecoveryRecommendation:
    """What the recovery strategy recommends the agent loop should do."""
    action: RecoveryAction
    reason: str
    system_hint: str = ""
    max_retries: int = 2


# Default mapping from failure type → recovery recommendation
_DEFAULT_RECOVERY: Dict[FailureType, RecoveryRecommendation] = {
    FailureType.TRANSIENT: RecoveryRecommendation(
        action=RecoveryAction.RETRY,
        reason="Transient failure – retrying may succeed.",
        system_hint="The last action failed due to a transient error (timeout / network). Retry the same action.",
        max_retries=3,
    ),
    FailureType.SELECTOR: RecoveryRecommendation(
        action=RecoveryAction.RESCAN_SELECTORS,
        reason="Selector failure – element not found. Re-scan the page.",
        system_hint=(
            "The selector did not match any element. "
            "Re-scan the page DOM to find the correct selector."
        ),
    ),
    FailureType.NAVIGATION: RecoveryRecommendation(
        action=RecoveryAction.INSPECT_URL,
        reason="Navigation failure – inspect current URL and page state.",
        system_hint=(
            "Navigation failed. Inspect the current URL and page content "
            "to determine what went wrong before retrying."
        ),
    ),
    FailureType.PERMISSION: RecoveryRecommendation(
        action=RecoveryAction.ASK_USER,
        reason="Permission denied – need user intervention.",
        system_hint=(
            "A permission error occurred. Ask the user for help or "
            "elevated permissions."
        ),
    ),
    FailureType.ENVIRONMENT: RecoveryRecommendation(
        action=RecoveryAction.INSTALL_PACKAGE,
        reason="Missing package or environment issue – use environment manager.",
        system_hint=(
            "A missing dependency or environment issue was detected. "
            "Attempt to install the required package or configure the environment."
        ),
    ),
    FailureType.AUTHENTICATION: RecoveryRecommendation(
        action=RecoveryAction.RE_AUTHENTICATE,
        reason="Authentication failure – re-authenticate or ask user for credentials.",
        system_hint=(
            "Authentication failed. Try re-authenticating or ask the user "
            "to provide valid credentials."
        ),
    ),
    FailureType.UNSUPPORTED: RecoveryRecommendation(
        action=RecoveryAction.SKIP,
        reason="Unsupported operation – skip and try an alternative approach.",
        system_hint=(
            "This operation is not supported. Try a different approach "
            "to achieve the same goal."
        ),
    ),
    FailureType.JAVASCRIPT: RecoveryRecommendation(
        action=RecoveryAction.USE_CDP,
        reason="JavaScript failure – fall back to CDP protocol.",
        system_hint=(
            "JavaScript execution failed. Fall back to using CDP for this operation."
        ),
    ),
    FailureType.UNKNOWN: RecoveryRecommendation(
        action=RecoveryAction.CHECKPOINT_AND_CHANGE_STRATEGY,
        reason="Unknown failure – checkpoint progress and change strategy.",
        system_hint=(
            "An unknown error occurred. Save a checkpoint of progress so far "
            "and try a different strategy."
        ),
    ),
}


class RecoveryStrategy:
    """Decide how to recover from classified failures.

    Tracks consecutive failures of the same type so that repeated unknown
    failures escalate to checkpoint-and-change-strategy.
    """

    def __init__(self, max_consecutive: int = 3):
        self.max_consecutive = max_consecutive
        self._consecutive_counts: Dict[FailureType, int] = {}
        self._history: List[ClassifiedFailure] = []

    @property
    def history(self) -> List[ClassifiedFailure]:
        return list(self._history)

    def recommend(self, failure: ClassifiedFailure) -> RecoveryRecommendation:
        """Return a ``RecoveryRecommendation`` for the given failure.

        If the same failure type has been seen ``max_consecutive`` times in
        a row the strategy escalates to
        ``RecoveryAction.CHECKPOINT_AND_CHANGE_STRATEGY`` regardless of the
        failure type.
        """
        self._history.append(failure)

        # Track consecutive same-type failures
        ftype = failure.failure_type
        if len(self._history) >= 2 and self._history[-2].failure_type == ftype:
            self._consecutive_counts[ftype] = self._consecutive_counts.get(ftype, 0) + 1
        else:
            self._consecutive_counts[ftype] = 1

        # Escalate if repeated too many times
        if self._consecutive_counts.get(ftype, 0) >= self.max_consecutive:
            logger.info(
                "Escalating recovery for %s after %d consecutive failures",
                ftype.value,
                self._consecutive_counts[ftype],
            )
            self._consecutive_counts[ftype] = 0  # reset counter
            return RecoveryRecommendation(
                action=RecoveryAction.CHECKPOINT_AND_CHANGE_STRATEGY,
                reason=(
                    f"Repeated {ftype.value} failure ({self.max_consecutive}× "
                    f"consecutive) – checkpoint and change strategy."
                ),
                system_hint=(
                    "Multiple consecutive failures of the same type. "
                    "Save a checkpoint and adopt a completely different approach."
                ),
            )

        rec = _DEFAULT_RECOVERY.get(ftype)
        if rec is None:
            rec = _DEFAULT_RECOVERY[FailureType.UNKNOWN]
        return rec

    def reset(self) -> None:
        """Clear all tracking state."""
        self._consecutive_counts.clear()
        self._history.clear()
