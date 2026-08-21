"""Tests for core.recovery — failure classification & recovery strategies."""

import pytest

from core.recovery import (
    ClassifiedFailure,
    FailureClassifier,
    FailureType,
    RecoveryAction,
    RecoveryRecommendation,
    RecoveryStrategy,
)


# ── FailureType enum ──────────────────────────────────────────────────────

class TestFailureType:
    def test_all_expected_members(self):
        expected = {
            "transient", "selector", "navigation", "permission",
            "environment", "authentication", "unsupported", "unknown",
        }
        assert {ft.value for ft in FailureType} == expected

    def test_string_value(self):
        assert FailureType.TRANSIENT == "transient"
        assert FailureType.UNKNOWN == "unknown"


# ── FailureClassifier ────────────────────────────────────────────────────

class TestFailureClassifier:
    @pytest.fixture()
    def classifier(self):
        return FailureClassifier()

    # -- transient --
    @pytest.mark.parametrize("error", [
        "TimeoutError: navigation timeout of 30s exceeded",
        "ETIMEDOUT connecting to host",
        "ECONNRESET by peer",
        "rate limit exceeded, try again later",
        "HTTP 503 Service Unavailable",
        "HTTP 429 Too Many Requests",
        "Temporary failure in name resolution",
        "Connection reset by peer",
        "Network error during fetch",
    ])
    def test_transient(self, classifier, error):
        result = classifier.classify(error)
        assert result.failure_type == FailureType.TRANSIENT
        assert result.error_text == error
        assert result.pattern_matched

    # -- selector --
    @pytest.mark.parametrize("error", [
        "NoSuchElementException: could not find element",
        "Element not found: #submit-btn",
        "stale element reference",
        "ElementNotInteractableException",
        "Could not locate selector .login-form",
        "selector not found: [data-id='x']",
    ])
    def test_selector(self, classifier, error):
        assert classifier.classify(error).failure_type == FailureType.SELECTOR

    # -- navigation --
    @pytest.mark.parametrize("error", [
        "net::ERR_NAME_NOT_RESOLVED",
        "Page not found: 404",
        "Navigation failed to https://example.com",
        "ERR_CERT_AUTHORITY_INVALID",
        "SSL_ERROR_HANDSHAKE_FAILURE_ALERT",
        "redirect loop detected",
        "Invalid URL provided",
    ])
    def test_navigation(self, classifier, error):
        assert classifier.classify(error).failure_type == FailureType.NAVIGATION

    # -- permission --
    @pytest.mark.parametrize("error", [
        "PermissionError: [Errno 13] Permission denied",
        "EACCES: permission denied, open '/etc/shadow'",
        "Operation not permitted",
        "Read-only file system",
    ])
    def test_permission(self, classifier, error):
        assert classifier.classify(error).failure_type == FailureType.PERMISSION

    # -- environment --
    @pytest.mark.parametrize("error", [
        "ModuleNotFoundError: No module named 'requests'",
        "ImportError: cannot import name 'foo'",
        "command not found: node",
        "npm ERR! missing dependency",
        "FileNotFoundError: [Errno 2] No such file or directory",
        "executable not found in PATH",
    ])
    def test_environment(self, classifier, error):
        assert classifier.classify(error).failure_type == FailureType.ENVIRONMENT

    # -- authentication --
    @pytest.mark.parametrize("error", [
        "HTTP 401 Unauthorized",
        "Authentication failed: invalid token",
        "session expired, please log in again",
        "Login required to view this page",
        "Invalid API key",
        "Access denied for user 'anon'",
    ])
    def test_authentication(self, classifier, error):
        assert classifier.classify(error).failure_type == FailureType.AUTHENTICATION

    # -- unsupported --
    @pytest.mark.parametrize("error", [
        "NotImplementedError: this feature is not supported",
        "UnsupportedOperationException",
        "deprecated API endpoint",
        "Browser does not support WebGL",
    ])
    def test_unsupported(self, classifier, error):
        assert classifier.classify(error).failure_type == FailureType.UNSUPPORTED

    # -- unknown --
    @pytest.mark.parametrize("error", [
        "something went horribly wrong",
        "unexpected error #9999",
        "",
    ])
    def test_unknown(self, classifier, error):
        assert classifier.classify(error).failure_type == FailureType.UNKNOWN

    def test_classify_returns_classified_failure(self, classifier):
        result = classifier.classify("timeout error")
        assert isinstance(result, ClassifiedFailure)
        assert result.failure_type == FailureType.TRANSIENT
        assert result.error_text == "timeout error"
        assert result.pattern_matched  # non-empty


# ── RecoveryStrategy ─────────────────────────────────────────────────────

