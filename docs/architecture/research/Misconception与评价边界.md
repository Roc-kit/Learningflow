# Misconception 与评价边界：第二轮源码研究

更新日期：2026-09-14

状态：**研究记录 / 待讨论**。

本文继续沿用 `学习Runtime演进方向.md` 的原则：Learningflow 当前实现只是早期原型，外部项目的方法可以用于补充、修改甚至推翻现有设计。

本轮聚焦两个问题：

1. 一次错误怎样逐步演变为“可用的错因 / misconception”，而不是模型随口猜一个标签；
2. 哪些题目应该由程序确定性判分，哪些需要 Tutor / 独立 Assessor / 人工判断。

本文只把目前证据足够的内容写成“当前判断”；其余保留为“待讨论”，不进入正式 Contract。

---

## 1. 先拆开四个经常被混用的概念

当前比较后，至少应该在语义上区分：

```text
Error / Response Event
  一次真实作答发生了什么

Doubt
  学习者自己表达“不懂 / 不确定 / 想继续问什么”

Weak Area
  多条 Evidence 显示某个知识范围持续不稳定

Misconception Hypothesis
  关于“学习者正在使用某个具体错误模型”的诊断假设
```

它们可能互相关联，但不能互相替代。

例如：

```text
题：Does Tom ___ football?
答：likes
```

能够直接确认的只有：

```text
这次回答是 likes
本题在当前 rubric 下错误
```

还不能直接确认：

```text
孩子不懂三单
孩子不懂 does
孩子把名词复数规则套到了动词
```

后面这些都需要更多 Evidence。

### 1.1 为什么 `Doubt` 要单独保留

`open-cognition` 把 Doubt 作为独立对象，只有：

```text
content
status: open | resolved
topic / flashcard relation
```

这虽然很简单，但语义是正确的：

> “我有疑问”不是“我已经存在某个错误模型”。

例如孩子说：

> 为什么 does 后面不能用 likes？

这首先是一条 learner-stated doubt。

它可能来自：

- 真正的 misconception；
- 还没学过；
- 规则记不牢；
- 只是想理解原因。

因此不应该自动写入 misconception。

### 1.2 为什么 `Weak Area` 也不等于 `Misconception`

`edu-agent-skills` 的 `weak-area-tracker` 有一个值得借鉴的原则：

- 第一次接触不算 weak area；
- 一次 slip 不算 weak area；
- repeated error 才进入持续追踪；
- 改善需要跨次 clean pass 才退出。

它的具体 `recurrence × type_weight + staleness_bonus` 评分公式目前没有足够理由直接采用，但“**持续不稳定 ≠ 具体错误模型**”这个分层值得保留。

例如：

```text
最近四次三单题：错、对、错、对
```

可以支持：

```text
三单独立应用仍不稳定
```

却仍然未必能支持：

```text
存在某一个确定 misconception
```

---

## 2. 外部项目在 Misconception 上其实并没有一个成熟统一答案

这一点需要明确，避免因为项目名字里有 `misconception tracking` 就误认为已经解决。

### 2.1 `knowledge-graph-mcp`：实现过于直接

当前源码中：

```text
update_node(... misconception_detected="...")
→ 直接追加到 node.misconceptions[]
```

没有看到完整的：

```text
支持 Evidence
反证 Evidence
待验证状态
重复检测
合并
撤销 / rejected
```

所以它适合借鉴：

- misconception 能成为 Context 查询维度；
- 可以和 concept relation / review 联动。

但不适合照搬其“检测到一个字符串就长期挂到 node 上”的生命周期。

### 2.2 Engram：教学策略很强，Misconception Store 本身仍很薄

Engram 有较强的行为策略：

- 高置信错误触发 hypercorrection；
- blind assessor 可以输出 misconceptions；
- repeated lapse 会改用新的教学策略；
- misconception 会进入后续 artifact / contrast case 的生成上下文。

这些值得借。

但是实际 `misconceptions.json` 的核心生命周期仍基本是：

```text
add
→ open
→ resolve
```

记录字段主要是：

```text
topic
node
description
status
timestamp
```

并没有建立非常完整的“假设如何被支持或推翻”的 Evidence graph。

另外 Engram 会把 `wrong + high confidence` 很积极地视为 misconception gold。这个策略在成人主动学习中可能有价值，但对小学儿童是否应该这么激进，目前不能直接接受。

