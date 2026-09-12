# Learningflow

Learningflow 是一个服务于 ChatGPT 的长期学习运行系统。它不是再做一个 AI 学习产品，而是给 ChatGPT 补上单次对话不擅长长期承担的能力：学习事实、Evidence、状态、复习、调度、教学反思和专用交互。

一句话定位：

> **Learningflow = ChatGPT 的长期学习操作系统。**

首个落地学科是小学英语，但核心目标不是做一套“英语题库”，而是持续运行下面这条闭环：

```text
任务 → 作答 → 证据 → 诊断 → 教学 → 再练 → 延迟复测 → 学习状态更新
                                      ↓
                               教学反思与方法迭代
```

当前产品边界：

- **ChatGPT**：孩子侧主教学 Runtime，承担文字/语音教学、追问、出题、解释和教学决策；
- **Teaching Skills**：只在需要稳定流程纪律时约束 ChatGPT，例如一次一题、先答后评、区分提示前后作答；
- **Learningflow Server / MCP**：承担长期 Context、Evidence、状态、复习、调度、通知、报告与可追溯事实；
- **Learningflow Web**：不是默认学习入口，只在照片、复杂交互、录音、长文本或受控测验等 ChatGPT 本身不适合的场景按需出现；
- **PostgreSQL / 媒体存储**：保存长期学习事实与媒体证据。

最核心的数据方向是：

```text
Learning Context → ChatGPT → Learning Evidence
```

## 当前阶段

项目于 2026-09-12 正式建仓，目前处于 **Stage 0：产品基线与最小闭环验证准备**。

已经有第一个可运行的 Learning OS 内核：Python 包、Stage 0 SQLite 本地事实库，以及基于官方 MCP Python SDK v2 的两个核心工具：

```text
get_learning_context
record_assessment_run
```

它们分别负责把有限、相关的学习上下文交给 ChatGPT，以及把一小段真实问答可靠写回长期系统。当前还没有通用 Web 应用、OCR、Learner State Compiler 或后台 Worker。

### 本地运行

```bash
uv sync

# 只创建合成测试学生，不把真实学生资料写进 Git
uv run learningflow-admin ensure-student \
  --id child-test \
  --name 测试学生 \
  --mode test

# 默认 stdio MCP
uv run python -m learningflow.mcp_server
```

本地需要 Streamable HTTP 时：

```bash
LEARNINGFLOW_MCP_TRANSPORT=streamable-http \
LEARNINGFLOW_MCP_PORT=8000 \
uv run python -m learningflow.mcp_server
```

MCP 地址为 `http://127.0.0.1:8000/mcp`。当前 HTTP 模式只用于本机集成测试；在鉴权、数据范围和部署侧 transport security 完成前，不把真实学生数据暴露到公网。

### M0 Bridge 与 Codex-first

当前 ChatGPT 环境已经实际能够调用 DevSpace 这类 MCP / 插件工具，因此 Learningflow 不再按套餐名称预判 MCP 是否可用；自建 MCP 以后按真实 UI 与端到端工具调用验收。与此同时保留最低依赖的人工 Bridge：

```bash
# 把有限学习 Context 输出成可直接粘贴到 ChatGPT 的 packet
uv run learningflow-admin context-packet \
  --id child-test \
  --mode test \
  --focus "一般现在时"

# ChatGPT 按 chatgpt/PROJECT_INSTRUCTIONS.md 输出 Evidence JSON 后写回
uv run learningflow-admin record-packet --file evidence.json
```

`record-packet` 允许 Evidence Packet 省略 `idempotency_key`，Bridge 会根据包内容生成稳定 key，避免重复粘贴形成重复 Evidence。

Stage 0 也可以完全先在 Codex 中验证，不依赖 ChatGPT Web 接入：

```bash
# 查看本机 Codex 会话
uv run learningflow-admin codex-sessions --limit 20

# 导出一个标准化会话；只包含可见 user / assistant 文本
uv run learningflow-admin codex-transcript --latest

# 将 Codex 会话同步到本机 data/transcripts/codex/（该目录不进 Git）
uv run learningflow-admin sync-codex --limit 20

# 用 Codex 语义分析一段 Transcript，默认只生成待审 Evidence Packet
uv run learningflow-admin compile-codex \
  --session-id <session_id> \
  --student-id child-test \
  --mode test

# 明确确认后才写入 Learningflow
uv run learningflow-admin compile-codex \
  --session-id <session_id> \
  --student-id child-test \
  --mode test \
  --write
```

标准化格式为 `learningflow.transcript.v1`。后续 ChatGPT Web、浏览器同步器或其他 Agent 只需要实现同一个 Transcript Adapter，不改 Evidence 内核。

`compile-codex` 不允许模型重新生成孩子的原回答。Codex 只负责选择 `prompt_message_id / response_message_id` 并给出评价；Learningflow 再按消息 ID 从 Transcript 原样恢复题干和回答。默认 dry-run，只有显式 `--write` 才持久化。

仓库同时提供 `codex/skills/learningflow-tutor/SKILL.md`。安装到 Codex Skills 后，Codex 可以直接读取 Learningflow Context、执行一次一题的短验证，并通过本地 CLI 保存 Evidence。

下一步优先验证：

```text
Codex / ChatGPT 教学
→ Teaching / Assessment Protocol 进入短验证
→ 孩子直接回答
→ 实时 Tool 写入，或会话结束后由 Transcript Compiler 提取
→ Learning Evidence
→ 下一次 Context 能读到这次事实
```

普通问答默认不切网页。M0 再额外选择一个确实需要专用 UI 的 Activity，验证 Web 作为按需 Adapter 能顺利回到当前教学上下文。

## 文档入口

新任务先读：

1. [`PROJECT_STATE.md`](PROJECT_STATE.md) — 现在处于什么阶段、下一步做什么；
2. [`AGENTS.md`](AGENTS.md) — AI / 开发治理与文档路由；
3. [`docs/README.md`](docs/README.md) — 产品、架构、工程文档索引；
4. [`DECISIONS.md`](DECISIONS.md) — 长期关键决策及原因。

原始长对话和未收口研究材料保存在本机 `resources/raw/`，不进入 Git，也不作为现行事实源。
