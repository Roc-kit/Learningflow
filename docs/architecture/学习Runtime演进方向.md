# Learning Runtime 演进方向

更新日期：2026-09-14

状态：**探索性工作基线（Working Direction）**。

本文不是 Learningflow 的最终架构说明，也不是现有实现的辩护文档。它用于把三类信息放在同一张图上持续比较：

```text
我们的当前原型
    +
外部项目已经探索过的方法
    +
真实儿童学习中的使用结果
    ↓
不断修正 Learningflow
```

当前 Learningflow 仍处于很早期阶段。已经写出的代码、MCP Contract、Evidence 结构、Teaching Skill 和 ChatGPT-first 路线，都只能视为**当前最小实验方案**。它们可以被保留、扩展、重构，必要时也可以被外部项目的更好方法或真实使用结果推翻。

只有经过源码验证、原型比较、真实学习效果验证后形成稳定约束的内容，才升级到 `长期学习操作系统.md`、`系统架构.md` 或 `DECISIONS.md`。

---

## 1. 先明确：我们现在并没有一个成熟的 Learning Runtime

Learningflow 目前已经有了一些可运行部件，但还不能把这些部件等同于“正确架构”。

### 1.1 已经存在的技术原型

目前已经做出的主要原型包括：

```text
ChatGPT / Codex 作为教学宿主
        │
        ├── Teaching / Assessment Protocol
        │
        ├── get_learning_context
        │
        ├── record_assessment_run
        │
        ├── Transcript Adapter
        │
        ├── Evidence Compiler
        │
        └── SQLite Evidence Store
```

已经有对应代码、测试或本机 smoke 的部分包括：

- `get_learning_context`；
- `record_assessment_run`；
- `live / batch_verbatim / summary` 不同 Evidence capture 语义；
- Codex Transcript 标准化；
- 模型只选择 message id、程序恢复原文的 Evidence Compiler；
- `learningflow-tutor` Skill；
- Test / Real 数据隔离的初步约束；
- 原始回答与模型评价分离的初步数据模型。

这些成果证明：

> **这条技术路线可以跑起来。**

但它们还没有证明：

> **这就是最合适的长期 Learning Runtime。**

### 1.2 当前真正验证过的范围很窄

目前更多是工程和语义层验证：

```text
工具能否调用
数据能否保存
Transcript 能否标准化
原回答能否不被模型篡改
Evidence 能否重新读回
测试数据能否与真实数据隔离
```

以下关键问题基本都还没有通过长期真实使用证明：

```text
孩子是否愿意长期这样使用
ChatGPT-first 是否真的降低家长负担
当前 Context 是否足够帮助下一次教学
当前 Evidence 粒度是否合适
Assessment Protocol 是否自然
一次问答应该怎样影响长期状态
错因怎样确认而不是臆测
什么时候应该复习
课程关系需要多复杂
怎样判断一种教学方法比另一种更有效
```

所以后续不能形成这种思维：

```text
我们已经把基础做对了
→ 外部项目只填我们没有的功能
```

更合理的是：

```text
我们已经有一个最小可运行假设
→ 用外部项目和真实使用共同审查它
→ 哪些合理就保留
→ 哪些不足就完善
→ 哪些方向错误就替换
```

---

## 2. 当前应该同时保留三种证据来源

### 2.1 我们自己的原型

价值在于：

- 可以直接跑；
- 能快速暴露真实集成问题；
- 与我们自己的 ChatGPT-first 使用目标紧密相关；
- 可以用真实孩子学习过程验证。

缺点是：

- 设计历史很短；
- 很多模块只是第一种能工作的实现；
- 缺少长期学习数据；
- 缺少成熟 learner-model / knowledge-tracing / review 经验。

因此“已经实现”只能说明试验成本低，不能自动提高架构优先级。

### 2.2 外部项目和研究实现

价值在于：

