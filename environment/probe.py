import platform
import subprocess
import sys
import shutil
import os
import socket
from datetime import datetime, timezone
from typing import Dict

from models import EnvironmentCapability

def get_current_time() -> str:
    return datetime.now(timezone.utc).isoformat()

def probe_os() -> EnvironmentCapability:
    return EnvironmentCapability(
        name="os",
        available=True,
        version=f"{platform.system()} {platform.release()}",
        verified=True,
        last_checked=get_current_time()
    )

def probe_python() -> EnvironmentCapability:
    return EnvironmentCapability(
        name="python",
        available=True,
        version=sys.version.split()[0],
        verified=True,
        last_checked=get_current_time()
    )

def _probe_cli_tool(name: str, cmd: list, version_flag: str = "--version", version_extract=lambda x: x.strip()) -> EnvironmentCapability:
    cap = EnvironmentCapability(
        name=name,
        available=False,
        verified=False,
        last_checked=get_current_time()
    )
    if shutil.which(cmd[0]):
        try:
            result = subprocess.run(cmd + [version_flag], capture_output=True, text=True, check=True, timeout=5)
            cap.available = True
            cap.version = version_extract(result.stdout if result.stdout else result.stderr)
            cap.verified = True
        except Exception:
            cap.available = True
            cap.verified = False
    return cap

def probe_git() -> EnvironmentCapability:
    return _probe_cli_tool("git", ["git"], version_extract=lambda x: x.split("version")[-1].strip())

def probe_node() -> EnvironmentCapability:
    return _probe_cli_tool("node", ["node"], version_extract=lambda x: x.strip().lstrip("v"))

def probe_docker() -> EnvironmentCapability:
    return _probe_cli_tool("docker", ["docker"], version_extract=lambda x: x.split("version")[-1].split(",")[0].strip())

def probe_chrome() -> EnvironmentCapability:
    cmds = ["google-chrome", "chrome", "google-chrome-stable", "chromium", "chromium-browser"]
    cap = EnvironmentCapability(
        name="chrome",
        available=False,
        verified=False,
        last_checked=get_current_time()
    )
    for cmd in cmds:
        if shutil.which(cmd):
            try:
                result = subprocess.run([cmd, "--version"], capture_output=True, text=True, check=True, timeout=5)
                cap.available = True
                cap.version = result.stdout.strip()
                cap.verified = True
                break
            except Exception:
                pass
    return cap

def probe_chrome_extension() -> EnvironmentCapability:
    exists = os.path.isdir("extension") or os.path.isdir("chrome_extension")
    return EnvironmentCapability(
        name="chrome_extension",
        available=exists,
        version=None,
        verified=exists,
        last_checked=get_current_time()
    )

def _is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect(('127.0.0.1', port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False

def probe_websocket_port() -> EnvironmentCapability:
    open_port = _is_port_open(9222)
    return EnvironmentCapability(
        name="websocket_port",
        available=open_port,
        version="9222" if open_port else None,
        verified=open_port,
        last_checked=get_current_time()
    )

def probe_http_bridge() -> EnvironmentCapability:
    open_port = _is_port_open(9222)
    return EnvironmentCapability(
        name="http_bridge",
        available=open_port,
        version=None,
        verified=open_port,
        last_checked=get_current_time()
    )

def probe_filesystem() -> EnvironmentCapability:
    return EnvironmentCapability(
        name="filesystem",
        available=True,
        version=None,
        verified=True,
        last_checked=get_current_time()
    )

def probe_virtual_environment() -> EnvironmentCapability:
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    return EnvironmentCapability(
        name="virtual_environment",
        available=in_venv,
        version=None,
        verified=in_venv,
        last_checked=get_current_time()
    )

PROBE_MAP = {
    "os": probe_os,
    "python": probe_python,
    "git": probe_git,
    "chrome": probe_chrome,
    "chrome_extension": probe_chrome_extension,
    "websocket_port": probe_websocket_port,
    "http_bridge": probe_http_bridge,
    "filesystem": probe_filesystem,
    "virtual_environment": probe_virtual_environment,
    "node": probe_node,
    "docker": probe_docker
}

def probe_capability(name: str) -> EnvironmentCapability | None:
    probe_func = PROBE_MAP.get(name)
    if probe_func:
        return probe_func()
    return None

def probe_all() -> Dict[str, EnvironmentCapability]:
    return {name: func() for name, func in PROBE_MAP.items()}
