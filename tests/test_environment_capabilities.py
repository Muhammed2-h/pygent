import pytest
from environment.capabilities import Capability, CapabilityRegistry
from models import EnvironmentCapability

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

def test_capability_registry_update_from_probes():
    registry = CapabilityRegistry()
    
    probes = {
        "python": EnvironmentCapability(
            name="python", available=True, version="3.10.0", verified=True, last_checked="2026-08-20T00:00:00Z"
        ),
        "git": EnvironmentCapability(
            name="git", available=True, version="2.34.1", verified=True, last_checked="2026-08-20T00:00:00Z"
        ),
        "chrome": EnvironmentCapability(
            name="chrome", available=False, version=None, verified=False, last_checked="2026-08-20T00:00:00Z"
        )
    }
    
    registry.update_from_probes(probes)
    
    assert registry.python.available is True
    assert registry.python.configured is True
    assert registry.python.version == "3.10.0"
    
    assert registry.git.available is True
    assert registry.git.configured is True
    assert registry.git.version == "2.34.1"
    
    assert registry.browser.available is False
    assert registry.browser.configured is False
    assert registry.browser.version is None

