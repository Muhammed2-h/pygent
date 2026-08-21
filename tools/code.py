import json
import os
import subprocess
import sys
import tempfile
import threading
from typing import Literal

from .registry import tool


@tool(
    name="execute_code",
    description="Executes code in Python, Bash, or PowerShell.",
    risk_level="danger",
    category="system",
)
def execute_code(
    language: Literal["python", "bash", "powershell"],
    code: str,
    timeout: int = 60,
    cwd: str | None = None,
    stdout_limit: int = 10000,
    stderr_limit: int = 10000,
) -> str:
    """Executes the given code and returns the output, including exit code, stdout, and stderr."""
    from tools.filesystem import normalize_and_check_path
    if cwd:
        try:
            normalize_and_check_path(cwd)
        except ValueError as e:
            return json.dumps({"exit_code": -1, "stdout": "", "stderr": "", "error": str(e)})
    timeout = min(timeout, 600)

    ext_map = {
        "python": ".py",
        "bash": ".sh",
        "powershell": ".ps1",
    }
    
    ext = ext_map.get(language, ".txt")
    temp_file_path = None
    process = None
    
    result_dict = {
        "exit_code": -1,
        "stdout": "",
        "stderr": "",
        "error": None
    }

    def read_stream(stream, limit, key):
        output = bytearray()
        truncated = False
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                if not truncated:
                    if len(output) + len(chunk) > limit:
                        output.extend(chunk[:limit - len(output)])
                        truncated = True
                    else:
                        output.extend(chunk)
        except Exception:
            pass
            
        result = output.decode("utf-8", errors="replace")
        if truncated:
            result += f"\n...[{key} truncated]"
        result_dict[key] = result

    try:
        with tempfile.NamedTemporaryFile(suffix=ext, mode='w', encoding='utf-8', delete=False) as f:
            temp_file_path = f.name
            f.write(code)

        cmd = []
        env = os.environ.copy()
        if language == "python":
            env["PYTHONUNBUFFERED"] = "1"
            cmd = [sys.executable, "-u", temp_file_path]
        elif language == "bash":
            cmd = ["bash", temp_file_path]
        elif language == "powershell":
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_file_path]
        else:
            cmd = [language, temp_file_path]
        
        is_posix = (os.name == 'posix')
        kwargs = {}
        if is_posix:
            kwargs["start_new_session"] = True
        elif sys.platform == "win32":
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            **kwargs
        )
        
        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_limit, "stdout"))
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_limit, "stderr"))
        stdout_thread.start()
        stderr_thread.start()
        
        try:
            process.wait(timeout=timeout)
            result_dict["exit_code"] = process.returncode
        except subprocess.TimeoutExpired:
            if is_posix:
                try:
                    import signal
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except Exception:
                    process.kill()
            else:
                process.kill()
            process.wait()
            result_dict["exit_code"] = process.returncode
            result_dict["error"] = f"Execution timed out after {timeout} seconds."
            
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

    except Exception as e:
        if not result_dict["error"]:
            result_dict["error"] = str(e)
    finally:
        if process:
            if process.stdout: process.stdout.close()
            if process.stderr: process.stderr.close()
        if temp_file_path:
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
        
    return json.dumps(result_dict)
