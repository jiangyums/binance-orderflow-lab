# AGENTS.md — 多 agent 协作协议

本文件是多 agent 协作的**唯一权威协议**。
角色行为细则的**权威索引见 `agents/README.md` §2**（角色 | 参与者 | 统一手册 | 工具加载入口）；下列仅为速查，路径均指向单本手册文件：

- `agents/pm.md`：Cline 的项目经理职责
- `agents/architect.md`：Qoder 的架构师职责
- `agents/coder.md`：opencode 的代码编写职责
- `agents/tester.md`：kilo 的测试职责
- `agents/reviewer.md`：审查员职责（VS Code Copilot 经 `.github/agents/reviewer.agent.md` 加载）
- `docs/management/12-multi-agent-roles.md`：多 agent 角色模型（生效）
- `docs/management/13-task-model.md`：任务模型（生效）
- `docs/management/14-responsibility-boundaries.md`：责任边界（草案，待用户审批）
- `docs/management/15-version-control-convention.md`：版本控制约定（草案，待用户审批）
- `docs/management/00-governance-index.md`：治理文档总目录（其余 01–11 号规则的入口；§6 定义「项目治理文档」的范围）

> **通用加载令**：各 agent 任务开始时，**只**读取与自己角色对应的那一本运行手册（见上列对应行），再按该手册的指针读取规则章节，然后行动。
> **不得批量读取其他角色的运行手册**——手册之间存在权限边界（如「不得置位 `approved` 系列状态」「不得修改治理文档」），读了他人手册会误设自己的边界。
> **刷新纪律**：注入各工具上下文的是**会话启动时的快照**，不会随本文件的磁盘编辑自动刷新。
> 每次任务开始时请回查根目录的 `AGENTS.md` **文件本体**并以之为准，勿仅凭注入副本行动；
> 引用本文件提及的任何路径前，先确认对应文件仍然存在。

## 1. 角色分工

| 智能体 | 角色 | 职责 | 写权限 |
|---|---|---|---|
| Cline | 项目经理（PM） | 审批需求/方案、输出审批结论、审批任务 | 只读审批 + 落盘即提交（任务台账，`14` §6.0） |
| Qoder | 架构师 | 需求分析、方案与接口设计 | 仅在已获批任务范围内；落盘即提交（`14` §6.0） |
| opencode | Coder | 代码编写者 | 仅实现已获批任务；落盘即提交（`14` §6.0） |
| kilo | Tester | 测试者 | 仅验证已获批任务；落盘即提交（`14` §6.0） |
| Reviewer | 审查员 | 依据已生效的文档对代码和文档进行审查，在代码测试以外的领域找到问题 | 只读审查 + 审计报告 / 台账落盘即提交（`14` §6.0） |
| ↳ VS Code Copilot | 审查员 | 承担 Reviewer 角色（加载入口 `.github/agents/reviewer.agent.md`） | 只读审查 + 审计报告 / 台账落盘即提交（`14` §6.0） |

> **落盘即提交**：各角色对本角色被允许落盘的那批文件（及对应任务台账）均可执行 `git add` / `git commit` / `git push`，见 `14` §6.0、`15` §10。

## 2. 任务模型

每个任务具有以下核心字段：

| 字段 | 说明 |
|---|---|
| `task_id` | 任务唯一标识，格式 T-YYYYMMDD-NNN |
| `status` | 当前状态 |
| `input_contracts` | 任务依赖的输入 |
| `output_contracts` | 任务产出 |
| `assignees` | 角色与参与者 |

任务状态：

```text
proposed
  ↓
proposed-reviewed
  ├── proposed-approved
  ├── proposed-rejected
  ├── proposed-blocked
  └── proposed-deferred

proposed-approved
  ↓
designed
  ↓
designed-reviewed
  ├── designed-approved
  ├── designed-rejected
  ├── designed-blocked
  └── designed-deferred

designed-approved
  ↓
build
  ↓
build-reviewed
  ├── build-reviewed-approved
  ├── build-reviewed-rejected
  ├── build-reviewed-blocked
  └── build-reviewed-deferred

build-verified
  ├── build-verified-approved
  ├── build-verified-rejected
  ├── build-verified-blocked
  └── build-verified-deferred

build-verified-approved
  └── 任务完成（final）
```

