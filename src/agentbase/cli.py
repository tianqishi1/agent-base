"""CLI: agentbase agents | run | serve"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="agentbase", description="Config-driven agent foundation")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("agents", help="list available agents")

    p_run = sub.add_parser("run", help="run one turn of an agent")
    p_run.add_argument("message", help="user message")
    p_run.add_argument("--agent", default="assistant")
    p_run.add_argument("--session", default=None, help="session id to continue")

    p_serve = sub.add_parser("serve", help="start the HTTP API")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.cmd == "agents":
        from .config import load_agents
        specs = load_agents()
        if not specs:
            print("(no agents found; set AGENTBASE_AGENTS_DIR or create ./agents/*.yaml)")
        for s in specs.values():
            print(f"{s.name:20s} model={s.model.name:24s} {s.description}")
        return 0

    if args.cmd == "run":
        from .config import load_agents
        from .loop import AgentLoop
        specs = load_agents()
        if args.agent not in specs:
            print(f"unknown agent '{args.agent}'. available: {', '.join(specs) or '(none)'}",
                  file=sys.stderr)
            return 2
        result = AgentLoop(specs[args.agent]).run(args.message, args.session)
        print(result.reply)
        print(f"\n[session={result.session_id} steps={result.steps} "
              f"tools={len(result.tool_calls)}]", file=sys.stderr)
        return 0

    if args.cmd == "serve":
        import uvicorn
        uvicorn.run("agentbase.server:app", host=args.host, port=args.port)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
