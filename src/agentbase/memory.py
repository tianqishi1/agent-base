"""Session memory: chat history per session (JSON) + step traces (JSONL)."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path


class SessionStore:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or os.environ.get("AGENTBASE_DATA_DIR", "data"))
        (self.root / "sessions").mkdir(parents=True, exist_ok=True)
        (self.root / "traces").mkdir(parents=True, exist_ok=True)

    def new_session_id(self) -> str:
        return time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]

    def _sess_path(self, session_id: str) -> Path:
        safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self.root / "sessions" / f"{safe}.json"

    def load_history(self, session_id: str) -> list[dict]:
        p = self._sess_path(session_id)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return []

    def save_history(self, session_id: str, messages: list[dict]) -> None:
        self._sess_path(session_id).write_text(
            json.dumps(messages, ensure_ascii=False, indent=1), encoding="utf-8")

    def trace(self, session_id: str, event: dict) -> None:
        p = self.root / "traces" / f"{session_id}.jsonl"
        event = {"ts": time.time(), **event}
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")