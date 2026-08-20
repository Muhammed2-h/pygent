import os
import pytest
from pathlib import Path

from tools.filesystem import file_read, file_write, file_patch, normalize_and_check_path

def test_normalize_and_check_path_no_root(tmp_path):
    # Without root
    p = normalize_and_check_path(str(tmp_path / "test.txt"))
    assert p == (tmp_path / "test.txt").resolve()

def test_normalize_and_check_path_with_root(tmp_path):
    root = str(tmp_path)
    # Inside root
    p = normalize_and_check_path(str(tmp_path / "test.txt"), allowed_root=root)
    assert p == (tmp_path / "test.txt").resolve()

    # Outside root (e.g. parent)
    with pytest.raises(ValueError, match="Access denied: Path"):
        normalize_and_check_path(str(tmp_path.parent / "test.txt"), allowed_root=root)

    # Attempt directory traversal
    with pytest.raises(ValueError, match="Access denied: Path"):
        normalize_and_check_path(str(tmp_path / ".." / "test.txt"), allowed_root=root)

def test_file_write_and_read(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
    file_path = str(tmp_path / "data" / "file.txt")
    
    # Write
    res_write = file_write(file_path, "Hello World")
    assert "Successfully wrote" in res_write
    assert (tmp_path / "data" / "file.txt").exists()

    # Read
    res_read = file_read(file_path)
    assert res_read == "Hello World"

def test_file_read_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
    file_path = str(tmp_path / "missing.txt")
    
    # Missing file
    assert "does not exist" in file_read(file_path)

    # Directory instead of file
    assert "is not a file" in file_read(str(tmp_path))

    # Outside root
    assert "Access denied" in file_read(str(tmp_path.parent / "outside.txt"))

def test_file_patch(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
    file_path = str(tmp_path / "patch.txt")
    file_write(file_path, "Line 1\nLine 2\nLine 3\n")

    # Successful patch
    res = file_patch(file_path, "Line 2", "Line TWO")
    assert "Successfully patched" in res
    assert "Line TWO" in file_read(file_path)

    # Patch not found
    res = file_patch(file_path, "Line 9", "Line NINE")
    assert "exact text to find was not found" in res

    # Non-unique patch
    file_write(file_path, "duplicate\nduplicate\n")
    res = file_patch(file_path, "duplicate\n", "unique\n")
    assert "Unique replacement required" in res

    # Patch missing file
    res = file_patch(str(tmp_path / "missing_patch.txt"), "a", "b")
    assert "does not exist" in res