class TestRecoveryStrategy:
    @pytest.fixture()
    def strategy(self):
        return RecoveryStrategy(max_consecutive=3)

    @pytest.fixture()
    def classifier(self):
        return FailureClassifier()

    def _make_failure(self, ftype: FailureType, msg: str = "err") -> ClassifiedFailure:
        return ClassifiedFailure(failure_type=ftype, error_text=msg)

    # -- default recommendations by failure type --

    def test_transient_recommends_retry(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.TRANSIENT))
        assert rec.action == RecoveryAction.RETRY

    def test_selector_recommends_rescan(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.SELECTOR))
        assert rec.action == RecoveryAction.RESCAN_SELECTORS

    def test_navigation_recommends_inspect_url(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.NAVIGATION))
        assert rec.action == RecoveryAction.INSPECT_URL

    def test_permission_recommends_ask_user(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.PERMISSION))
        assert rec.action == RecoveryAction.ASK_USER

    def test_environment_recommends_install_package(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.ENVIRONMENT))
        assert rec.action == RecoveryAction.INSTALL_PACKAGE

    def test_authentication_recommends_re_authenticate(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.AUTHENTICATION))
        assert rec.action == RecoveryAction.RE_AUTHENTICATE

    def test_unsupported_recommends_skip(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.UNSUPPORTED))
        assert rec.action == RecoveryAction.SKIP

    def test_unknown_recommends_checkpoint_change_strategy(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.UNKNOWN))
        assert rec.action == RecoveryAction.CHECKPOINT_AND_CHANGE_STRATEGY

    # -- recommendation fields --

    def test_recommendation_has_reason(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.SELECTOR))
        assert rec.reason
        assert isinstance(rec.reason, str)

    def test_recommendation_has_system_hint(self, strategy):
        rec = strategy.recommend(self._make_failure(FailureType.SELECTOR))
        assert rec.system_hint
        assert "selector" in rec.system_hint.lower() or "re-scan" in rec.system_hint.lower()

    # -- escalation on repeated failures --

    def test_repeated_unknown_escalates(self, strategy):
        fail = self._make_failure(FailureType.UNKNOWN)
        strategy.recommend(fail)
        strategy.recommend(fail)
        rec = strategy.recommend(fail)  # 3rd consecutive → escalate
        assert rec.action == RecoveryAction.CHECKPOINT_AND_CHANGE_STRATEGY

    def test_repeated_transient_escalates(self, strategy):
        """Even transient failures escalate after max_consecutive hits."""
        fail = self._make_failure(FailureType.TRANSIENT)
        strategy.recommend(fail)
        strategy.recommend(fail)
        rec = strategy.recommend(fail)
        assert rec.action == RecoveryAction.CHECKPOINT_AND_CHANGE_STRATEGY

    def test_different_types_do_not_escalate(self, strategy):
        strategy.recommend(self._make_failure(FailureType.TRANSIENT))
        strategy.recommend(self._make_failure(FailureType.SELECTOR))
        rec = strategy.recommend(self._make_failure(FailureType.NAVIGATION))
        # No escalation — each type only appeared once
        assert rec.action == RecoveryAction.INSPECT_URL

    def test_escalation_resets_counter(self, strategy):
        fail = self._make_failure(FailureType.TRANSIENT)
        strategy.recommend(fail)
        strategy.recommend(fail)
        strategy.recommend(fail)  # escalates
        # After escalation the counter resets, so next one is normal
        rec = strategy.recommend(fail)
        assert rec.action == RecoveryAction.RETRY

    # -- history tracking --

    def test_history_tracking(self, strategy):
        f1 = self._make_failure(FailureType.TRANSIENT, "t1")
        f2 = self._make_failure(FailureType.SELECTOR, "s1")
        strategy.recommend(f1)
        strategy.recommend(f2)
        assert len(strategy.history) == 2
        assert strategy.history[0].failure_type == FailureType.TRANSIENT
        assert strategy.history[1].failure_type == FailureType.SELECTOR

    def test_reset_clears_state(self, strategy):
        strategy.recommend(self._make_failure(FailureType.TRANSIENT))
        strategy.reset()
        assert len(strategy.history) == 0

    # -- integration: classifier → strategy --

    def test_end_to_end_classify_and_recover(self, strategy, classifier):
        error = "NoSuchElementException: button not found"
        failure = classifier.classify(error)
        assert failure.failure_type == FailureType.SELECTOR
        rec = strategy.recommend(failure)
        assert rec.action == RecoveryAction.RESCAN_SELECTORS

    def test_end_to_end_js_failure_environment(self, strategy, classifier):
        """JS / CDP-related errors that map to environment (missing package)."""
        error = "ModuleNotFoundError: No module named 'selenium'"
        failure = classifier.classify(error)
        assert failure.failure_type == FailureType.ENVIRONMENT
        rec = strategy.recommend(failure)
        assert rec.action == RecoveryAction.INSTALL_PACKAGE

    def test_custom_max_consecutive(self):
        strategy = RecoveryStrategy(max_consecutive=2)
        fail = self._make_failure(FailureType.SELECTOR)
        strategy.recommend(fail)
        rec = strategy.recommend(fail)  # 2nd → escalate already
        assert rec.action == RecoveryAction.CHECKPOINT_AND_CHANGE_STRATEGY
