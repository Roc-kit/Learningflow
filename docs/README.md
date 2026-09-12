# Learningflow 文档索引

本目录只维护当前有效产品、架构和工程文档。历史过程与原始长对话不作为日常开发入口。

## 产品

- [`product/产品基线.md`](product/产品基线.md)：产品目标、首版范围、角色和不可混淆的业务概念。
- [`product/真实学习流程.md`](product/真实学习流程.md)：ChatGPT 作为主教学入口，Skill / MCP / Web 按需扩展的真实日常流程与 M0 验证路径。
- [`../chatgpt/PROJECT_INSTRUCTIONS.md`](../chatgpt/PROJECT_INSTRUCTIONS.md)：当前 Plus 路径可直接放入 ChatGPT Project 的 Teaching Protocol 模板。

## 架构

- [`architecture/长期学习操作系统.md`](architecture/长期学习操作系统.md)：最高层架构定位；定义 Context → ChatGPT → Evidence、Teaching Skill、MCP 系统调用层和按需 Activity Adapter。
- [`architecture/系统架构.md`](architecture/系统架构.md)：当前完整软件框架工作基线，包括模块、数据、运行流程、M1/M2/M3 建议。
- [`architecture/M0最小闭环设计.md`](architecture/M0最小闭环设计.md)：Stage 0 当前实施基线；定义 ChatGPT 直接问答、Assessment Skill、MCP Evidence 保存与可选 Web，不引入 Learner State 算法。

注意：该文件由建仓前 v0.1 设计基线收口而来，其中 FastAPI / React / PostgreSQL / Worker 等尚未全部通过正式实现验证，不应描述成已经存在的运行事实。

## 开发治理

- [`development/文档治理.md`](development/文档治理.md)：事实源、拆分、归档和长度规则。
- [`development/Git工作流.md`](development/Git工作流.md)：本地 Git、远端同步、commit/checkpoint 与敏感数据规则。
- [`development/项目管理.md`](development/项目管理.md)：Milestone、Issue、Discussion、Project State 和任务收口方式。

## 历史与原始材料

- `docs/archive/`：未来存放已失效但仍需追溯的正式文档；默认不读取。
- `resources/raw/`：本机原始聊天、AI 思考和未收口资料；`.gitignore` 排除，不进入版本库。

新会话默认从仓库根目录 `PROJECT_STATE.md` 开始，不从本目录逐份遍历文档。
