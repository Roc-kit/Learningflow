# Engram 深挖：Evidence 与状态推进

更新日期：2026-09-14

状态：**源码研究记录 / Candidate 输入**。

本专题继续检查 Engram 的 `engram.py`、Assessor 与架构文档，目的不是采用 Engram，而是回答：它有哪些机制能够反过来暴露 Learningflow 当前 Evidence Contract 的不足。

## 1. 核心判断

Engram 的核心并不是：

```text
回答
→ 打一个更准的分
→ 更新 mastery
```

而是：

```text
发生了什么类型的学习事件？
        +
学习者实际产出了什么？
        +
评价者给出了什么 verdict？
        ↓
不同事件执行不同的 state transition
```

这提示 Learningflow：在讨论 mastery 算法之前，必须先确保一次学习事件本身的语义足够清楚。

## 2. Engine 自己保存事实，Grader 只拥有 verdict

Engram 的 learner production、confidence、probe 等由 engine 在 `stash` 时先保存；Blind Assessor 返回结果后，receipt 创建代码重新从 stash 取 learner facts，而不是相信 Assessor 原样回显。

```text
Engine-owned facts
  production
  confidence
  probe

Grader-owned judgement
  grade
  rating
  misconception
  rubric_notes
  error_class
```

这比单纯要求模型“不要改写原答案”更强：完整性由程序结构保证，而不是 Prompt 纪律保证。

Learningflow 当前 Transcript Compiler 已经部分具有这个性质：模型返回 message id，程序恢复原文；但实时 `record_assessment_run` 仍允许调用方一次提交 learner facts + judgement，没有同等级的 provenance separation。

**当前判断：这个原则值得成为 Candidate。**

## 3. Evidence 先落盘，State 后推进

Engram 在 apply state 时明确遵守：

```text
write receipt
→ append succeeds
→ update graph / FSRS state
```

而不是先改 state 再补 Evidence。

这样即使中间 crash，最坏情况是：

```text
有 Evidence，但 State 还没推进
```

而不会出现：

```text
State 已经变成 mastered
但支撑它的 Evidence 不存在
```

这个顺序与 Learningflow 已有“State 可由 Evidence 重算”的原则一致，未来实现 State Compiler 时应继续保持。

## 4. 同样一次“答错”，事件类型不同，状态含义不同

Engram 至少区分：

```text
encode      首次编码 / 首次验证
review      间隔检索
transfer    新情境迁移
relearn     同日失败后的重新达到标准
audit       对评分本身的复核
```

### 4.1 `relearn` 不等于第二次 review

同一天第一次 retrieval 失败、教学后再次答对，第二次作答会被保存，但不再推进 FSRS schedule。

这避免：

```text
刚刚被纠正
→ 立刻答对
→ 被错误计算为又一次长期保持成功
```

这与 Learningflow 已有的“刚讲完答对 ≠ 延迟独立掌握”原则高度一致，但 Engram 把它落实到了 state transition。

### 4.2 `transfer` 失败不等于 memory lapse

如果一个成熟概念在迁移题里失败，Engram 会记录 transfer failure，但不因此把原概念的 memory schedule 大幅降级。

它区分：

```text
概念记得住
≠
能在新情境自动迁移
```

这一点对 Learningflow 很重要：未来不能用一个简单的 `incorrect` 去统一降低所有 mastery 维度。

### 4.3 `audit` 只评价评分系统，不改变学习状态

Blind Assessor 对 Tutor 自评做 spot audit 时，audit receipt 会留下，但 schedule / reps / state 全部不动。

因此：

> **并不是所有“关于学习的记录”都应该成为 Learner State 的输入。**

## 5. 暴露出的 Learningflow 当前实现缺口

`M0最小闭环设计.md` 曾提出：

```text
guided_practice
independent_check
delayed_check
transfer_check
```

但当前实际 SQLite `assessment_runs` 只有：

```text
purpose
capture_mode   # live / batch_verbatim / summary
surface
```

当前实现里，**技术采集方式 `capture_mode` 已落地，但教学事件语义 `assessment mode / evidence kind` 没有真正进入数据库 Contract。**

这是本轮源码对照发现的一个真实“文档设计 > 当前实现”缺口。

它不意味着现在立刻加一个 enum 字段就算解决。更应该先确认未来需要表达哪些正交维度：

```text
Capture provenance
  live / transcript / summary / ...

Learning event intent
  guided practice / independent / delayed / transfer / ...

Evaluation role
  tutor judgement / blind assessor / deterministic / human / audit

State effect
  eligible / informational-only / unknown
```

这四个维度不能继续混成一个 `result` 或 `capture_mode`。

## 6. 当前优先级修正

Evidence 这条线下一步不应先讨论“mastery 用什么算法”。更靠前的问题是：

> **我们是否已经把一次学习事件表达清楚到足以让未来 State Compiler 正确解释？**

如果连：

```text
这是提示后的练习
还是隔三天后的独立复测
还是迁移任务
还是对原评分的 audit
```

都没有可靠区分，那么后面无论用规则、BKT、FSRS 还是 LLM，都只是对语义不足的数据做更复杂计算。

当前研究优先级调整为：

```text
先验证 Evidence event semantics
→ 再实验 independent assessor
→ 再讨论 State Compiler 如何消费不同 Evidence
```

这里的“验证”先使用真实 M0 Transcript / 作答样本确认字段需要，不立即修改数据库。

## 7. 当前可借与不借

值得继续验证：

- engine-owned learner facts / grader-owned judgement；
- Evidence 先写、State 后推进；
- event kind 决定 state transition，而不是只有 correct / incorrect；
- audit 类证据可以存在但明确不影响 State；
- immediate relearn 与 delayed review 分开；
- memory retention 与 transfer capability 分开解释。

暂不照搬：

- Engram 全套 event kind；
- 其成人学习场景的 confidence / calibration 全模型；
- FSRS state machine；
- 所有 event 都做成 append-only JSONL 文件；
- 任何尚未通过小学英语真实样本证明必要的复杂字段。
