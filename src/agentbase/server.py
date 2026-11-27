"""Interface layer: HTTP API (FastAPI). Run: uvicorn agentbase.server:app --port 8000"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import load_agents
from .loop import AgentLoop

app = FastAPI(title="agentbase", version="0.1.0")
_loops: dict[str, AgentLoop] = {}
_specs = {}


def _refresh() -> None:
    _specs.clear()
    _specs.update(load_agents())
    _loops.clear()


class ChatRequest(BaseModel):
    agent: str = "assistant"
    message: str
    session_id: str | None = None


@app.on_event("startup")
def _startup() -> None:
    _refresh()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/agents")
def agents() -> list[dict]:
    return [
        {"name": s.name, "description": s.description, "model": s.model.name,
         "tools": s.tools, "max_steps": s.max_steps}
        for s in _specs.values()
    ]


@app.post("/reload")
def reload_agents() -> dict:
    _refresh()
    return {"agents": list(_specs)}


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    if req.agent not in _specs:
        raise HTTPException(404, f"unknown agent '{req.agent}'. GET /agents for the list.")
    if req.agent not in _loops:
        _loops[req.agent] = AgentLoop(_specs[req.agent])
    result = _loops[req.agent].run(req.message, req.session_id)
    return {"reply": result.reply, "session_id": result.session_id,
            "steps": result.steps, "tool_calls": result.tool_calls}
