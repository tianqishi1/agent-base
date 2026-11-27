"""HTTP interface tests with a stubbed agent loop (no model calls)."""
import pytest
from fastapi.testclient import TestClient

from agentbase import server
from agentbase.loop import RunResult


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBASE_AGENTS_DIR", str(tmp_path))
    (tmp_path / "a.yaml").write_text("name: stub\ndescription: test agent\n", encoding="utf-8")

    class StubLoop:
        def __init__(self, spec):
            self.spec = spec

        def run(self, message, session_id=None):
            return RunResult(reply=f"echo:{message}", session_id=session_id or "s1", steps=1)

    monkeypatch.setattr(server, "AgentLoop", StubLoop)
    with TestClient(server.app) as c:
        yield c


def test_health_and_agents(client):
    assert client.get("/health").json() == {"ok": True}
    names = [a["name"] for a in client.get("/agents").json()]
    assert names == ["stub"]


def test_chat_and_unknown_agent(client):
    r = client.post("/chat", json={"agent": "stub", "message": "hi"})
    assert r.status_code == 200
    assert r.json()["reply"] == "echo:hi"
    assert client.post("/chat", json={"agent": "nope", "message": "x"}).status_code == 404


def test_reload_picks_up_new_yaml(client, tmp_path):
    (tmp_path / "b.yaml").write_text("name: second\n", encoding="utf-8")
    r = client.post("/reload")
    assert set(r.json()["agents"]) == {"stub", "second"}