- 已经有人尝试过 mastery、misconception、prerequisite、review、verifier 等问题；
- 能看到不同设计的真实数据模型和算法边界；
- 可以帮助我们少走一部分重复探索；
- 有些项目在某个子问题上可能明显比我们成熟。

外部项目不只是用于补充“尚未实现的模块”。它们也应该用于重新检查我们已经写出的东西，例如：

```text
Evidence 模型是否过于扁平？
Assessment Run 的边界是否合理？
Context Packet 是否应该包含别的状态？
Misconception 是否应独立建模？
Skill 是否太重或太轻？
MCP 是否应该暴露不同业务动作？
Transcript 是否应该成为正式 Evidence 来源？
我们当前的 source_quality / assistance_level 是否足够？
```

### 2.3 真实学习结果

这是最终权重最高的一层。

如果某种设计在开源项目里很完整，但实际让孩子使用更复杂、家长负担更大、教学更机械，就不应该因为“架构漂亮”而采用。

反过来，如果我们自己的简单方案在真实使用中效果很好，也没有必要为了贴近成熟 ITS 架构而增加复杂度。

因此长期判断顺序应当是：

```text
外部方法提供候选
        ↓
结合我们的产品目标做最小原型
        ↓
真实学习中验证
        ↓
再决定是否成为长期架构
```

---

## 3. 当前大方向仍然成立，但它本身也是待验证假设

目前最有希望的总体分工仍然是：

> **通用大模型负责教学智能，Learningflow 负责长期学习 Runtime。**

也就是尽量让 ChatGPT / Codex 负责：

```text
自然对话
讲解
追问
举例
生成练习
临场判断
根据回答换一种讲法
```

Learningflow 更偏向负责：

```text
学习事实
长期状态
知识关系
复习调度
教学约束
上下文选择
教学反思
跨会话连续性
```

这个方向目前看起来合理，也与我们已经实现的原型相容，但仍需要外部项目和真实使用持续检验。

特别是以下边界都不是最终结论：

- 多少诊断应该交给 LLM，多少应该进入 Runtime；
- Skill 应该只是协议，还是需要更强状态机；
- Learner State 应该多结构化；
- Concept Graph 是否值得成为核心；
- Review 是 Runtime 主动调度，还是由模型按 Context 判断；
- Transcript 在长期系统中应是 fallback，还是正式一等输入源。

---

## 4. 把当前原型和外部方法放到同一个能力矩阵

后续不是“我们有什么 + 别人补什么”，而是逐块比较谁的方法更合理。

| 能力 | Learningflow 当前状态 | 外部项目可借鉴点 | 当前判断 |
| --- | --- | --- | --- |
| 教学宿主 | 已尝试 ChatGPT / Codex-first | Edu Agent Skills、Claude Teacher Plugin、Learn FASTER Kit 的 Skill / Agent 接入方式 | **已有原型，但边界仍需比较** |
| Context | 已有 `get_learning_context` 的最小 Contract | learner profile、frontier、due review、misconception 如何进入 Context | **很初步** |
| Assessment 流程 | 已有一次一题、先答后评、记录提示的协议 | 其他 Tutor 的 Socratic、scaffolding、mastery check 流程 | **很初步** |
| Evidence | 已有 AssessmentRun / Item / Response / Revision 与 Transcript 路线 | Engram 的 evidence receipt、Verifier 系统、其他项目 evidence log | **当前重点比较对象** |
| Learner State | 尚未正式实现 | knowledge-graph-mcp、LearnGraph、open-mastery 等 | **待设计** |
| Mastery 更新 | 尚未实现 | Engram、open-mastery、knowledge tracing 项目 | **待研究** |
| Misconception | 目前主要停留在模型诊断 / 候选概念 | knowledge-graph-mcp、Coding-Tutor / Traver | **待设计** |
| Concept / Prerequisite | 只有产品层面的“最小课程映射”设想 | open-mastery、LearnGraph、knowledge-graph-mcp | **待验证必要性和粒度** |
| Review | 尚未实现 | SM-2 / FSRS 项目、open-cognition、Engram | **待实验，算法不预设** |
| Session / 长期记录 | 已有最小 Session / Transcript / Evidence 思路 | open-cognition 等长期 session 模型 | **可能需要重构** |
| Teaching Reflection | 产品需求已确认，尚未实现 | TutorGym、Tutor evaluation 研究 | **长期重要，仍很早期** |
| Parent / Guardian | 产品需求存在，未形成成熟实现 | 后续继续寻找更贴近家庭学习的项目 | **明显缺口** |

