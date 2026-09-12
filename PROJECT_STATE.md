# Learningflow 当前状态

更新日期：2026-09-12

本文件只回答四件事：**当前阶段、已经确认什么、还没实现什么、下一步做什么**。历史讨论通过 Git、归档文档和本机 `resources/raw/` 追溯，不在这里堆积聊天流水。

## 1. 项目定位

```text
Learningflow
= 家庭侧长期学习运行系统
= 连续 Learning Evidence / 学习遥测
+ AI 教学与诊断
+ 作业监督、复习调度、家长通知
+ 教学反思与方法迭代
```

首个学科为小学英语。核心内核按跨学科设计，但首版不建设全学段知识图谱，也不同时实现多个学科。

## 2. 当前阶段

当前处于：

```text
Stage 0：正式建仓 + 产品基线 + 最小闭环验证准备
```

截至 2026-09-12：

- 已完成 Learningflow 本地 Git 仓库初始化；
- 已建立 `AGENTS.md / PROJECT_STATE.md / DECISIONS.md / docs/` 的文档治理基线；
- 已将前期长对话与原始思考移入本机 `resources/raw/`，避免继续作为项目根目录事实源；
- 已将两份建仓前设计收口为当前稳定入口：
  - `docs/product/真实学习流程.md`
  - `docs/architecture/系统架构.md`
- 已完成 M0 最小闭环实施基线：`docs/architecture/M0最小闭环设计.md`；当前基线为 ChatGPT-first，不选择任何开源项目作为母项目；
- 已确认 ChatGPT 是孩子侧主教学界面；Assessment Skill 约束短验证流程，Learningflow MCP/Server 保存长期事实，Web 只按需提供图片、复杂交互、录音等专用能力；
- 已形成最高层架构定位 `docs/architecture/长期学习操作系统.md`：Learningflow 以 `Context → ChatGPT → Evidence` 为核心数据回路，Teaching Skill 是逻辑协议，MCP/Tools 是长期 Runtime 的受控业务调用层；
- M0 不引入 LearnerState、BKT、FSRS、知识图谱或复杂诊断；
- 已创建第一个可运行 M0 Learning OS 内核：Python 包、SQLite Stage 0 本地事实库、官方 MCP Python SDK v2 Server；
- 已实现并验证两个核心 MCP 工具：`get_learning_context` 与 `record_assessment_run`；后者支持 `live / batch_verbatim / summary` 证据语义与幂等写入；
- 已通过自动测试验证 Evidence 写入/读取、Test/Real 边界、summary 不冒充逐字证据、答案 key/rubric 不进入 learner-safe Context；
- 已通过本机 Streamable HTTP 做真实 MCP Client 往返验证；测试后服务已关闭，测试端口不属于项目固定配置；
- 当前 Stage 0 本地事实库使用 SQLite，只用于最快验证 ChatGPT-first Contract；PostgreSQL 仍是后续长期运行候选，不把 SQLite 视为正式生产选型；
- 当前 ChatGPT 环境已经实际具备 MCP / 插件工具调用能力，DevSpace 即为已验证实例；Learningflow 自建 MCP 的具体连接方式以后按账号真实 UI、连接权限与端到端工具调用结果验收，不再按套餐名称预判可用性；
- Manual Bridge 仍作为最低依赖 fallback：`context-packet` 将有限 Context 带入 ChatGPT，`record-packet` 将 ChatGPT 生成的 Evidence Packet 写回 Learningflow；Teaching Protocol 模板位于 `chatgpt/PROJECT_INSTRUCTIONS.md`；
- 已完成 Manual Bridge 命令行真实往返验证：空 Context → 写入一条 `batch_verbatim` Evidence → 再次按 focus 查询能够读回原回答与 Assessment；
- 已实现 `CodexTranscriptAdapter`：只读取 Codex rollout 中可见的 user / assistant 文本，确定性排除 developer message、hidden reasoning、tool call 与 tool output；
- 已真实同步本机约 100 个 Codex 会话到忽略 Git 的 `data/transcripts/codex/`，统一格式为 `learningflow.transcript.v1`；再次全量同步全部 `unchanged`，同步路径已验证幂等；
- 已实现 Codex Evidence Compiler：模型只选择题目/回答的 message ID 并给出评价，程序按 ID 从 Transcript 原样恢复题干与孩子回答；默认 dry-run，显式 `--write` 才持久化；
- 已用合成英语短验证做真实 `codex exec + Structured Output` smoke：成功识别 `likes` 为错误、后续 `like` 为正确，同时 Evidence Packet 保留原始消息文本；
- 已增加 Codex-first 的 `learningflow-tutor` Skill，并安装到本机 `~/.codex/skills/learningflow-tutor/`；Codex 可以直接读取 Learningflow Context、按 Teaching Protocol 教学并写回 Evidence；
- 当前自动测试 15 项通过，覆盖 Learning Kernel、MCP、Manual Bridge、Transcript Adapter 与 Evidence Compiler 的关键边界；
- 尚未创建通用前端、OCR、Learner State Compiler、Worker、正式公网部署或 ChatGPT 原生可写 MCP 连接；FastAPI / React / PostgreSQL 等未实现部分仍不是运行事实。

