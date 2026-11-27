"""Orchestration layer: the agent loop (model -> tool calls -> results -> ... -> final)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import AgentSpec
from .memory import SessionStore
from .providers import ChatProvider, build_provider
from .tools import ToolRegistry, registry as global_registry
from . import builtin_tools  # noqa: F401  (registers built-in tools)


@dataclass
class RunResult:
    reply: str
    session_id: str
    steps: int
    tool_calls: list[dict] = field(default_factory=list)


def _clean_assistant(msg: dict) -> dict:
    out: dict = {"role": "assistant", "content": msg.get("content") or ""}
    tcs = msg.get("tool_calls")
    if tcs:
        out["tool_calls"] = [
            {
                "id": tc.get("id") or f"call_{i}",
                "type": "function",
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"].get("arguments") or "{}",
                },
            }
            for i, tc in enumerate(tcs)
        ]
    return out


class AgentLoop:
    def __init__(self, spec: AgentSpec, provider: ChatProvider | None = None,
                 tools: ToolRegistry | None = None, store: SessionStore | None = None):
        self.spec = spec
        self.store = store or SessionStore()
        self.tools = tools or self._build_registry(spec)
        self.provider = provider or build_provider(spec.model)

    @staticmethod
    def _build_registry(spec: AgentSpec) -> ToolRegistry:
        for mod in spec.tool_modules:
            p = Path(mod)
            if not p.is_absolute() and spec.source_path is not None:
                p = spec.source_path.parent / p
            global_registry.load_module(p)
        selected = ToolRegistry()
        for t in global_registry.select(spec.tools):
            selected._tools[t.name] = t
        return selected

    def run(self, message: str, session_id: str | None = None) -> RunResult:
        session_id = session_id or self.store.new_session_id()
        history = self.store.load_history(session_id)
        messages: list[dict] = [{"role": "system", "content": self.spec.system_prompt}]
        messages += history
        messages.append({"role": "user", "content": message})

        schemas = [t.schema() for t in self.tools.select(["*"])]
        record: list[dict] = []
        reply = ""
        steps = 0
        for step in range(1, self.spec.max_steps + 1):
            steps = step
            msg = _clean_assistant(self.provider.chat(messages, schemas, self.spec.temperature))
            messages.append(msg)
            self.store.trace(session_id, {"step": step, "assistant": msg})
            if not msg.get("tool_calls"):
                reply = msg["content"]
                break
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                args = tc["function"]["arguments"]
                result = self.tools.call(name, args)
                record.append({"name": name, "arguments": args, "result": result[:500]})
                tool_msg = {"role": "tool", "tool_call_id": tc["id"], "content": result}
                messages.append(tool_msg)
                self.store.trace(session_id, {"step": step, "tool": name, "args": args,
                                              "result": result[:2000]})
        else:
            reply = "(max_steps reached before a final answer)"

        self.store.save_history(session_id, messages[1:])  # persist without system prompt
        return RunResult(reply=reply, session_id=session_id, steps=steps, tool_calls=record)
