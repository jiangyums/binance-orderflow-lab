# 项目治理索引

## 1. 文档目的

本目录定义项目治理体系，用于管理：

- 规则文本
- 决策记录
- 状态变化
- 文档引用
- 变更过程
- 审计记录

本目录不定义业务算法，不定义工程实现。

---

## 2. 权威层级

项目治理信息按以下优先级解释：

1. 已生效规则文本
2. 已确认裁定文本
3. 治理台账
4. 审计记录
5. 历史讨论记录

---

## 3. 核心治理对象

|对象|说明|
|-|-|
|Rule|规则文本|
|Decision|裁定|
|Ledger|追加记录|
|State|状态|
|Evidence|证据|
|Reference|引用|

---

## 4. 文档状态

所有治理文档具有：

- 草案
- 候选
- 生效
- 废止

## 5. 治理文档目录

本目录下包含以下治理文档：

| 文件 | 说明 |
|---|---|
| 00-governance-index.md | 本文件：项目治理索引 |
| 01-governance-principles.md | 治理原则 |
| 02-document-lifecycle.md | 文档生命周期 |
| 03-rule-management.md | 规则管理 |
| 04-state-model.md | 状态模型 |
| 05-change-control.md | 变更控制 |
| 06-reference-policy.md | 引用策略 |
| 07-term-management.md | 术语管理 |
| 08-open-items-management.md | 开放项管理 |
| 09-audit-policy.md | 审计策略 |
| 10-authority-map.md | 权威映射 |
| 11-governance-open-items.md | 治理开放项 |
| 12-multi-agent-roles.md | 多 agent 角色模型 |
| 13-task-model.md | 任务模型 |
| 14-responsibility-boundaries.md | 责任边界 |
| 15-version-control-convention.md | 版本控制约定（生效） |

> 说明：本文档目录为治理文档清单。12、13、14、15 已确认角色定义、任务状态机与治理流程，现均已升级为生效状态。
> 注：编号 `14` 原为 `14-governance-transitions.md`（治理流程与状态转移），该文件已删除；本次顺延重编号后，`14` 现由《责任边界》占用。

---

## 6. 项目治理文档的范围

「项目治理文档」指下列载体下的**文档文件（`.md`）**：

| 载体 | 说明 |
|---|---|
| `docs/management/` | 治理规则本体（`00`–`15`，见 §5 目录） |
| `agents/` | 各角色运行手册（见 `agents/README.md`） |
| `.clinerules/` | 工具加载令 |
| `.opencode/agents/` | opencode 的 agent 定义 |
| `.kilo/agents/` | kilo 的 agent 定义 |
| `.github/agents/` | VS Code Copilot 的 agent 定义（Reviewer 加载入口） |
| `AGENTS.md` | 多 agent 协作协议（根目录单文件） |

规则：

- 上述目录下的**全部文档文件**均为项目治理文档；治理文档的身份由**所在载体**决定，不逐文件列举。
- 载体目录本身不是治理文档，其中的文档文件才是。
- `docs/` 下 `management/` 以外的文档（设计文档、统计报告、实验记录等）**不属于**项目治理文档。
- 任务台账 `tasks/` **不属于**项目治理文档（它是任务状态的事实来源，见 `15-version-control-convention.md` §4）。
- 本节是「什么算项目治理文档」的**唯一判定依据**。其他文件引用该概念时一律指向本节，不复制清单。

> **与 `15-version-control-convention.md` §3.1 的区别**：§3.1 规定「哪些文件纳入版本控制」，本节规定「哪些文件是治理文档」。二者**不是同一集合**：纳管范围包含实现、配置、测试等全部受管文件；治理文档只包含规则文本与角色手册。不得互相替代。