### 2.3 `edu-agent-skills`：生命周期思想更适合我们，但仍主要是 Prompt 规范

它提出：

```text
repeated conceptual mistake
→ classify surface / structural / deep
→ restate learner's wrong model
→ confirm with learner
→ root cause
→ targeted correction
→ novel-case verification
→ log weak area
```

其中值得借鉴的核心是：

> **不要假定 misconception；先把错误模型说清楚，并通过后续问题验证。**

但这里大部分仍是 Skill / Prompt 层规范，不是严谨的数据生命周期实现。

因此也不能直接把 `surface / structural / deep` 三分类写死进 Learningflow 数据库。

---

## 3. 当前更适合 Learningflow 的 Misconception 思考模型

目前更倾向于先采用“Evidence → Hypothesis → Probe → Update”的思想，而不是先设计复杂 taxonomy。

候选链路：

```text
Learner Response
      │
      ▼
Observed Error / Pattern
      │
      ├── 一次性 slip → 保留 Evidence，不升级
      │
      ├── 多次不稳定 → Weak Area Candidate
      │
      └── 出现具体错误推理
              │
              ▼
      Misconception Hypothesis
              │
              ▼
       Diagnostic Probe
              │
       ┌──────┴──────┐
       ▼             ▼
   支持假设         反驳假设
       │             │
       ▼             ▼
  targeted       reject / revise
  remediation       hypothesis
       │
       ▼
  delayed / transfer recheck
```

这里最重要的不是状态名字，而是：

> **任何长期错因判断都应该可以回到“为什么这么判断”的 Evidence。**

### 当前暂时不建议做的事情

暂时不建议：

- 一次答错就创建正式 Misconception；
- 让 LLM 自己输出一个字符串并永久挂到知识点；
- 预先建设几百种固定 misconception taxonomy；
- 直接用一个 0–1 的“误区置信度”掩盖证据不足；
- 因为一条 misconception hypothesis，就同步降低一大片 prerequisite mastery。

---

## 4. 待讨论：Misconception 是否需要独立持久化实体

这里目前还不能定。

有两种合理路线。

### 路线 A：先不建独立实体

早期只保存：

```text
Evidence
+ assessment reason
+ diagnostic notes
```

每次 Context 生成时由模型重新综合近期 Evidence。

优点：

- 最简单；
- 不会过早把模型猜测固化；
- 适合当前数据很少的阶段。

缺点：

- 同一个错因会被反复重新推理；
- 很难追踪“这个假设什么时候出现、怎样被否定”；
- 后续 Review / targeted remediation 不容易稳定引用。

### 路线 B：建立 `DiagnosticHypothesis` / `MisconceptionHypothesis`

它不是“真相表”，而是显式保存诊断假设，例如：

```text
id
student_id
concept_id?
description
status
supporting_evidence[]
contradicting_evidence[]
created_at
updated_at
resolved_at?
```

状态也不一定叫 `confirmed`，更保守的候选是：

```text
candidate
supported
rejected
resolved
reopened
```

优点：

- 可追溯；
- 可撤销；
- 能驱动 diagnostic probe 和 review；
- 比直接写 `node.misconceptions[]` 更严谨。

缺点：

- 现在可能太早；
- 容易把一个很自然的教学判断工程化得过重；
- `supported` 到底需要多少 Evidence，目前没有标准。

**当前不决策。** 建议先通过真实小学英语案例观察 5–10 个“明显重复错误”，看是否真的需要持久化生命周期。

---

## 5. 判分首先应该拆成“答案事实”和“评价机制”

Learningflow 当前已经有：

```text
LearnerResponse.raw_answer

AssessmentRevision
  result
  normalized_answer
  reason
  evaluation_method
```

这个分层本身应该保留。

但是当前 `evaluation_method` 只有：

```text
deterministic
llm
human
```

还不能区分：

```text
Tutor 自评
独立 Assessor
二次 Audit
人工复核覆盖
```

而且 `get_learning_context` 当前会直接取一个 Response 最新的 `AssessmentRevision`。

如果以后加入 audit，这种“最新一条就是当前真相”的规则可能不够，因为：

> Audit 可能只是记录第二意见，并不应该自动覆盖原评价或改变 State。

这一点已经成为现有数据模型的明确待完善处。

---

## 6. 哪些题适合确定性判分

当前产品文档已经确立原则：

> 客观题优先规则判分，开放题结合评分标准交给模型。

