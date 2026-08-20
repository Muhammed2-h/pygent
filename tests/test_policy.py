import pytest
from browser.policy import BrowserPolicy, RiskLevel

def test_risk_level_ordering():
    assert RiskLevel.DANGEROUS > RiskLevel.SENSITIVE
    assert RiskLevel.SENSITIVE > RiskLevel.SAFE
    assert RiskLevel.DANGEROUS > RiskLevel.SAFE
    assert RiskLevel.SAFE < RiskLevel.DANGEROUS
    
    assert max(RiskLevel.SAFE, RiskLevel.DANGEROUS) == RiskLevel.DANGEROUS
    assert max(RiskLevel.SENSITIVE, RiskLevel.SAFE) == RiskLevel.SENSITIVE

def test_evaluate_js_safe():
    policy = BrowserPolicy()
    assert policy.evaluate_js("console.log('hello');") == RiskLevel.SAFE
    assert policy.evaluate_js("document.querySelector('div')") == RiskLevel.SAFE
    # Check that substrings inside words are safe
    assert policy.evaluate_js("let payload = 1;") == RiskLevel.SAFE
    assert policy.evaluate_js("window.removeEventListener('click', fn)") == RiskLevel.SAFE
    assert policy.evaluate_js("let buyer = 'me';") == RiskLevel.SAFE

def test_evaluate_js_sensitive():
    policy = BrowserPolicy()
    # Need word boundaries
    assert policy.evaluate_js("document.getElementById('upload').click()") == RiskLevel.SENSITIVE
    assert policy.evaluate_js("form.submit()") == RiskLevel.SENSITIVE
    # Changed from downloadFile to download
    assert policy.evaluate_js("window.download()") == RiskLevel.SENSITIVE

def test_evaluate_js_dangerous():
    policy = BrowserPolicy()
    assert policy.evaluate_js("confirm('purchase')") == RiskLevel.DANGEROUS
    assert policy.evaluate_js("delete data") == RiskLevel.DANGEROUS
    assert policy.evaluate_js("document.cookie = 'password=123'") == RiskLevel.DANGEROUS

def test_evaluate_cdp_safe():
    policy = BrowserPolicy()
    assert policy.evaluate_cdp("Page.navigate", {"url": "https://example.com"}) == RiskLevel.SAFE
    assert policy.evaluate_cdp("Runtime.evaluate") == RiskLevel.SAFE

def test_evaluate_cdp_sensitive():
    policy = BrowserPolicy()
    assert policy.evaluate_cdp("Input.dispatchKeyEvent") == RiskLevel.SENSITIVE
    assert policy.evaluate_cdp("Fetch.continueRequest") == RiskLevel.SENSITIVE

def test_evaluate_cdp_dangerous():
    policy = BrowserPolicy()
    assert policy.evaluate_cdp("Security.setIgnoreCertificateErrors") == RiskLevel.DANGEROUS
    assert policy.evaluate_cdp("Storage.clearDataForOrigin") == RiskLevel.DANGEROUS
    # Use word boundary for delete
    assert policy.evaluate_cdp("Runtime.evaluate", {"expression": "delete(account)"}) == RiskLevel.DANGEROUS
