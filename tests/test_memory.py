"""Session store: persistence, isolation, path safety."""
from agentbase.memory import SessionStore


def test_roundtrip_and_isolation(tmp_path):
    store = SessionStore(tmp_path)
    sid = store.new_session_id()
    assert store.load_history(sid) == []
    msgs = [{"role": "user", "content": "hello"}]
    store.save_history(sid, msgs)
    assert store.load_history(sid) == msgs
    assert store.load_history(store.new_session_id()) == []


def test_session_id_path_traversal_sanitized(tmp_path):
    store = SessionStore(tmp_path)
    store.save_history("../../escape", [{"role": "user", "content": "x"}])
    assert not (tmp_path.parent.parent / "escape.json").exists()
    assert list((tmp_path / "sessions").glob("*.json"))


def test_trace_appends_jsonl(tmp_path):
    import json
    store = SessionStore(tmp_path)
    store.trace("s1", {"step": 1})
    store.trace("s1", {"step": 2})
    lines = (store.root / "traces" / "s1.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["step"] for x in lines] == [1, 2]
    assert all("ts" in json.loads(x) for x in lines)
