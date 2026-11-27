"""Agent definitions: load YAML specs, interpolate env vars.

A new agent = one YAML file in the agents dir. Example:

    name: assistant
    description: General assistant
    model:
      base_url: ${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}
      api_key_env: DEEPSEEK_API_KEY
      name: deepseek-chat
    system_prompt: |
      You are a helpful assistant.
    tools: ["*"]          # or a whitelist: [current_time, calculator]
    tool_modules: []      # optional python files with extra @tool functions
    temperature: 0.3
    max_steps: 12
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")


def _interpolate(value):
    if isinstance(value, str):
        def sub(m):
            return os.environ.get(m.group(1), m.group(2) if m.group(2) is not None else "")
        return _ENV_RE.sub(sub, value)
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    return value


@dataclass
class ModelSpec:
    name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/v1"
    api_key_env: str = "DEEPSEEK_API_KEY"
    timeout_s: float = 60.0
    max_retries: int = 2

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


@dataclass
class AgentSpec:
    name: str
    description: str = ""
    system_prompt: str = "You are a helpful assistant."
    model: ModelSpec = field(default_factory=ModelSpec)
    tools: list[str] = field(default_factory=lambda: ["*"])
    tool_modules: list[str] = field(default_factory=list)
    temperature: float = 0.3
    max_steps: int = 12
    source_path: Path | None = None

    @classmethod
    def from_dict(cls, raw: dict, source_path: Path | None = None) -> "AgentSpec":
        raw = _interpolate(raw)
        model_raw = raw.get("model") or {}
        model = ModelSpec(
            name=model_raw.get("name", "deepseek-chat"),
            base_url=model_raw.get("base_url", "https://api.deepseek.com/v1"),
            api_key_env=model_raw.get("api_key_env", "DEEPSEEK_API_KEY"),
            timeout_s=float(model_raw.get("timeout_s", 60.0)),
            max_retries=int(model_raw.get("max_retries", 2)),
        )
        return cls(
            name=raw["name"],
            description=raw.get("description", ""),
            system_prompt=raw.get("system_prompt", "You are a helpful assistant."),
            model=model,
            tools=raw.get("tools", ["*"]),
            tool_modules=raw.get("tool_modules", []),
            temperature=float(raw.get("temperature", 0.3)),
            max_steps=int(raw.get("max_steps", 12)),
            source_path=source_path,
        )


def load_agent(path: str | Path) -> AgentSpec:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return AgentSpec.from_dict(raw, source_path=path)


def load_agents(agents_dir: str | Path | None = None) -> dict[str, AgentSpec]:
    agents_dir = Path(agents_dir or os.environ.get("AGENTBASE_AGENTS_DIR", "agents"))
    specs: dict[str, AgentSpec] = {}
    if not agents_dir.exists():
        return specs
    for p in sorted(agents_dir.glob("*.yaml")) + sorted(agents_dir.glob("*.yml")):
        spec = load_agent(p)
        specs[spec.name] = spec
    return specs
