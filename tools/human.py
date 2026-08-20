from typing import List, Optional
import builtins
from .registry import tool

@tool(
    name="ask_user",
    description="Ask the user a question. Use this to clarify requirements, solicit preferences, or get confirmation for risky actions.",
    risk_level="safe",
    category="human",
)
def tool_ask_user(
    question: str,
    choices: Optional[List[str]] = None,
    risk: Optional[str] = None,
    reason: Optional[str] = None
) -> str:
    """
    Ask the user a question, optionally providing choices, stating a risk, or giving a reason.
    """
    lines = [f"QUESTION: {question}"]
    if reason:
        lines.append(f"REASON: {reason}")
    if risk:
        lines.append(f"RISK: {risk}")
    if choices:
        lines.append(f"CHOICES: {', '.join(choices)}")
    
    prompt = "\n".join(lines) + "\nYour answer: "
    
    try:
        response = builtins.input(prompt)
        return response
    except Exception as e:
        return f"Error reading input: {e}"
