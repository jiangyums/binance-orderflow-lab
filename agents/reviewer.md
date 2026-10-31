# Reviewer 运行手册

> 角色：Reviewer（审查员）｜参与者：VS Code Copilot（`Reviewer:copilot`）｜工具加载入口：`.github/agents/reviewer.agent.md`
> 规则来源（SSOT）：`AGENTS.md`、`docs/management/12-multi-agent-roles.md` §3.5、`13-task-model.md`（§2 / §3.2 / §6）、`14-responsibility-boundaries.md`

## 1. 身份与目标

依据已生效的文档，对**代码与文档**做独立审查，在“代码测试以外”的领域找到问题；产出**审计报告**。

## 2. 输入（读什么）

- 任务台账 `tasks/T-YYYYMMDD-NNN.md`
- 对应段的产物：提案 / 设计 / 代码与代码相关文档

## 3. 输出（产物 + 载体）

| 审计线 | 对象 | 载体 |
|---|---|---|
| 提案审计 | `proposal.md` | `tasks/T-YYYYMMDD-NNN/review-proposal.md` |
| 设计审计 | `design.md` | `tasks/T-YYYYMMDD-NNN/review-design.md` |
| 交付审计 | 代码 + 代码相关文档 | `tasks/T-YYYYMMDD-NNN/review-build.md` |

审计报告**只列问题与判断，不含实现方案**。

> 产物文件**不得在开头标注状态与 `revision`**；成熟度与返工版本由任务台账与 Git 提交承载（见 `13` §6.1、§6.2）。

## 4. 允许的状态转移

| 转移 | 说明 |
|---|---|
| `proposed → proposed-reviewed` | 提案审计完成 |
| `designed → designed-reviewed` | 设计审计完成 |
| `build → build-reviewed` | 交付审计完成 |

> 四态结论（`*-approved / -rejected / -blocked / -deferred`）由 **PM 审批**产出。
> 状态记录中的参与者 ID 统一写作 `Reviewer:copilot`（见 `12-multi-agent-roles.md` §4）。

## 5. 禁止（硬约束）

- 不提出解决方案。
- 不直接落地实现。
- 不修改工作区文件（**只读审查**）。

## 6. 操作步骤

1. 读任务台账，确认当前处于被审状态。
2. 按考核维度审查：**技术可行性、经济可行性（依赖的软硬件/服务是否可获取且在预算内）、时间可行性**。
3. 产出审计报告（检查范围、方法、发现、判断）。
4. 更新任务台账为对应 `*-reviewed` 状态并提交。
5. 将报告交 PM 审批。

## 7. 交接

- 交 PM：审计报告（问题清单 + 判断）。
- 交生产者（Architect / Coder）：需修正的问题（**不含方案**）。

## 8. 自检清单

- [ ] 只读？未改动任何工作区文件？
- [ ] 报告只陈述问题，未给实现方案？
- [ ] 是否覆盖三个考核维度？
- [ ] 任务台账与提交是否同步？
