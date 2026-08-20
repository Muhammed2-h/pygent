import json
import os
import subprocess
import sys
import tempfile
from typing import Literal, Optional

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
    cwd: Optional[str] = None,
    stdout_limit: int = 10000,
    stderr_limit: int = 10000,
) -> str:
    """Executes the given code and returns the output, including exit code, stdout, and stderr."""
    if timeout > 600:
        timeout = 600

    ext_map = {
        "python": ".py",
        "bash": ".sh",
        "powershell": ".ps1",
    }
    
    ext = ext_map.get(language, ".txt")
    
    with tempfile.NamedTemporaryFile(suffix=ext, mode='w', encoding='utf-8', delete=False) as f:
        f.write(code)
        temp_file_path = f.name

    cmd = []
    if language == "python":
        cmd = [sys.executable, temp_file_path]
    elif language == "bash":
        cmd = ["bash", temp_file_path]
    elif language == "powershell":
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_file_path]
    else:
        # Fallback or unknown
        cmd = [language, temp_file_path]
    
    result_dict = {
        "exit_code": -1,
        "stdout": "",
        "stderr": "",
        "error": None
    }
    
    out_f = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False)
    err_f = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False)
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=out_f,
            stderr=err_f,
            text=True
        )
        
        try:
            process.wait(timeout=timeout)
            result_dict["exit_code"] = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            result_dict["exit_code"] = process.returncode
            result_dict["error"] = f"Execution timed out after {timeout} seconds."
            
        out_f.seek(0)
        result_dict["stdout"] = out_f.read(stdout_limit)
        if len(out_f.read(1)) > 0:
            result_dict["stdout"] += "\n...[stdout truncated]"
            
        err_f.seek(0)
        result_dict["stderr"] = err_f.read(stderr_limit)
        if len(err_f.read(1)) > 0:
            result_dict["stderr"] += "\n...[stderr truncated]"

    except Exception as e:
        result_dict["error"] = str(e)
    finally:
        out_f.close()
        err_f.close()
        try:
            os.remove(out_f.name)
            os.remove(err_f.name)
            os.remove(temp_file_path)
        except OSError:
            pass
        
    return json.dumps(result_dict)
