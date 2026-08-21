import platform
import sys
from unittest.mock import MagicMock, patch

from environment.probe import (
    probe_all,
    probe_chrome,
    probe_chrome_extension,
    probe_docker,
    probe_filesystem,
    probe_git,
    probe_http_bridge,
    probe_node,
    probe_os,
    probe_python,
    probe_virtual_environment,
    probe_websocket_port,
)


def test_probe_os():
    cap = probe_os()
    assert cap.name == "os"
    assert cap.available is True
    assert cap.verified is True
    assert platform.system() in cap.version

def test_probe_python():
    cap = probe_python()
    assert cap.name == "python"
    assert cap.available is True
    assert cap.verified is True
    assert sys.version.split()[0] in cap.version

@patch("shutil.which")
@patch("subprocess.run")
def test_probe_cli_tools(mock_run, mock_which):
    mock_which.return_value = "/usr/bin/tool"
    mock_result = MagicMock()
    mock_result.stdout = "tool version 1.2.3"
    mock_run.return_value = mock_result

    # Git
    cap = probe_git()
    assert cap.name == "git"
    assert cap.available is True
    assert cap.verified is True
    assert "1.2.3" in cap.version

    # Node
    mock_result.stdout = "v14.17.0"
    cap = probe_node()
    assert cap.name == "node"
    assert cap.available is True
    assert cap.verified is True
    assert cap.version == "14.17.0"

    # Docker
    mock_result.stdout = "Docker version 20.10.7, build f0df350"
    cap = probe_docker()
    assert cap.name == "docker"
    assert cap.available is True
    assert cap.verified is True
    assert cap.version == "20.10.7"

@patch("shutil.which")
@patch("subprocess.run")
def test_probe_chrome(mock_run, mock_which):
    mock_which.side_effect = lambda cmd: "/usr/bin/google-chrome" if cmd == "google-chrome" else None
    mock_result = MagicMock()
    mock_result.stdout = "Google Chrome 114.0.5735.90 "
    mock_run.return_value = mock_result

    cap = probe_chrome()
    assert cap.name == "chrome"
    assert cap.available is True
    assert cap.verified is True
    assert cap.version == "Google Chrome 114.0.5735.90"

@patch("os.path.isdir")
def test_probe_chrome_extension(mock_isdir):
    mock_isdir.return_value = True
    cap = probe_chrome_extension()
    assert cap.name == "chrome_extension"
    assert cap.available is True

@patch("environment.probe._is_port_open")
def test_probe_ports(mock_is_port_open):
    mock_is_port_open.return_value = True
    
    cap = probe_websocket_port()
    assert cap.name == "websocket_port"
    assert cap.available is True
    assert cap.version == "9222"

    cap = probe_http_bridge()
    assert cap.name == "http_bridge"
    assert cap.available is True

def test_probe_filesystem():
    cap = probe_filesystem()
    assert cap.name == "filesystem"
    assert cap.available is True
    assert cap.verified is True

def test_probe_virtual_environment():
    cap = probe_virtual_environment()
    assert cap.name == "virtual_environment"
    # Testing logic can be simple, just ensure it returns a valid EnvironmentCapability
    assert isinstance(cap.available, bool)

@patch("environment.probe.probe_os")
@patch("environment.probe.probe_python")
def test_probe_all(mock_python, mock_os):
    mock_os.return_value = MagicMock(name="os")
    mock_python.return_value = MagicMock(name="python")
    results = probe_all()
    assert "os" in results
    assert "python" in results
    assert "git" in results
    assert "chrome" in results
    assert "docker" in results