## 3. 当前已经确认的产品原则

### 3.1 真实使用入口

- 孩子主要通过 **ChatGPT App** 接受讲解、追问、出题和互动，文字与语音都属于主路线；首版不自建实时语音老师。
- 普通 AI 追加题默认直接在 ChatGPT 中完成；Learningflow Web 只负责作业照片、复杂题型、长文本、录音和其他专用采集。
- 纸面学校作业继续保留纸笔流程，不要求为了让系统识别而重录整份作业。
- ChatGPT 对话与网页之间必须有明确交接；在自动工具链未实测前，允许结构化复制/粘贴作为可靠 fallback。

### 3.2 数据与学习判断

- **原始学习证据是长期资产；OCR、判分、诊断、掌握状态属于可重算的派生结果。**
- 原始记录、提取结果、分析判断、当前学习状态四类数据必须分开。
- “作业完成”“接受过教学”“当场答对”“独立掌握”“延迟保持”不能合并成一个状态。
- 错因是待验证假设，不因一道题自动扩散为整个知识点不会。
- 学习状态必须能回到具体证据；提示后答对不能冒充独立掌握证据。

### 3.3 长期运行

- 系统采用 **Server-first、客户端轻量** 的方向：长期记录、调度、复习、报告和通知不依赖 ChatGPT 当前是否在线。
- 首期通知只实现 **企业微信群 Webhook**；其他通知渠道不提前建设。
- 从第一阶段就区分测试空间与真实学生，避免测试数据污染真实长期记录。
- 教学反思与学生学习状态是两条不同反馈链：一个回答“孩子学得怎么样”，另一个回答“我们的教学方法效果怎么样”。

### 3.4 外部工具与内容来源

- 不预建、长期维护豆包、元宝、微信、抖音、小红书等完整固定连接器集合。
- 保留“**按任务发现外部能力**”的能力：需要时研究和选择当前可用的 MCP、插件、官方 API、搜索方式或其他合规接口。
- 工具使用经验可以记录，但过期能力需要重新验证；外部能力不可用不能阻塞作答保存、任务调度等核心流程。

## 4. 当前权威文档

产品：

```text
docs/product/产品基线.md
docs/product/真实学习流程.md
```

架构：

```text
docs/architecture/系统架构.md
docs/architecture/长期学习操作系统.md
docs/architecture/M0最小闭环设计.md
```

工程治理：

```text
AGENTS.md
docs/development/文档治理.md
docs/development/Git工作流.md
docs/development/项目管理.md
```

历史与原始证据：

```text
resources/raw/     # 本机保留，不进入 Git
docs/archive/      # 未来确有追溯价值的已失效正式文档
```

## 5. 下一步

优先顺序固定为：

```text
1. 先用 Codex 跑第一次真实 M0
   → `learningflow-tutor` 读取有限 Context
   → Codex 按 Teaching / Assessment Protocol 教学
   → 孩子直接文字作答，先验证教学与 Evidence 语义
   → Codex 直接写回结构化 Evidence
   → 用下一轮 Context 验证历史 Evidence 是否真正影响教学

2. 同时验证 Transcript 路线
   → Codex 本地 rollout 自动标准化
   → Transcript 分析 / Evidence 编译
   → 与实时写入结果对照

3. 再接 ChatGPT Web / App
   → 优先 MCP / Plugin 直接调用
   → 无法实时接入时使用聊天导出 / 同步器进入同一 Transcript Contract
   → 语音路径只要求能取得可靠转写或会话记录，不要求先取得原始音频

4. 只有遇到宿主本身不适合的活动，再实现第一个按需 Web Activity

5. 根据 M0 结果冻结首版长期存储与部署方式，再进入 M1：任务 + 学生隔离 + 作业照片 + OCR + 最小课程结构
```

当前不先搭空微服务、不先做完整知识图谱、不先建设固定外部连接器、不先实现复杂 mastery 算法。

## 6. 当前验收焦点

M0 只验证一件事：

> 孩子是否能较少依赖家长，始终以 ChatGPT 为主教学入口，完成“听讲 → 直接回答短验证 → 结构化保存关键 Evidence → 老师依据具体答案继续教学”的闭环。

如果普通问答必须频繁切网页、需要家长搬运题目或答案、工具调用破坏语音/文字连续性，则优先改 Skill / MCP 接入体验，不用后端复杂度掩盖产品问题。
