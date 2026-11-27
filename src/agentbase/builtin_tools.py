"""Built-in tools. File tools are sandboxed to AGENTBASE_WORKSPACE."""
from __future__ import annotations

import ast
import datetime as _dt
import operator
import os
import urllib.request
from pathlib import Path

from .tools import tool


def _workspace() -> Path:
    root = Path(os.environ.get("AGENTBASE_WORKSPACE", "workspace")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_path(rel: str) -> Path:
    root = _workspace()
    p = (root / rel).resolve()
    if not str(p).startswith(str(root)):
        raise ValueError(f"path escapes workspace: {rel}")
    return p


@tool
def current_time() -> str:
    """Get current local date and time."""
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")


_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("only arithmetic expressions are allowed")


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression, e.g. '3 * (4 + 5) / 2'."""
    return str(_eval(ast.parse(expression, mode="eval")))


@tool
def read_file(path: str) -> str:
    """Read a UTF-8 text file inside the agent workspace. path is relative to workspace."""
    p = _safe_path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return text[:20000]


@tool
def write_file(path: str, content: str) -> str:
    """Write a UTF-8 text file inside the agent workspace. path is relative to workspace."""
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"written {len(content)} chars to {path}"


@tool
def list_dir(path: str = ".") -> str:
    """List entries of a directory inside the agent workspace."""
    p = _safe_path(path)
    return "\n".join(sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())) or "(empty)"


@tool
def http_get(url: str) -> str:
    """Fetch a URL via HTTP GET and return the body text (truncated to 8000 chars)."""
    req = urllib.request.Request(url, headers={"User-Agent": "agentbase/0.1"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read(200000).decode("utf-8", errors="replace")
    return body[:8000]
