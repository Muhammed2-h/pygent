import pytest
from unittest.mock import patch
from tools.human import tool_ask_user

def test_ask_user_basic():
    with patch("builtins.input", return_value="yes") as mock_input:
        response = tool_ask_user(question="Do you want to continue?")
        assert response == "yes"
        mock_input.assert_called_once_with("QUESTION: Do you want to continue?\nYour answer: ")

def test_ask_user_with_choices():
    with patch("builtins.input", return_value="A") as mock_input:
        response = tool_ask_user(
            question="Which option?",
            choices=["A", "B", "C"]
        )
        assert response == "A"
        mock_input.assert_called_once_with("QUESTION: Which option?\nCHOICES: A, B, C\nYour answer: ")

def test_ask_user_with_risk_and_reason():
    with patch("builtins.input", return_value="Proceed") as mock_input:
        response = tool_ask_user(
            question="Confirm action?",
            risk="High",
            reason="Because it will modify the system"
        )
        assert response == "Proceed"
        mock_input.assert_called_once_with(
            "QUESTION: Confirm action?\nREASON: Because it will modify the system\nRISK: High\nYour answer: "
        )

def test_ask_user_all_params():
    with patch("builtins.input", return_value="y") as mock_input:
        response = tool_ask_user(
            question="Delete files?",
            choices=["y", "n"],
            risk="Irreversible",
            reason="Cleanup"
        )
        assert response == "y"
        mock_input.assert_called_once_with(
            "QUESTION: Delete files?\nREASON: Cleanup\nRISK: Irreversible\nCHOICES: y, n\nYour answer: "
        )

def test_ask_user_exception():
    with patch("builtins.input", side_effect=EOFError("EOF")):
        response = tool_ask_user(question="Hello?")
        assert "Error reading input: EOF" in response
