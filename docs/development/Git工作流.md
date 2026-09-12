# Learningflow Git 工作流

当前项目先使用简单、可恢复的 Git 主线，不为尚未出现的团队协作提前建设复杂分支模型。

## 1. 开发前检查

```bash
git status --short
git status -sb
git log --oneline --decorate -6
```

如果已经配置远端：

```bash
git fetch origin
git status -sb
```

规则：

- 本地与 `origin/main` 一致：正常开发；
- 本地只落后且可 fast-forward：`git pull --ff-only`；
- 本地只领先：不要 pull；
- 已 diverged：停止普通开发，先分析，不自动 merge / rebase / force push；
- 工作区有无关未提交修改：保留并绕开，不 reset / clean / stash。

## 2. 分支

- 当前单人早期开发以 `main` 为主。
- 明确需要隔离的实验、较大重构或未来多人协作时再使用 feature branch / worktree。
- 不为了形式给每个小改动创建分支。

## 3. Commit

一个 commit 应对应一个可说明、可验证、可回退的逻辑单元。

常用格式：

```text
checkpoint: initialize project governance
feat: add practice submission flow
fix: preserve original attempt on resubmission
docs: clarify evidence revision rules
test: cover real/test workspace isolation
```

阶段 checkpoint 只提交可运行或可验证状态。

## 4. 不允许的操作

除非用户明确要求并已分析影响，不使用：

```text
git reset --hard
git clean -fd
git push --force
git rebase 对已共享历史改写
```

不把别人的未提交改动清掉来制造“干净工作区”。

## 5. 敏感与真实学习数据

以下内容不得提交 Git：

- `.env`、API Key、Token、Webhook URL；
- 真实学生姓名、身份资料；
- 真实作业照片、录音、OCR 原始隐私材料；
- 生产/真实数据库、媒体存储和运行日志；
- `resources/raw/` 中的原始聊天与研究材料。

测试使用合成学生、合成题目和脱敏样例。

## 6. 远端仓库

当前正式建仓步骤只初始化本地 Git。创建 GitHub 仓库、设置公开/私有、添加 `origin` 和首次 push 作为单独外部动作处理；在没有明确仓库归属和可见性要求前，不自行创建远端。

远端建立后，GitHub Issue 用于明确 Bug / Feature；开放式产品研究和路线讨论适合 Discussion（工具支持时）。GitHub 对象和本地代码的事实源保持分工：代码、版本化文档从本地 Git 写入，Issue 记录目标、验收和结果。
