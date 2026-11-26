"""Model layer: any OpenAI-compatible endpoint (DeepSeek / DashScope / OpenAI / Ollama / vLLM).

Swap providers by changing base_url + api_key_env + model name in the agent YAML.
"""
from __future__ import annotations

from typing import Protocol

from .config import ModelSpec


class ChatProvider(Protocol):
    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             temperature: float = 0.3) -> dict:
        """Return an assistant message dict: {role, content, tool_calls?}."""
        ...


class OpenAICompatProvider:
    def __init__(self, spec: ModelSpec):
        from openai import OpenAI  # lazy import: core loop/tests work without the SDK
        self.spec = spec
        self.client = OpenAI(base_url=spec.base_url, api_key=spec.api_key or "EMPTY")

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             temperature: float = 0.3) -> dict:
        kwargs: dict = dict(model=self.spec.name, messages=messages, temperature=temperature)
        if tools:
            kwargs["tools"] = tools
        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message.model_dump(exclude_none=True)
        msg.setdefault("content", "")
        return msg


class MockProvider:
    """Scripted provider for offline tests: pops one canned assistant message per call."""

    def __init__(self, script: list[dict]):
        self.script = list(script)
        self.calls: list[dict] = []

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             temperature: float = 0.3) -> dict:
        self.calls.append({"messages": messages, "tools": tools})
        if not self.script:
            return {"role": "assistant", "content": "(mock script exhausted)"}
        return self.script.pop(0)


def build_provider(spec: ModelSpec) -> ChatProvider:
    return OpenAICompatProvider(spec)