源码研究后，这个方向仍然合理，但需要更精细。

### 6.1 很适合确定性判分

当答案结构和 answer key 都明确时：

```text
单选
多选
匹配
排序
True / False
明确答案集的填空
```

程序直接比较结构化值，优点是：

- 一致；
- 便宜；
- 可复核；
- 不受 Tutor 对话情绪影响。

### 6.2 条件式确定性判分

小学英语中大量题目处于这一层：

```text
go → goes
do → does
child → children
He ___ (like) cats.
```

如果题目拥有明确的：

```text
expected_answer
accepted_answers[]
normalization rules
```

则可以确定性判分。

但需要谨慎处理：

- 大小写；
- 标点；
- 前后空格；
- 缩写与完整形式；
- 多个语法上都合理的答案；
- 题目本身语境不足。

所以“填空题”这个题型本身不等于确定性判分，关键在于有没有封闭答案空间。

### 6.3 不适合只用确定性判分

典型包括：

```text
解释为什么
造句
改写句子但允许多种表达
阅读开放问答
作文
口头解释
迁移题
错因说明
```

这些更适合 rubric-based Assessor。

### 6.4 口语需要再拆一层

如果只获得 ChatGPT 的转写文本：

```text
可以评价内容
不能可靠评价发音
```

要评：

```text
发音
重音
流利度
漏读
音素问题
```

必须使用实际音频或能够访问声学信息的模型 / 服务。

不能把 transcript 当作原始语音 Evidence。

### 6.5 纸笔作业还多一个不确定性来源

纸笔流程至少有：

```text
图片
→ 答案提取 / OCR
→ 结构化答案
→ 判分
```

所以必须区分：

```text
extraction uncertainty
grading uncertainty
```

例如规则判分得到“错误”，但 OCR 把 `goes` 识别成 `goe5`，真正不确定的是提取，不是学生知识。

这条边界应该继续保留在后续作业模块设计中。

---

## 7. 独立 Assessor 应该用在哪里：当前有三种方案

这里仍然是待讨论重点。

### 方案 A：所有开放题都独立 Assessor

```text
Tutor
→ 收到回答
→ 独立 Assessor
→ verdict
→ Tutor 根据 verdict 继续
```

优点：最干净，Tutor 不给自己教学成果评分。

问题：

- 增加延迟；
- 增加模型调用；
- 语音实时教学可能明显变卡；
- 很多低风险练习其实没必要。

### 方案 B：Tutor 即时判断，关键 Evidence 独立复核

例如：

```text
guided practice
  → Tutor 自评即可

independent / delayed / transfer check
  → 独立 Assessor
```

优点：更符合实际教学体验，也保留高价值 Evidence 的独立性。

风险：

- 必须定义哪些 Evidence “高价值”；
- 同一 Response 可能出现 Tutor verdict 与 Assessor verdict 不一致；
- State Compiler 需要知道应该听谁的。

### 方案 C：实时都由 Tutor，事后抽样 Audit

类似 Engram Review 的部分做法：

```text
Tutor 自评
→ 正常继续
→ 后台 / 会话后随机或按风险抽样 blind audit
```

优点：交互最顺。

问题：

- 如果 Tutor 当场判断错，教学已经沿着错误判断继续；
- Audit 只能改善长期状态和未来教学，不能修复当场体验。

### 当前倾向，但不定案

目前看 **B 最值得原型验证**：

> 低风险练习保留 Tutor 的即时智能；真正要推进长期状态的 Evidence 尽量走更独立、更严格的评价。

但是否值得增加一次模型调用，需要真实测试延迟和实际评分差异。

---

## 8. 当前 Evidence Compiler 有一个可以直接做的对照实验

现在的离线 Compiler 是：

```text
一次 Codex 调用
→ 选择 prompt_message_id / response_message_id
→ 同时输出 correct / incorrect / partial + reason
```

程序再根据 message id 恢复原始文本。

事实保存这部分已经比较稳，但“抽取”和“评价”仍由同一个模型步骤完成。

可以做一个不改变正式数据模型的实验：

```text
Stage A：Evidence Selector
  只选择“哪两条消息构成真实问答”
  不判分

Stage B：Independent Assessor
  只看：
    question
    learner answer
    expected answer / rubric（若有）
    必需的 source material
  不看完整教学对话
  输出 verdict + reason
```

然后比较：

```text
当前单阶段结果
vs
两阶段 blind-ish Assessor 结果
```

