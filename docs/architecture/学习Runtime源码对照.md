# Learning Runtime 外部源码对照

更新日期：2026-09-14

状态：**研究记录 / 可变结论**。

本文服务于 `学习Runtime演进方向.md`。它不是竞品功能清单，而是把 Learningflow 当前原型与外部项目针对同一个问题逐项比较：

```text
它怎么解决？
我们现在怎么解决？
谁的语义更严谨？
哪些值得直接借？
哪些只值得做实验？
哪些反而不适合 Learningflow？
```

这里的“借鉴”允许修改已经实现的代码、Tool Contract、Skill 和数据模型；现有实现不享有默认正确性。

## 1. 第一轮源码基线

本轮不是只读 README。已在本机独立 research cache 检出以下仓库并检查关键源码 / Skill：

| 项目 | 本轮检出 commit | 本轮重点 |
| --- | --- | --- |
| Engram | `0590eb8` | assessor、receipt、learn/review、deterministic engine |
| open-mastery | `2b6c156` | graph、frontier、student state、record_mastery |
| knowledge-graph-mcp | `2d39208` | node model、graph service、mastery、misconception、SM-2 |
| edu-agent-skills | `e75f443` | check-understanding、misconception-detector、learning-memory |
| open-cognition | `bd95d6f` | Skill、session、doubt、flashcard/review、MCP flows |
| Coding-Tutor / Traver | `d1fa15b` | knowledge tracing、turn-level verifier、candidate response selection |

这些项目成熟度差异很大。本轮只判断“某个机制是否值得借鉴”，不因为项目整体完整就提高其可信度。

---

## 2. Evidence 与评价：Engram 对当前原型提出了最直接的挑战

### 2.1 Learningflow 当前做法

当前已经有一些值得保留的事实保护：

```text
AssessmentRun
  → AssessmentItem.prompt
  → LearnerResponse.raw_answer
  → AssessmentRevision(result / reason / evaluation_method)
```

Transcript 路线还有额外约束：

```text
模型只返回 prompt_message_id / response_message_id
→ 程序验证消息角色和顺序
→ 程序按 ID 恢复原始题目与回答
```

因此模型不能把孩子原本回答的 `likes` 偷偷改成 `like`。

这是当前原型里应该保留的部分。

但当前也有明显不足：

1. 实时 `record_assessment_run` 允许教学 LLM 同时提交自己的 `result / reason`；
2. Transcript `Evidence Compiler` 当前同一次模型调用既负责选择哪些消息构成 Evidence，又负责给 `correct / incorrect / partial`；
3. `evaluation_method = llm` 只能说明“大模型评的”，不能回答是哪个 grader、是否独立、看过哪些教学上下文；
4. `AssessmentRevision` 虽然与原回答分表，但目前还没有形成“评价证据本身也可审计”的完整语义。

### 2.2 Engram 的关键方法

Engram 的关键不是它用了 FSRS，而是它把**教学权和评价权分开**：

```text
Tutor
  负责教学、提示、引导
        │
        ▼
learner production（原回答）
        │
        ▼
Blind Assessor
  只看 claim / rubric / probe / production
  不看教学对话
        │
        ▼
Receipt
        │
        ▼
deterministic engine
  更新 schedule / state
```

它的 assessor 明确要求：

- 不接受 Tutor 对课堂“进行得很好”的印象；
- 只按 rubric 和 learner production 评分；
- confidence 只能来自学习者明确自报，不能推断；
- receipt 带 grader 身份；
- receipt 用 `sid` 做 settle 幂等；
- audit receipt 不修改 schedule；
- engine 侧坚持 state 只能通过 receipt 推进。

其 target architecture 还进一步强调：receipt append-only，不允许回写重写历史评价。

### 2.3 对 Learningflow 的判断

**值得保留：**

- 原始题目 / 回答与评价分层；
- Transcript 通过 message id 锁定原文；
- idempotency；
- source quality / assistance level。

**应该进入 Candidate 的改进：**

1. 把“事实抽取”和“学习评价”拆成两个逻辑步骤；
2. Tutor 的即时判断可以保存，但不能默认等同于可信 learner-state input；
3. 增加独立 Assessor / post-hoc verifier 的实验；
4. 评价记录未来需要知道 `grader / evaluator identity / evaluation context`；
5. State Compiler 只消费满足最低可信条件的 evaluation receipt，而不是任意 `llm` 评价。

**暂时不要照搬：**

- Engram 的完整 receipt 字段；
- 成人自学场景中的 confidence / calibration 全套机制；
- 立即引入 FSRS；
- 为了“分权”强制每一道儿童练习都调用第二个 Agent，破坏实时体验。

