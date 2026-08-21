import pytest
from unittest.mock import patch, MagicMock
from tools.environment import tool_env_expand

def test_env_expand_success():
    with patch("tools.environment.EnvironmentManager") as MockManager:
        mock_instance = MockManager.return_value
        mock_instance.ensure_capability.return_value = True
        
        result = tool_env_expand("pytest", "pip install pytest", "testing")
        
        assert "Successfully expanded" in result
        mock_instance.ensure_capability.assert_called_once_with("pytest", "pip install pytest", "testing")

def test_env_expand_failure():
    with patch("tools.environment.EnvironmentManager") as MockManager:
        mock_instance = MockManager.return_value
        mock_instance.ensure_capability.return_value = False
        
        result = tool_env_expand("pytest", "pip install pytest", "testing")
        
        assert "Failed to expand" in result
        mock_instance.ensure_capability.assert_called_once_with("pytest", "pip install pytest", "testing")

def test_confirmation_callback():
    from tools.environment import confirmation_callback
    with patch("tools.environment.tool_ask_user") as mock_ask:
        mock_ask.return_value = "y"
        assert confirmation_callback("Test prompt") is True
        
        mock_ask.return_value = "n"
        assert confirmation_callback("Test prompt") is False
        
        mock_ask.return_value = " Y "
        assert confirmation_callback("Test prompt") is True
