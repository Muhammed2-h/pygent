import datetime
import os
from tools import ToolRegistry, eval_expr


def test_tool_registry_calculate():
    registry = ToolRegistry()
    res = registry.execute("calculate", {"expression": "2*3"})
    assert res == "6"

    res_add = registry.execute("calculate", {"expression": "10 + 5"})
    assert res_add == "15"

    # Exponentiation is intentionally disabled to prevent DoS (e.g. 99999**99999)
    res_pow = registry.execute("calculate", {"expression": "2 ** 3"})
    assert res_pow.startswith("Error:")

    res_neg = registry.execute("calculate", {"expression": "-5 + 2"})
    assert res_neg == "-3"

    res_err = registry.execute("calculate", {"expression": "import os"})
    assert res_err.startswith("Error:")


def test_tool_registry_get_time():
    registry = ToolRegistry()
    res = registry.execute("get_time", {})
    # Verify it returns a valid ISO format datetime
    parsed = datetime.datetime.fromisoformat(res)
    assert parsed is not None


def test_tool_registry_env_info(monkeypatch):
    registry = ToolRegistry()
    monkeypatch.setenv("TEST_VAR", "test_val")
    res = registry.execute("env_info", {"variable": "TEST_VAR"})
    assert res == "test_val"

    res_not_found = registry.execute("env_info", {"variable": "NON_EXISTENT_VAR_12345"})
    assert res_not_found == "Not found"


def test_tool_registry_unknown_tool():
    registry = ToolRegistry()
    res = registry.execute("unknown_tool", {})
    assert res == "Error: tool unknown_tool not found"


def test_tool_registry_schemas():
    registry = ToolRegistry()
    schemas = registry.get_tool_schemas()
    assert len(schemas) == 3
    tool_names = [s["function"]["name"] for s in schemas]
    assert "get_time" in tool_names
    assert "calculate" in tool_names
    assert "env_info" in tool_names
