# agent-base：可复用的 Agent 底座

一个**轻量、配置驱动、可部署**的 agent 底座。以后想做任意 agent，只需要：

> **新 agent = 一个 YAML（人设 + 模型 + 工具清单） + 可选的一个 Python 工具文件**

不需要动内核。内核只有五层，全部可替换：

```
┌────────────────────────────────────────────────┐
│  接口层   CLI (agentbase run/serve) │ HTTP API │
├────────────────────────────────────────────────┤
│  编排层   AgentLoop：模型→工具→结果→…→最终回答  │
│           max_steps 护栏 / 会话续聊 / 步级trace │
├────────────────────────────────────────────────┤
│  工具层   @tool 装饰器 + 自动 JSON Schema       │
│           内置: 时间/计算器/文件沙箱/HTTP GET   │
├────────────────────────────────────────────────┤
│  模型层   OpenAI 兼容协议 → DeepSeek / 通义 /   │
│           OpenAI / Kimi / Ollama / vLLM 随便换  │
├────────────────────────────────────────────────┤
│  记忆层   sessions/*.json + traces/*.jsonl     │
└────────────────────────────────────────────────┘
```

## 快速开始（Windows / PowerShell）

```powershell
cd D:\codex\agent-base
python -m venv .venv
.\.venv\Scripts\pip install -e .
Copy-Item .env.example .env   # 填入你的 API key（DeepSeek 或 DashScope 至少一个）

.\.venv\Scripts\agentbase agents                     # 列出所有 agent
.\.venv\Scripts\agentbase run "现在几点？顺便算一下 365*24"
.\.venv\Scripts\agentbase run --agent translator "你好，世界"
.\.venv\Scripts\agentbase run --session <上次的session_id> "继续刚才的话题"
.\.venv\Scripts\agentbase serve --port 8000          # 启动 HTTP API
```

HTTP 调用：

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/chat -ContentType "application/json" -Body '{"agent":"assistant","message":"帮我算 2^10"}'
# GET /agents 查看可用 agent；POST /reload 热加载 YAML；GET /health 探活
```

## 如何新增一个 agent（核心用法）

1）在 `agents/` 下新建 `my_agent.yaml`：

```yaml
name: my_agent
description: 周报生成器
model:
  base_url: ${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}
  api_key_env: DEEPSEEK_API_KEY
  name: deepseek-chat
system_prompt: |
  你是一个周报助手，把零散记录整理成结构化周报……
tools: [current_time, read_file, write_file]   # "*" = 全部工具
tool_modules: ["../tools/my_tools.py"]         # 可选：自定义工具
temperature: 0.3
max_steps: 12
```

2）（可选）写自定义工具 `tools/my_tools.py`：

```python
from agentbase.tools import tool

@tool
def query_erp(order_id: str) -> str:
    """按订单号查询 ERP 订单状态。"""
    ...  # 你的业务逻辑 / 内部 API 调用
```

类型注解自动生成参数 schema，docstring 自动成为工具描述。
完整示例见 `examples/custom_tool_demo/`。

3）`agentbase run --agent my_agent "..."` 或 HTTP `/chat` 直接用；服务端 `POST /reload` 热加载。

## 换模型 / 换服务商

只改 YAML 的 `model` 三行，任何 OpenAI 兼容端点都行：

| 服务商 | base_url | 模型示例 |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 阿里百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` / `qwen-max` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen3:8b`（key 随便填） |
| 本地 vLLM | `http://localhost:8001/v1` | 你部署的模型 |

## 部署

```powershell
docker build -t agent-base .
docker run -d -p 8000:8000 --env-file .env -v agent_data:/data -v agent_ws:/workspace agent-base
```

- 会话与 trace 落在 `/data`，文件工具沙箱在 `/workspace`，挂卷即持久化。
- 新 agent 上线 = 改 YAML → 重新 build，或挂载 agents 目录 + `POST /reload`。
- 无 Docker 时：`agentbase serve` + nssm/计划任务/任意进程管理器即可。

## 设计约定

- **工具错误不炸循环**：异常变成 `ERROR: ...` 文本回传给模型，让它自己纠错。
- **max_steps 护栏**：防止工具死循环烧 token。
- **文件工具沙箱**：`read_file/write_file/list_dir` 被限制在 `AGENTBASE_WORKSPACE` 内，路径穿越直接拒绝。
- **全程可审计**：每一步 assistant 消息、工具入参/结果都写 `data/traces/<session>.jsonl`。
- **离线可测**：`MockProvider` 脚本化模型响应，`pytest` 不需要任何 API key。

## 测试

```powershell
.\.venv\Scripts\python -m pytest tests -v
```

## 路线图（按需再加，保持内核小）

- [ ] SSE 流式输出（`/chat/stream`）
- [ ] MCP 客户端（把外部 MCP server 的工具挂进 ToolRegistry）
- [ ] 多 agent 协作（sub-agent 作为工具调用）
- [ ] 长期记忆 / 向量检索（可接百炼知识库或本地 sqlite-vec）
- [ ] 鉴权与限流（上生产前加 API key 中间件）

## 选型背景（为什么自建而不是直接用现成 harness）

- **DeepSeek Harness**（MIT，TS，"Everything is a Plugin"）：理念最接近本底座，但处于 developer preview、官方警告破坏性变更；适合愿意跟上游跑的 TS 团队。
- **Codex harness**（openai/codex，Rust）：优秀的编码专用成品 agent，不是通用底座。
- **HKUDS OpenHarness / nanobot**（Python）：同类轻量底座，可作为参考实现对照。
- **AGX（港大 HKUDS，agx.cool）**：游戏竞技场 + RSI 学习平台，是"训练场"不是"底座"；本底座产出的 agent 未来可以包装成 AGX 参赛包去竞技场里进化。