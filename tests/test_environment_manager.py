import pytest
from unittest.mock import Mock, patch
from environment.manager import EnvironmentManager
from models import EnvironmentCapability


@pytest.fixture
def mock_memory_store():
    store = Mock()
    store.add_memory = Mock()
    return store


@pytest.fixture
def mock_capabilities():
    return {
        "python": EnvironmentCapability(name="python", available=True, version="3.10"),
        "git": EnvironmentCapability(name="git", available=False)
    }


def test_init_defaults():
    manager = EnvironmentManager()
    assert manager.confirmation_callback("Test") is False
    assert manager.memory_store is None


def test_check_capabilities(mock_capabilities):
    with patch("environment.manager.probe_all", return_value=mock_capabilities):
        manager = EnvironmentManager()
        caps = manager.check_capabilities()
        assert "python" in caps
        assert caps["python"].available is True


def test_get_capability(mock_capabilities):
    with patch("environment.manager.probe_all", return_value=mock_capabilities):
        manager = EnvironmentManager()
        assert manager.get_capability("python").available is True
        assert manager.get_capability("git").available is False
        assert manager.get_capability("unknown") is None


def test_requires_confirmation():
    manager = EnvironmentManager()
    assert manager._requires_confirmation("sudo apt install git") is True
    assert manager._requires_confirmation("echo 'hello'") is False
    assert manager._requires_confirmation("pip install req", reason="installing driver") is True
    assert manager._requires_confirmation("google-chrome --version") is True


def test_repair_or_install_needs_confirmation_denied():
    callback = Mock(return_value=False)
    manager = EnvironmentManager(confirmation_callback=callback)
    
    with patch("subprocess.run") as mock_run:
        result = manager.repair_or_install("git", "sudo apt install git")
        assert result is False
        callback.assert_called_once()
        mock_run.assert_not_called()


def test_repair_or_install_needs_confirmation_approved():
    callback = Mock(return_value=True)
    manager = EnvironmentManager(confirmation_callback=callback)
    
    with patch("subprocess.run") as mock_run:
        result = manager.repair_or_install("git", "sudo apt install git")
        assert result is True
        callback.assert_called_once()
        mock_run.assert_called_once()


def test_repair_or_install_no_confirmation_needed():
    callback = Mock()
    manager = EnvironmentManager(confirmation_callback=callback)
    
    with patch("subprocess.run") as mock_run:
        result = manager.repair_or_install("git", "git --version")
        assert result is True
        callback.assert_not_called()
        mock_run.assert_called_once()


def test_verify_and_persist(mock_capabilities, mock_memory_store):
    with patch("environment.manager.probe_all", return_value=mock_capabilities):
        manager = EnvironmentManager(memory_store=mock_memory_store)
        
        # Test available capability
        assert manager.verify_and_persist("python") is True
        mock_memory_store.add_memory.assert_called_once_with(
            content="Capability 'python' is available and verified.",
            mem_type="fact",
            title="Capability: python"
        )
        
        # Test unavailable capability
        assert manager.verify_and_persist("git") is False


def test_ensure_capability_already_available(mock_capabilities, mock_memory_store):
    with patch("environment.manager.probe_all", return_value=mock_capabilities):
        manager = EnvironmentManager(memory_store=mock_memory_store)
        
        # Should just verify and persist
        assert manager.ensure_capability("python", "sudo apt install python") is True
        mock_memory_store.add_memory.assert_called_once()


def test_ensure_capability_missing_no_command(mock_capabilities):
    with patch("environment.manager.probe_all", return_value=mock_capabilities):
        manager = EnvironmentManager()
        
        # Missing, and no install command provided
        assert manager.ensure_capability("git") is False


def test_ensure_capability_install_success(mock_memory_store):
    # First it's missing, then after repair it's available
    state = {"available": False}
    
    def fake_probe_all():
        return {
            "git": EnvironmentCapability(name="git", available=state["available"])
        }
    
    with patch("environment.manager.probe_all", side_effect=fake_probe_all):
        manager = EnvironmentManager(
            confirmation_callback=lambda x: True,
            memory_store=mock_memory_store
        )
        
        with patch("subprocess.run") as mock_run:
            def side_effect(*args, **kwargs):
                state["available"] = True
            mock_run.side_effect = side_effect
            
            assert manager.ensure_capability("git", "sudo apt install git") is True
            mock_run.assert_called_once()
            mock_memory_store.add_memory.assert_called_once()


def test_ensure_capability_install_fails():
    def fake_probe_all():
        return {
            "git": EnvironmentCapability(name="git", available=False)
        }
    
    with patch("environment.manager.probe_all", side_effect=fake_probe_all):
        manager = EnvironmentManager(confirmation_callback=lambda x: True)
        
        with patch("subprocess.run") as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
            
            assert manager.ensure_capability("git", "sudo apt install git") is False
            mock_run.assert_called_once()