### 2.4 最值得先做的低成本实验

利用我们已经有的 Transcript 路线，不需要先改实时教学：

```text
真实教学 Transcript
      │
      ├── A：当前 Compiler
      │      选择 Evidence + 自己评分
      │
      └── B：两阶段
             Selector 只选择 prompt/response
                    ↓
             Blind Assessor 只看题目、rubric、原回答
```

比较：

- A/B 正误判断分歧率；
- Tutor 自评与 blind assessor 分歧；
- 对明显错误、提示后正确、部分正确的差异；
- 是否出现“教学者过于乐观”的系统性偏差。

如果没有明显收益，不必为了架构纯洁性增加第二评价链；如果分歧明显，再升级 Contract。

---

## 3. Knowledge Graph：open-mastery 的结构值得借，但 mastery 语义不适合照搬

### 3.1 open-mastery 做得好的地方

它把两件事分得很清楚：

```text
Curriculum Graph
  YAML node / prereqs / assess / context

Student State
  node → mastery record
```

`Graph.get_frontier()` 的职责非常窄：

```text
节点自己未 mastered
+ 所有 prerequisite 已 mastered
= frontier candidate
```

更值得借的是：**graph 不替 LLM 决定最终下一课。**

它只告诉 LLM：

> 这些内容现在具备前置条件。

LLM 再结合兴趣、上下文等选择其中一个。

这与 Learningflow 的 ChatGPT-first 思路相容。

另外它把教学指导做成 prompt cascade：

```text
subject
→ domain
→ unit
→ node context
```

这比把每个知识点塞进一个巨大的系统提示更值得参考。

### 3.2 它不适合直接借的地方

`StudentState.record_mastery()` 接受：

```text
node_id + BloomLevel
```

然后直接写入 mastery，并据此解锁后继节点。

也就是说：

```text
外部 Agent 说 mastered
→ state 就 mastered
→ frontier 改变
```

没有 Evidence receipt 链。

对 Learningflow 而言，这比当前“Evidence 优先、State 可重算”的方向更弱。

### 3.3 对 Learningflow 的判断

**Candidate：**

- Subject Pack / Concept Graph 与 Learner State 分离；
- prerequisite DAG；
- frontier 只输出“可学候选”，不替 ChatGPT 做最终教学选择；
- 分层 prompt / pedagogical context cascade。

**不采用：**

- MCP 直接 `record_mastery` 作为长期事实源；
- “只要标记 mastered 就解锁”的无 Evidence 状态推进。

**开放问题：**

小学英语是否真的需要细粒度 DAG，仍需用真实教材和作业验证。可以先从 10–30 个强依赖关系的小图实验，而不是建立完整小学英语知识图谱。

---

## 4. knowledge-graph-mcp：字段设计有启发，但状态更新语义偏弱

### 4.1 值得看的部分

它把 mastery 拆成：

```text
recall
application
explanation
```

同时拥有：

```text
prerequisite
builds_on
related_to
contradicts
applies_to
parent_of
```

以及：

```text
ready_to_learn
due_for_review
struggling
stalled
misconceptions
knowledge_gaps
next_recommended
```

这些查询类型很适合反过来问我们：未来 `get_learning_context` 到底应该回答哪些问题。

### 4.2 不能直接照搬的部分

源码允许调用方直接更新：

```text
mastery_recall
mastery_application
mastery_explanation
mastery_level
quality
misconception_detected
```

overall mastery 使用固定权重：

```text
0.3 * recall
+ 0.4 * application
+ 0.3 * explanation
```

misconception 也是直接把字符串 append 到 node 上。

这几个设计对我们的风险是：

- 数值看起来精确，但来源不一定可追溯；
- 固定权重很容易制造“科学感强、证据弱”的 mastery；
- 一次 LLM 判断可能直接变成长期 misconception；
- graph node 同时承载课程事实、学生状态、复习状态，边界较混。

### 4.3 对 Learningflow 的判断

**Idea / Candidate：**

- 多维能力不要过早压成单一 mastery；
- `ready_to_learn / struggling / stalled / due` 这类 Runtime Query 值得参考；
- concept relation 可以不只 prerequisite。

**明确不作为当前方向：**

- 直接暴露 `update mastery` 给 LLM；
- 固定 `0.3/0.4/0.3` 权重；
- `misconception_detected="..."` 一次写入即成为长期事实。

---

## 5. Skill：当前单一 learningflow-tutor 太粗，但现在不应该机械拆成 20 个 Skill

### 5.1 Learningflow 当前做法

`learningflow-tutor` 目前同时包含：

```text
读取 Context
自然教学
Assessment
保留原答
评价
Evidence 持久化
Transcript 编译入口
```