状态记录格式：

```text
T-YYYYMMDD-NNN <旧状态> -> <新状态> by <角色>:<参与者ID> | <原因/动作>
```

示例：

```text
T-20261017-001 proposed | 提案提议
T-20261017-001 proposed -> proposed-reviewed | 提案审计完成
T-20261017-001 proposed-reviewed -> proposed-approved | decision=通过
T-20261017-001 proposed-approved -> designed | 设计开始
T-20261017-001 designed -> designed-reviewed | 设计审计完成
T-20261017-001 designed-reviewed -> designed-approved | decision=通过
T-20261017-001 designed-approved -> build | 构建开始
T-20261017-001 build -> build-reviewed | 交付审计完成
T-20261017-001 build-reviewed-approved -> build-verified by Tester:kilo | 测试完成
T-20261017-001 build-verified -> build-verified-approved | verdict=通过
```

## 3. 消息格式

### 3.1 消息包

所有跨 agent 消息都应包含：

| 字段 | 说明 |
|---|---|
| `from_agent` | 发送角色 |
| `to_agent` | 接收角色 |
| `task_id` | 任务标识 |
| `kind` | 消息类型 |
| `payload` | 消息内容 |

常见 `kind`：

| 值 | 说明 |
|---|---|
| `task_proposed` | 提出任务 |
| `review_request` | 请求审查 |
| `review_result` | 审查结果 |
| `approval` | 审批 |
| `rejection` | 驳回 |
| `conclusion` | 审批结论 |
| `task_status_changed` | 任务状态变化 |
| `observation` | 观察或补充说明 |

### 3.2 提交审批（Qoder 发出）

```text
【提交审批】
对象：方案名 + 涉及文件路径
动机：解决什么问题（1-3 行）
变更摘要：新增/修改哪些文件与接口
风险与回滚：
自检：已对照本协议与 docs/management/ 哪些条款
```

### 3.3 审批结论（Cline 发出）

每次审批必须按此格式输出（便于整体复制回 Qoder）：

```text
【审批】结论：approved / rejected / blocked / deferred（四态之一）
范围：涉及的文件与文档（路径）
问题：
- P0 阻断项：<文件路径:行号> — 问题说明 + 修改建议
- P1 应修项：...
- P2 建议项：...
审计意见核对表：逐条标注「修复 / 无视 / 延后」
审计覆盖缺口：尚未被审计、应当被审计的领域
条件：仅 `blocked` 时填写缺少的条件；`rejected` 时填写返工要求
下一步：Qoder 应执行的具体动作
```

> 审批结论只能是四态之一；不得使用「有条件通过」「部分通过」「通过但需补充」等表述。

## 4. 多 agent 审批与任务协作

建议流程：

1. 架构师提出任务或方案。
2. Reviewer 依据已生效的文档审查代码和文档，找到问题。
3. Tester 依据已生效的设计文档测试代码，交付测试结果。
4. PM 审批 Reviewer、Tester 的输出结果。
5. PM 审批项目治理文档（治理文本由 Coder 落盘）。
6. 用户审批项目治理文档。
7. 审批通过后，执行者落地。产物**一律直接落盘到最终载体**，不设草稿专用目录；**产物文件内不得标注状态或 `revision`**，成熟度由任务台账与 Git 提交承载（见 `13-task-model.md` §6.1）。
8. 任务状态更新为 `build-verified-approved`（终态）。

多 agent 角色和任务规则的详细内容见：

- `docs/management/12-multi-agent-roles.md`
- `docs/management/13-task-model.md`

## 5. 冲突处理

- 协作冲突以 `docs/management/10-authority-map.md` 为准：高层规则优先
- 行为细则冲突：Cline 以 `agents/pm.md` 为准，Qoder 以 `agents/architect.md` 为准
- 本协议与角色细则冲突时，本协议（角色分工与流程）优先