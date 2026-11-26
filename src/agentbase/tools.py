"""Tool layer: @tool decorator + registry + auto JSON-schema from type hints."""
from __future__ import annotations

import importlib.util
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, func: Callable | None = None, *, name: str | None = None, description: str | None = None):
        """Usable as @registry.register or @registry.register(name=...)."""
        def wrap(f: Callable) -> Callable:
            tname = name or f.__name__
            desc = description or (inspect.getdoc(f) or "").strip() or tname
            sig = inspect.signature(f)
            props: dict[str, Any] = {}
            required: list[str] = []
            for pname, param in sig.parameters.items():
                ann = param.annotation if param.annotation is not inspect.Parameter.empty else str
                jtype = _TYPES.get(ann, "string")
                props[pname] = {"type": jtype, "description": pname}
                if param.default is inspect.Parameter.empty:
                    required.append(pname)
            params = {"type": "object", "properties": props, "required": required}
            self._tools[tname] = Tool(tname, desc, params, f)
            f._tool_name = tname  # type: ignore[attr-defined]
            return f
        return wrap(func) if func is not None else wrap

    def load_module(self, path: str | Path) -> None:
        """Import a python file; its @tool-decorated functions self-register."""
        path = Path(path)
        spec = importlib.util.spec_from_file_location(f"agentbase_tools_{path.stem}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load tool module: {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def select(self, patterns: list[str]) -> list[Tool]:
        if not patterns or "*" in patterns:
            return list(self._tools.values())
        return [self._tools[p] for p in patterns if p in self._tools]

    def call(self, name: str, arguments: str | dict) -> str:
        tool = self.get(name)
        if tool is None:
            return f"ERROR: unknown tool '{name}'. Available: {', '.join(self.names())}"
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
            result = tool.func(**args)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:  # tool errors go back to the model, never crash the loop
            return f"ERROR: {type(exc).__name__}: {exc}"


# Global registry used by built-in tools and the @tool decorator.
registry = ToolRegistry()


def tool(func: Callable | None = None, *, name: str | None = None, description: str | None = None):
    """Decorator: register a function into the global registry."""
    return registry.register(func, name=name, description=description)