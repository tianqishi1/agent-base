"""Provider layer tests: no network, no API key."""

from agentbase.config import ModelSpec
from agentbase.providers import MockProvider, build_provider


def test_client_timeout_and_retries(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "sk-test")
    spec = ModelSpec(name="m", base_url="http://localhost:9/v1", api_key_env="TEST_KEY",
                     timeout_s=7.5, max_retries=4)
    provider = build_provider(spec)
    assert provider.client.timeout == 7.5
    assert provider.client.max_retries == 4


def test_spec_defaults_and_yaml_knobs():
    from agentbase.config import AgentSpec
    spec = AgentSpec.from_dict({"name": "t", "model": {"timeout_s": 12, "max_retries": 0}})
    assert spec.model.timeout_s == 12.0
    assert spec.model.max_retries == 0
    default = AgentSpec.from_dict({"name": "t"})
    assert default.model.timeout_s == 60.0
    assert default.model.max_retries == 2


def test_mock_provider_records_and_exhausts():
    mp = MockProvider([{"role": "assistant", "content": "one"}])
    assert mp.chat([{"role": "user", "content": "hi"}])["content"] == "one"
    assert "exhausted" in mp.chat([])["content"]
    assert len(mp.calls) == 2


def test_api_key_missing_falls_back(monkeypatch):
    monkeypatch.delenv("NO_SUCH_KEY_ENV", raising=False)
    spec = ModelSpec(api_key_env="NO_SUCH_KEY_ENV")
    assert spec.api_key == ""
    provider = build_provider(spec)  # must not raise without a key
    assert provider.client.api_key == "EMPTY"
