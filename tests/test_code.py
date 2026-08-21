import json
import os
import sys

from tools.code import execute_code
from tools.registry import ToolRegistry


def test_execute_code_python():
    res = execute_code(language="python", code="print('hello')")
    data = json.loads(res)
    assert data["exit_code"] == 0
    assert data["stdout"].strip() == "hello"
    assert data["stderr"] == ""

def test_execute_code_bash():
    if sys.platform != "win32":
        res = execute_code(language="bash", code="echo 'world'")
        data = json.loads(res)
        assert data["exit_code"] == 0
        assert data["stdout"].strip() == "world"

def test_execute_code_timeout():
    res = execute_code(language="python", code="import time\ntime.sleep(2)", timeout=1)
    data = json.loads(res)
    assert data["exit_code"] != 0
    assert "timed out" in data["error"]

def test_execute_code_limits():
    code = "import sys\nsys.stdout.write('a' * 20000)\nsys.stderr.write('b' * 20000)"
    res = execute_code(language="python", code=code, stdout_limit=10, stderr_limit=10)
    data = json.loads(res)
    assert data["stdout"] == "aaaaaaaaaa\n...[stdout truncated]"
    assert data["stderr"] == "bbbbbbbbbb\n...[stderr truncated]"

def test_execute_code_cwd(tmpdir):
    cwd_path = str(tmpdir)
    res = execute_code(language="python", code="import os\nprint(os.getcwd())", cwd=cwd_path)
    data = json.loads(res)
    assert data["exit_code"] == 0
    # Use os.path.samefile on posix or just basic normalization
    if hasattr(os.path, 'samefile'):
        assert os.path.samefile(data["stdout"].strip(), cwd_path)
    else:
        assert data["stdout"].strip().lower() == cwd_path.lower()

def test_tool_registry_has_execute_code():
    registry = ToolRegistry()
    assert "execute_code" in registry.tools