重点观察：

- 是否真的减少过度宽松评分；
- 两者不一致率是多少；
- 小学英语客观题是否根本不值得调用 Assessor；
- 延迟 / 成本是否可以接受；
- 缺少 answer key / rubric 时 Assessor 是否频繁只能 pending_review。

这是目前比较适合做的研究原型，因为不需要先修改正式 Schema。

---

## 9. 当前现有 Schema 可能缺的不是“更多表”，而是评价语义

当前 `assessment_revisions` 已经允许一个 Response 有多条 Revision，这意味着未来理论上可以同时保存：

```text
Tutor verdict
Assessor verdict
Human verdict
Audit result
```

所以不一定马上增加新表。

更可能缺的是：

```text
grader_role / verdict_role
grader identity / version
是否参与 State 编译
是否 supersede 前一评价
是否仅 audit / informational
rubric / answer-key version
```

但这些字段现在也不应该一次全部加入。

先通过两阶段 Compiler 实验验证：

> **“多评价来源”是不是一个真实问题，而不是理论洁癖。**

---

## 10. 当前需要继续讨论的四个问题

### 10.1 Misconception 要不要早期就持久化？

目前倾向：**先不急着建完整实体，但要保留未来可追溯升级的路径。**

需要结合真实使用判断：同一个错因是否真的会跨会话反复出现到值得独立管理。

### 10.2 “孩子明确说出错误规则”能不能直接升级为 misconception？

例如：

> 因为 he 是一个人，所以后面的动词不用加 s。

这比单纯答错强很多，但是否直接叫“supported misconception”，还是仍需要一道区分题验证，目前不确定。

### 10.3 独立 Assessor 的门槛放在哪里？

候选是：

```text
只用于开放题
只用于 independent / delayed / transfer
只用于 State advancement
Tutor 与规则评分冲突时才启动
按风险抽样
```

需要实际测延迟、准确性与调用成本后决定。

### 10.4 儿童场景是否应该采集 confidence？

Engram 很依赖 `confidence-before-feedback`，尤其高置信错误。

补充教育心理学资料后，可以把问题进一步缩小：

- Grade 3–6 儿童中已经观察到 high-confidence error 的 hypercorrection effect；
- 综述显示儿童在小学早期已经能够做有一定信息量的 confidence judgment，约 7–9 岁后区分正确 / 错误回答的 metacognitive monitoring 明显改善；
- 但儿童仍存在明显 overconfidence bias，confidence 不能当作“孩子真实掌握度”的直接读数。

因此现在的问题不再是“儿童能不能提供 confidence”，而是产品上是否值得采集，以及怎样采集。

仍待验证：

- 能否稳定理解 0–100 confidence；
- 每题询问会不会严重打断教学；
- “很确定 / 不太确定 / 猜的”这种三档是否更适合；
- 是否只有 diagnostic / independent check 才问；
- confidence 是否真的能改善我们的错因诊断和后续教学，而不是只多一个数据字段；

目前 Learningflow 自己都没有真实数据。

当前倾向仍是：**不加入每题必问的 confidence Contract；如果实验，优先用低摩擦的离散选项，并只在少量诊断 / 独立验证题中采集。**

参考线索：

- Metcalfe & Finn, *Hypercorrection of high confidence errors in children*, Learning and Instruction, 2012；
- *Metacognitive Development and Conceptual Change in Children*, Review of Philosophy and Psychology, 2020；
- *Development of Children’s monitoring and control when learning from texts*, Metacognition and Learning, 2020。

---

## 11. 本轮暂时形成的研究结论

可以比较有把握保留的只有这些：

1. **答错、Doubt、Weak Area、Misconception Hypothesis 必须在概念上分开。**
2. **单次错误不能自动升级为长期 misconception。**
3. **Misconception 如果长期保存，必须能够回到支持 / 反驳它的 Evidence。**
4. **客观、封闭答案空间优先确定性判分。**
5. **开放回答应考虑 rubric-based 评价；Tutor 自评不是唯一可能方案。**
6. **事实抽取和评价可以拆开，值得直接用当前 Transcript Compiler 做实验。**
7. **OCR/转写不确定性与判分不确定性要分开。**
8. **当前 Schema 已能保存多个 revision，但缺少评价角色与 State effect 的明确语义。**

其他内容仍然是 Candidate / 待讨论，不进入正式架构决策。