作为 Stage 0，它的好处是简单、能跑。

问题是随着功能增加，容易变成“所有教学规则都堆在一个 SKILL.md”。

### 5.2 edu-agent-skills 值得借的不是数量，而是 routing

它把能力分成：

```text
teach-concept
check-understanding
misconception-detector
learning-memory
weak-area-tracker
spaced-repetition
...
```

更关键的是每个 Skill 明确：

```text
什么时候激活
什么时候跳过
依赖什么输入
失败后路由到哪里
什么条件下升级到另一个 Skill
```

其中 `misconception-detector` 明确要求：

- 重复错误模式；
- 或学习者解释暴露了错误 mental model；
- 单次执行错误不应进入 misconception；
- 先复述并确认错误模型，再纠正；
- 纠正后要用新场景验证。

这与 Learningflow 当前“错因只是候选假设”的原则高度一致，但它把操作闭环写得更完整。

### 5.3 需要拒绝的部分

`learning-memory` 示例 schema 里包含：

```text
learning_style: code-first | concept-first | mixed
```

这种 profile 很容易变成长期标签。Learningflow 当前不应因为一个 Skill 模板就把“学习风格”持久化成学生属性。

同样，20 个 Skill 是编码学习场景的方式，不代表儿童学习 Runtime 需要 20 个独立 Skill。

### 5.4 对 Learningflow 的判断

**短期保留单一 `learningflow-tutor`，但开始内部按能力边界组织：**

```text
Teach policy
Assessment policy
Diagnosis policy
Persistence policy
```

先把 routing / activation / escalation 条件写清楚。

只有当：

- 单一 Skill 已经明显过长；
- 不同协议需要独立触发；
- 宿主支持组合 Skill；
- 拆分能真实改善行为稳定性；

再物理拆成多个 Skill。

---

## 6. open-cognition：更值得借交互边界，而不是 learner-state

open-cognition 的强项不是严谨 Evidence，而是把长期学习体验的几个入口串得比较自然：

```text
Topic
Flashcard
Resource
Artifact
Doubt
Session Log
```

其 Skill 有一个很值得借的交互原则：

> **Socratic mode 和 system-management mode 不要混在一起。**

也就是孩子正在思考时，不要突然打断：

```text
“我现在要保存一条记录”
“请选择标签”
“是否要建立卡片”
```

对 Learningflow 更应该进一步：普通 Evidence 保存尽量后台完成，孩子甚至不应该知道数据库动作发生了。

另外 `Doubt` 作为一等对象有一定启发：

```text
孩子主动提出但尚未解决的问题
```

和：

```text
系统推断出的 misconception
```

不是同一类东西。

前者是事实，可以直接保存；后者是推断，需要验证。

### 对 Learningflow 的判断

**Candidate：**

- 教学交互与系统管理动作分离；
- Session 恢复时读取少量相关历史；
- `Doubt / Open Question` 与 misconception 分开；
- 当前会话有自然结束和 resume point。

**不直接采用：**

- 以 flashcard 作为核心 Evidence 单位；
- 由 Tutor 自己在 review 中决定 quality 后直接进入调度；
- Topic / Card / Artifact 产品模型整体照搬。

---

## 7. Coding-Tutor / Traver：Verifier 的另一个用途是评价“老师下一步说什么”

Traver 的 verifier 与 Engram assessor 解决的不是同一个问题。

其 Tutor 每一轮可以：

```text
Conversation
    ↓
Knowledge Tracing
    ↓
生成多个 Tutor response candidates
    ↓
Verifier 给 candidate 打分
    ↓
选择最高分回答给学生
```

也就是说 verifier 在这里用于：

> **挑选更好的教学动作。**

而不是只判断学生答对没有。

这对应 Learningflow 已经提出、但尚未实现的 Teaching Reflection / Tutor Evaluation。

### 对 Learningflow 的判断

当前不值得为了儿童日常教学让每一轮 ChatGPT 都生成 N 个回答再跑 verifier，成本和延迟都太高。

但它提供了一个更实际的演进路径：

```text
先离线分析 Transcript
→ 标记 Tutor 当时采取了什么策略
→ 评价这一轮是否与学生状态匹配
→ 再关联后续 Evidence
```

如果以后确实发现某类教学动作经常失误，再考虑少量关键节点的在线 verifier，而不是一开始就做多候选推理。

---

## 8. 第一轮之后，对当前 Learningflow 的具体修正假设

下面都还是 Candidate / Experiment，不是现在立即改表的 Decision。

### 8.1 Evidence Compiler 应优先实验“两阶段评价”

当前：

```text
Transcript
→ 一个模型同时选择 Evidence + 评分
```

候选：

