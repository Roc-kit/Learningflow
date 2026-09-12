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

当前没有正式应用代码。已有设计文档属于产品/架构工作基线，不代表对应能力已经实现。

下一步优先验证：

```text
ChatGPT 直接教学
→ Assessment Skill 进入短验证
→ 孩子直接用文字 / 语音回答
→ MCP 保存关键 Learning Evidence
→ ChatGPT 根据这次具体回答继续教学
```

普通问答默认不切网页。M0 再额外选择一个确实需要专用 UI 的 Activity，验证 Web 作为按需 Adapter 能顺利回到当前教学上下文。

## 文档入口

新任务先读：

1. [`PROJECT_STATE.md`](PROJECT_STATE.md) — 现在处于什么阶段、下一步做什么；
2. [`AGENTS.md`](AGENTS.md) — AI / 开发治理与文档路由；
3. [`docs/README.md`](docs/README.md) — 产品、架构、工程文档索引；
4. [`DECISIONS.md`](DECISIONS.md) — 长期关键决策及原因。

原始长对话和未收口研究材料保存在本机 `resources/raw/`，不进入 Git，也不作为现行事实源。