这张表要随着源码审计和真实使用持续修改。

---

## 5. 当前最值得研究的七类机制

下面这些不是“下一步必须实现的七个模块”，而是外部项目反复出现、值得用来审查我们现有设计的七类机制。

### 5.1 Evidence-driven learning

这是目前最重要的研究主线之一。

我们当前已经强调原始作答不能被 mastery 结论替代，但还没有成熟回答：

```text
什么算强 Evidence？
什么算弱 Evidence？
提示后答对如何处理？
同一知识点连续答对几次意味着什么？
延迟回答的权重怎样变化？
迁移题是否应独立记录？
```

Engram 等项目的价值，在于帮助我们完善甚至重构现有 Evidence 模型，而不只是提供未来 mastery 算法。

### 5.2 Learner State / Mastery

目前我们有一个强原则：State 不能代替 Evidence。

但这还远远不等于已经设计好了 State。

需要比较：

```text
单一 mastery 分数
多维 mastery
状态枚举
证据摘要
recall / application / explanation 分离
confidence / uncertainty
最后独立验证时间
```

最终可能非常简单，也可能需要更丰富结构；现在不预设。

### 5.3 Misconception / Knowledge Tracing

目前 Learningflow 只明确了：

> 错误答案 ≠ 已确认错因。

还没有成熟机制来把：

```text
模型猜测
→ 待验证假设
→ 设计区分题
→ 新 Evidence
→ 确认 / 否定
```

真正做成闭环。

Coding-Tutor / Traver、knowledge-graph-mcp 等项目应该用于帮助我们完善这一层。

### 5.4 Concept / Prerequisite / Frontier

目前我们还没有证明一定需要完整 Knowledge Graph。

但外部项目反复出现：

```text
prerequisite
mastery gate
frontier
ready_to_learn
learning path
```

这提示我们不能只把课程结构理解为教材章节目录。

需要通过真实小学英语场景判断：

- 简单标签是否足够；
- 只维护少量 prerequisite 是否足够；
- frontier 是否真的能改善“下一步学什么”；
- 图谱维护成本是否超过收益。

### 5.5 Review / Delayed Check

我们目前甚至还没到选择 FSRS 还是 SM-2 的阶段。

更基本的问题是：

```text
哪些知识需要进入复测？
复测的单位是什么？
由谁决定到期？
复测结果怎样反馈 State？
学校作业本身是否已经构成一部分复习？
```

外部项目中的 SRS 算法、due card 模型和值得借鉴，但不能直接当成答案。

### 5.6 Teaching Skill / Runtime Policy

我们现在的 Assessment Protocol 只是第一版。

外部 Skill / Tutor 项目可以帮助回答：

- 哪些教学动作必须强约束；
- 哪些交给模型自然发挥更好；
- 什么时候进入 Assessment；
- 什么时候应该退出；
- 是否需要显式 state machine；
- Skill 怎样读取和写回长期状态而不过度控制模型。

所以 `learningflow-tutor` 也属于研究对象，而不是已经完成的答案。

### 5.7 Teaching Reflection

我们已经把教学反思列为长期需求，但目前只是产品方向。

TutorGym 等项目提示我们可以把：

```text
使用了什么教学策略
→ 学生当场表现
→ 后续延迟表现
→ 同类知识点上的效果
```

