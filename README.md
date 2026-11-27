# agent-base — a reusable, config-driven agent foundation

[![ci](https://github.com/tianqishi1/agent-base/actions/workflows/ci.yml/badge.svg)](https://github.com/tianqishi1/agent-base/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

English | [简体中文](README_CN.md)

A **minimal, config-driven, deployable** foundation for building LLM agents.

> **A new agent = one YAML file (persona + model + tool list) + an optional Python tool file.**
> No kernel changes needed.

**Ecosystem**: foundation agent-base · evaluation [eval-pipeline](https://github.com/tianqishi1/eval-pipeline) · skills [marketing-skills-cn](https://github.com/tianqishi1/marketing-skills-cn) · example apps [afterpilot](https://github.com/tianqishi1/afterpilot) / [heng-erp](https://github.com/tianqishi1/heng-erp) / [pregnancy-butler](https://github.com/tianqishi1/pregnancy-butler)

## Architecture (5 replaceable layers)

```
Interface    CLI (agentbase run/serve) | HTTP API (FastAPI)
Orchestration AgentLoop: model -> tool calls -> results -> ... -> final answer
              max_steps guard / session resume / per-step traces
Tools        @tool decorator + auto JSON Schema from type hints
              built-ins: time / calculator / sandboxed files / HTTP GET
Model        any OpenAI-compatible endpoint: DeepSeek / Qwen (DashScope) /
              OpenAI / Kimi / Ollama / vLLM — swap via YAML
Memory       sessions/*.json + traces/*.jsonl
```

## Quickstart

```bash
git clone https://github.com/tianqishi1/agent-base.git && cd agent-base
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env    # add at least one API key (DeepSeek or DashScope)

agentbase agents                      # list agents
agentbase run "What time is it? Also compute 365*24"
agentbase run --agent translator "Hello, world"
agentbase run --session <session_id> "continue the previous topic"
agentbase serve --port 8000           # HTTP API
```

HTTP:

```bash
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" \
  -d '{"agent":"assistant","message":"compute 2^10"}'
# GET /agents | POST /reload (hot-reload YAML) | GET /health
```

## Define a new agent

1) Create `agents/my_agent.yaml`:

```yaml
name: my_agent
description: Weekly report generator
model:
  base_url: ${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}
  api_key_env: DEEPSEEK_API_KEY
  name: deepseek-chat
  timeout_s: 60        # per-request timeout
  max_retries: 2       # SDK retries connection errors / 429 / 5xx with backoff
system_prompt: |
  You turn scattered notes into a structured weekly report...
tools: [current_time, read_file, write_file]   # "*" = all tools
tool_modules: ["../tools/my_tools.py"]         # optional custom tools
temperature: 0.3
max_steps: 12
```

2) (Optional) custom tools in `tools/my_tools.py`:

```python
from agentbase.tools import tool

@tool
def query_erp(order_id: str) -> str:
    """Look up an ERP order status by order id."""
    ...  # your business logic
```

Type hints become the parameter JSON Schema; the docstring becomes the tool
description. Full example: `examples/custom_tool_demo/`.

3) Run it: `agentbase run --agent my_agent "..."`, or `POST /chat`. Hot-reload with `POST /reload`.

## Swap models / providers

Only the `model` block changes — any OpenAI-compatible endpoint works:

| Provider | base_url | example model |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Aliyun DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` / `qwen-max` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| Ollama (local) | `http://localhost:11434/v1` | `qwen3:8b` (any key) |
| vLLM (local) | `http://localhost:8001/v1` | your deployed model |

## Deploy

```bash
docker build -t agent-base .
docker run -d -p 8000:8000 --env-file .env -v agent_data:/data -v agent_ws:/workspace agent-base
```

Sessions/traces persist in `/data`; file tools are sandboxed to `/workspace`.
Ship a new agent by editing YAML and rebuilding, or mount the agents dir and `POST /reload`.

## Design guarantees

- **Tool errors never crash the loop**: exceptions become `ERROR: ...` text so the model can self-correct.
- **max_steps guard** against tool loops burning tokens.
- **Sandboxed file tools**: path traversal outside `AGENTBASE_WORKSPACE` is rejected.
- **Auditable**: every assistant message and tool call is traced to `data/traces/<session>.jsonl`.
- **Timeouts & retries**: per-request `timeout_s` and SDK-level exponential-backoff retries (`max_retries`).
- **Offline-testable**: `MockProvider` scripts model responses; the full test suite needs no API key.

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q       # offline tests
ruff check src tests      # lint
```

## Roadmap (keep the kernel small)

- [ ] SSE streaming (`/chat/stream`)
- [ ] MCP client (mount external MCP server tools into the registry)
- [ ] Multi-agent collaboration (sub-agents as tools)
- [ ] Long-term memory / vector retrieval
- [ ] Auth & rate limiting middleware

## License

Apache-2.0. See [LICENSE](LICENSE).
