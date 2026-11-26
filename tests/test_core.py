"""Offline tests: no API key needed (MockProvider)."""
import json

import pytest

from agentbase.config import AgentSpec, ModelSpec, load_agents
from agentbase.loop import AgentLoop
from agentbase.memory import SessionStore
from agentbase.providers import MockProvider
from agentbase.tools import ToolRegistry
from agentbase import builtin_tools  # registers built-ins


@pytest.fixture(autouse=True)
def _dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBASE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AGENTBASE_WORKSPACE", str(tmp_path / "ws"))
    return tmp_path


def _spec(**kw) -> AgentSpec:
    base = dict(name="test", system_prompt="sys", tools=["*"], max_steps=6)
    base.update(kw)
    return AgentSpec(**base)


def _tc(name, args, cid="call_1"):
    return {"role": "assistant", "content": "",
            "tool_calls": [{"id": cid, "type": "function",
                            "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_tool_schema_from_hints():
    reg = ToolRegistry()

    @reg.register
    def greet(name: str, times: int = 1) -> str:
        """Say hello."""
        return "hi " + name * times

    s = reg.get("greet").schema()["function"]
    assert s["description"] == "Say hello."
    assert s["parameters"]["properties"]["name"]["type"] == "string"
    assert s["parameters"]["properties"]["times"]["type"] == "integer"
    assert s["parameters"]["required"] == ["name"]
    assert reg.call("greet", {"name": "a", "times": 2}) == "hi aa"


def test_calculator_and_sandbox():
    from agentbase.tools import registry
    assert registry.call("calculator", {"expression": "2+3*4"}) == "14"
    assert registry.call("calculator", {"expression": "__import__('os')"}) .startswith("ERROR")
    assert registry.call("write_file", {"path": "a.txt", "content": "hello"}) .startswith("written")
    assert registry.call("read_file", {"path": "a.txt"}) == "hello"
    assert registry.call("read_file", {"path": "../../etc/passwd"}).startswith("ERROR")


def test_loop_tool_flow_and_persistence():
    provider = MockProvider([
        _tc("calculator", {"expression": "6*7"}),
        {"role": "assistant", "content": "The answer is 42."},
    ])
    store = SessionStore()
    loop = AgentLoop(_spec(), provider=provider, store=store)
    result = loop.run("what is 6*7?")
    assert result.reply == "The answer is 42."
    assert result.steps == 2
    assert result.tool_calls[0]["result"] == "42"
    # history persisted: user, assistant(tool_call), tool, assistant(final)
    history = store.load_history(result.session_id)
    assert [m["role"] for m in history] == ["user", "assistant", "tool", "assistant"]
    # second turn continues the same session
    provider.script.append({"role": "assistant", "content": "Sure."})
    r2 = loop.run("thanks", session_id=result.session_id)
    assert r2.session_id == result.session_id
    assert len(store.load_history(result.session_id)) == 6
    # trace exists
    traces = list((store.root / "traces").glob("*.jsonl"))
    assert traces and traces[0].read_text(encoding="utf-8").strip()


def test_max_steps_guard():
    provider = MockProvider([_tc("current_time", {}, f"c{i}") for i in range(10)])
    loop = AgentLoop(_spec(max_steps=3), provider=provider)
    result = loop.run("loop forever")
    assert result.steps == 3
    assert "max_steps" in result.reply


def test_unknown_tool_returns_error_not_crash():
    provider = MockProvider([
        _tc("no_such_tool", {}),
        {"role": "assistant", "content": "recovered"},
    ])
    loop = AgentLoop(_spec(), provider=provider)
    result = loop.run("x")
    assert result.reply == "recovered"
    assert result.tool_calls[0]["result"].startswith("ERROR")


def test_env_interpolation(monkeypatch):
    monkeypatch.setenv("MY_MODEL", "qwen-max")
    spec = AgentSpec.from_dict({
        "name": "t",
        "model": {"name": "${MY_MODEL}", "base_url": "${MISSING_URL:-http://localhost:11434/v1}"},
    })
    assert spec.model.name == "qwen-max"
    assert spec.model.base_url == "http://localhost:11434/v1"


def test_load_shipped_agents():
    specs = load_agents("agents")
    assert "assistant" in specs and "translator" in specs
    assert specs["translator"].tools == []


def test_custom_tool_module(tmp_path):
    mod = tmp_path / "extra.py"
    mod.write_text(
        "from agentbase.tools import tool\n"
        "@tool\n"
        "def shout(text: str) -> str:\n"
        "    \"\"\"Uppercase text.\"\"\"\n"
        "    return text.upper()\n", encoding="utf-8")
    spec = _spec(tools=["shout"], tool_modules=[str(mod)])
    provider = MockProvider([
        _tc("shout", {"text": "hey"}),
        {"role": "assistant", "content": "done"},
    ])
    loop = AgentLoop(spec, provider=provider)
    result = loop.run("shout hey")
    assert result.tool_calls[0]["result"] == "HEY"
    # whitelist respected: only 'shout' offered to the model
    offered = [t["function"]["name"] for t in provider.calls[0]["tools"]]
    assert offered == ["shout"]