联系起来。

但如何避免过度归因、怎样控制变量、需要多少样本，目前都没有答案。

---

## 6. 当前重点参考项目：不是“抄模块”，而是“拿来挑战我们的设计”

以下项目暂时作为第一轮源码审计对象。项目能力本身仍需逐项验证，不把前期 AI 搜索摘要直接当事实。

| 项目 | 优先研究的问题 | 可能影响 Learningflow 哪一层 |
| --- | --- | --- |
| Engram | Evidence receipt、free recall、mastery 更新、FSRS 接口 | **可能修改现有 Evidence 语义和未来 State Compiler** |
| open-mastery | DAG、mastery gate、frontier、teacher/student MCP | **可能修改课程结构、Context 和下一步决策模型** |
| knowledge-graph-mcp | concept relation、multi-dimensional mastery、misconception、review | **可能影响 State 数据模型和 Context Contract** |
| Edu Agent Skills | 教学 Skill 如何挂到通用 Agent Runtime | **直接对照现有 `learningflow-tutor` 和 Assessment Protocol** |
| open-cognition | session、doubt、flashcard、review、持久化结构 | **可能影响 Session / learner memory / review 设计** |
| Coding-Tutor / Traver | verifier、knowledge tracing、turn-level diagnosis | **可能影响 Evidence Compiler 和 misconception 验证流程** |
| TutorGym | tutor 行为评估、simulated learner、step-level feedback | **可能影响未来 Teaching Reflection / Tutor evaluation** |

第二梯队继续保留 LearnGraph、Learnify、EduGlow、EduAdapt AI、LearnKit、Learn FASTER Kit、Claude Teacher Plugin 等。如果源码显示某个机制更完整，可以随时提升优先级。

---

## 7. 源码审计时同时审查“别人”和“我们”

后续每研究一个项目，不只回答“它有什么”，还要回答：

```text
1. 它解决的问题，我们当前是否已经遇到？
2. 我们现在是怎么处理的？
3. 它的方法与我们的区别是什么？
4. 哪种方法的数据语义更严谨？
5. 哪种方法更适合 ChatGPT-first 的儿童学习场景？
6. 借鉴它需要增加多少复杂度？
7. 能否只吸收其中一个小机制？
8. 是否应该修改现有数据模型 / Tool Contract / Skill？
9. 是否值得做一个 A/B 原型或真实学习实验？
10. 最终结论属于 Idea、Candidate 还是 Decision？
```

同时对每个外部项目至少核实：

```text
长期数据到底保存了什么
Evidence 与 State 是否分开
mastery 实际怎么更新
misconception 如何产生和确认
graph 是否真的参与运行时决策
review 的输入与输出是什么
LLM 与 Runtime 如何分工
Skill / MCP / Tool 如何组织
README 描述与代码实现是否一致
```

---

## 8. 研究结论仍然分三级，但原型本身也不能跳级

```text
Idea
  看到一个值得研究的方法，尚未证明适合 Learningflow

Candidate
  已完成源码确认，并通过我们自己的小原型或真实场景证明有价值

Decision
  已形成长期选择，进入主架构文档 / DECISIONS.md
```

需要特别强调：

> **“Learningflow 已经实现”不等于 Candidate，更不等于 Decision。**

现有代码如果只是为了 M0 跑通最短路径，它仍可能只是一个实现中的 Idea / Prototype。

---

## 9. 当前合理的演进方式

不是：

```text
M0 已经把底座做完
→ M1 加 Learner State
→ M2 加 Graph
→ M3 加 Review
```

而更像：

```text
当前最小原型
      │
      ├── 跑真实学习
      │
      ├── 审计外部成熟方法
      │
      └── 对照发现问题
              │
              ▼
       修改当前原型
              │
              ▼
      再跑真实学习
              │
              ▼
      逐步形成稳定 Runtime
```

因此未来完全可能发生：

