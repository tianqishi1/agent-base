"""Custom tools for your agent: just decorate functions with @tool.

The JSON schema is generated from type hints; the docstring becomes the description.
"""
from agentbase.tools import tool


@tool
def word_count(text: str) -> str:
    """Count characters and whitespace-separated words in text."""
    return f"chars={len(text)} words={len(text.split())}"


@tool
def todo_add(item: str, priority: int = 2) -> str:
    """Append a todo item to todos.txt in the agent workspace."""
    from agentbase.builtin_tools import _safe_path
    p = _safe_path("todos.txt")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"[P{priority}] {item}\n")
    return f"added: {item}"