```text
Transcript
→ Selector：只选 prompt / response ID
→ 程序锁定原文
→ Assessor：独立评价
```

这是第一优先级的架构实验。

### 8.2 `assessment.result` 暂时应理解为“评价记录”，不是 State Truth

即使来源是 LLM，也不能因为保存进 `assessment_revisions` 就自动获得长期事实地位。

未来可能需要区分：

```text
tutor_judgement
blind_assessor
deterministic
human
```

以及 evaluator / grader 的版本与身份。

### 8.3 Misconception 应建立生命周期，而不是一个标签

候选：

```text
observed_error
    ↓
hypothesis
    ↓
targeted_probe
    ↓
supported / rejected / uncertain
```

其中“重复错误后再启动诊断”“让学习者确认我们是否准确描述了他的错误想法”“用新场景验证”都值得进入未来 Diagnosis Protocol。

### 8.4 Concept Graph 与 Learner State 应保持物理和语义分离

如果未来加入 graph，更倾向：

```text
Subject / Curriculum Graph
        +
Evidence-derived Learner State
        ↓
Frontier Candidates
```

而不是 graph node 自己同时保存课程定义、学生 mastery、misconception 和 review schedule。

### 8.5 Frontier 应是候选生成器，不是教学决策器

Runtime 可以回答：

```text
现在有哪些内容满足前置条件？
```

ChatGPT 再结合：

```text
教材进度
学校作业
最近错误
兴趣 / 当前任务
到期复测
```

决定这一次学什么。

### 8.6 Skill 优先完善 routing，不急着增加 Skill 数量

第一步应该是把现有 Tutor Skill 内的边界写清楚，而不是立刻拆目录：

```text
什么时候只是 Teach
什么时候进入 Assessment
什么时候重复错误才进入 Diagnosis
什么时候结束 Diagnosis 回到 Teach
什么时候只后台保存，不打断学习者
```

### 8.7 Teaching Reflection 先离线，不先在线拦截

优先：

```text
Transcript
→ 教学动作分类 / verifier
→ 与后续 Evidence 对照
```

而不是：

```text
每一轮生成多个 Tutor 回答
→ verifier 选一个
```

只有离线证据证明在线控制有必要，才增加实时复杂度。

---

## 9. 第一轮明确“不借”的内容

研究的价值也包括排除。

目前明确不因为外部项目存在就采用：

- knowledge-graph-mcp 的固定 mastery 权重；
- 任意 LLM 直接写 mastery；
- 单次错误直接写长期 misconception；
- open-mastery 的 `record_mastery` 作为长期状态事实；
- edu-agent-skills 的 `learning_style` 长期标签；
- 为了模块化一次性拆出十几个 / 二十个 Skill；
- open-cognition 以 flashcard 为核心的数据模型；
- 当前阶段直接引入 SM-2 / FSRS；
- Traver 每轮多候选 + verifier 的在线高成本推理。

这些结论以后可以因新证据改变，但当前没有理由引入。

---

## 10. 下一轮研究问题

第一轮已经从“看项目”收缩出几个更具体的问题。下一轮应继续围绕问题，而不是项目数量：

1. Engram 的 receipt / state advancement 具体怎样落盘，哪些字段真正在 engine 中影响 state？
2. Blind Assessor 在儿童英语这种有确定答案 + 开放解释混合的场景，怎样与 deterministic grader 组合？
3. open-mastery 的 graph granularity 和 prompt cascade 是否适合小学英语教材映射？
4. knowledge-graph-mcp 的 `ready_to_learn / stalled / knowledge_gaps` 查询中，哪些可以不依赖数值 mastery 实现？
5. Misconception hypothesis 最小数据模型是什么，怎样避免把 LLM 猜测永久化？
6. Teaching Reflection 能否先完全从 Transcript 派生，而不增加实时 Tool？
7. Parent / Guardian 方向仍然缺少足够强的参考项目，需要单独继续搜索。

---

## 11. 专题深挖

第一轮总表之后，单个项目的细节不继续堆在本文。当前专题：

- [`research/Engram_Evidence与状态推进.md`](research/Engram_Evidence与状态推进.md)：继续检查 receipt / stash / state transition 后发现，Learningflow 当前更靠前的缺口不是 mastery 算法，而是 **Evidence event semantics**；尤其需要区分采集来源、教学事件类型、评价角色和是否允许影响 Learner State。
- [`research/Misconception与评价边界.md`](research/Misconception与评价边界.md)：第二轮按问题研究 Error / Doubt / Weak Area / Misconception 的边界，并继续讨论 deterministic grader、Tutor 自评、独立 Assessor 与多评价来源如何组合；未决项保留为“待讨论”。