- Evidence 表结构调整；
- Assessment Protocol 重写；
- Context Contract 增删字段；
- Transcript 路线从 fallback 升级为正式入口；
- 某些 MCP 工具合并或拆分；
- Learner State 比预期更早出现；
- Knowledge Graph 比预期更晚，甚至不做完整版本；
- Review 只采用简单规则，而不引入复杂算法；
- 某个外部项目的单一机制成为我们的关键组成部分。

这些都不属于“推翻项目”，而是早期产品正常演进。

---

## 10. 当前不钉死的开放问题

接下来所有研究，优先帮助回答下面这些问题：

1. 我们现在的 Evidence 模型是否足够表达真实学习过程？
2. 当前 `AssessmentRun → Item → Response → Revision` 是否应该调整？
3. Context 最小需要哪些信息，才能真实改善下一次教学？
4. Learner State 最小应保存什么，哪些只应即时推断？
5. mastery 应该怎样由不同强度 Evidence 更新？
6. misconception 怎样从 LLM 猜测变成可验证、可撤销的状态？
7. Concept / prerequisite 需要做到什么粒度才值得维护？
8. `frontier` 是否真正优于“教材范围 + 最近弱项 + 到期复测”？
9. Review 应该使用简单规则、FSRS 类算法还是模型决策的组合？
10. Teaching Skill 需要多少显式状态机？
11. Transcript、实时 Tool、作业图片等不同来源怎样统一 Evidence 质量？
12. Teaching Reflection 最少需要记录哪些教学动作，才能形成可靠反馈？
13. Parent / Guardian 参与应该放在哪里，怎样减少而不是增加家长操作？
14. ChatGPT-first 本身是否在真实长期使用中成立？

这些问题没有预设答案，也允许反过来修改当前原型。

---

## 11. 当前阶段真正要避免的两种极端

第一种极端：

> **因为我们已经写了代码，就默认自己的设计已经正确。**

这会让外部研究失去价值。

第二种极端：

> **因为外部项目功能完整，就直接把它们的架构拼进 Learningflow。**

这会快速造成过度设计。

当前更合适的原则是：

> **用我们自己的原型获得真实问题，用外部成熟方法扩大解法空间，再用真实学习结果筛选。**

Learningflow 现在需要的是快速学习和修正，不是尽快冻结架构。

---

## 12. 第一轮源码审计已经产生的修正方向

第一轮已经不再停留在 README 功能比较。详细记录见：

- [`学习Runtime源码对照.md`](学习Runtime源码对照.md)

当前最值得进入实验的不是“马上加 Graph / FSRS”，而是几项会直接审查现有原型的变化：

1. **Evidence 事实抽取与评价分离**：当前 Transcript Compiler 同时选 Evidence 和评分，优先实验 Selector + Blind Assessor 两阶段；
2. **Tutor judgement 不自动成为 State Truth**：实时教学者的 `result / reason` 可以保存，但未来 State Compiler 应区分评价来源与可信等级；
3. **Misconception 建立 hypothesis → probe → supported/rejected 生命周期**，而不是一次错误直接贴标签；
4. **Concept Graph 与 Learner State 分离**，如果引入 frontier，它只产生可学候选，不替 ChatGPT 决定最终教学内容；
5. **Skill 先完善 routing / escalation，再决定是否物理拆分**，不因为外部项目有 20 个 Skill 就照搬；
6. **Teaching Reflection 先做 Transcript 离线评价**，只有证据证明有必要才进入 turn-level 在线 verifier。

同时第一轮也确认了一些当前设计值得继续保留的部分：

- 原始题目 / 原始回答与评价分层；
- Transcript 通过 message id 恢复原文；
- Evidence 的 source quality / assistance level；
- Evidence 优先、Learner State 可重算；
- ChatGPT 负责最终教学选择，Runtime 提供受约束候选和长期事实。

这里的“保留”仍然只是当前最合理判断，不升级为不可修改的 Decision。
