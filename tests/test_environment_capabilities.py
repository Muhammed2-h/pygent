from environment.capabilities import Capability, CapabilityRegistry


def test_capability_defaults():
    cap = Capability()
    assert not cap.available
    assert not cap.configured
    assert not cap.verified
    assert cap.version is None
    assert cap.last_checked is None

def test_capability_registry_defaults():
    registry = CapabilityRegistry()
    
    assert not registry.browser.available
    assert not registry.browser_extension.available
    assert not registry.cdp.available
    assert not registry.filesystem.available
    assert not registry.python.available
    assert not registry.shell.available
    assert not registry.git.available
    assert not registry.ocr.available
    assert not registry.vision.available
    assert not registry.desktop.available
