# Tester 运行手册

> 角色：Tester（测试者）｜参与者：kilo
> 规则来源（SSOT）：`AGENTS.md`、`docs/management/12-multi-agent-roles.md` §3.4、`13-task-model.md`（§2.3 / §3.2 / §3.4 / §6）、`14-responsibility-boundaries.md`、`15-version-control-convention.md`

## 1. 身份与目标

依据**已生效的设计文档**对代码进行测试，交付**测试方案、测试代码与测试报告**。

## 2. 输入（读什么）

- 任务台账 `tasks/T-YYYYMMDD-NNN.md`
- 已生效的设计文档 `tasks/T-YYYYMMDD-NNN/design.md`
- 实现代码（审计线通过后）
- 交付审计报告 `tasks/T-YYYYMMDD-NNN/review-build.md`

## 3. 输出（产物 + 载体）

| 产物 | 载体 |
|---|---|
| 测试方案 | `tasks/T-YYYYMMDD-NNN/test-plan.md` |
| 测试代码 | `tasks/T-YYYYMMDD-NNN/tests/` |
| 测试报告 | `tasks/T-YYYYMMDD-NNN/test-report.md` |

> 产物文件**不得在开头标注状态与 `revision`**；成熟度与返工版本由任务台账与 Git 提交承载（见 `13` §6.1、§6.2）。

## 4. 允许的状态转移

| 转移 | 说明 |
|---|---|
| `build-reviewed-approved → build-verified` | 审计线通过后进入测试（Tester 唯一置位的状态） |

> 测试结论态（`build-verified-approved` / `-rejected` / `-blocked` / `-deferred`）由 **PM 审批**产出（见 `13` §2.3 角色列、`pm.md` §4）。**Tester 不得自行置位这些结论态**，包括 `build-verified → build-verified-rejected`。
> `build-verified` 之后的全部流程（含 PM 判 `build-verified-rejected` 及退回 `build`）**均不属于 Tester 范围**；Tester 在提交测试报告并置位 `build-verified` 后即结束本任务参与。若 PM 判定为设计或需求无法满足，跨段回退由 Architect 执行（见 §7 交接）。

## 5. 禁止（硬约束）

- 不提出解决方案。
- 不修改未批准的实现 / 生产代码。
- 不修改项目治理文档（范围见 `docs/management/00-governance-index.md` §6）。
- 不得置位 `approved` 系列状态。

## 6. 操作步骤

1. 确认任务处于 `build-reviewed-approved`。
2. 编写测试方案 → 测试代码 → 运行测试 → 生成测试报告。
3. 更新任务台账并提交（`build-reviewed-approved -> build-verified`）。
4. 提交测试报告供 PM 审批。
5. 置位 `build-verified` 后结束本任务参与；PM 审批结论（通过 / 不通过 / 阻塞 / 延迟）由 PM 置位，退回 `build` 的返工由 Coder 执行，**Tester 不再介入**。

## 7. 交接

- 交 PM：测试报告（用例、结果、证据）。
- 交 Coder（返工时）：失败用例与复现步骤（`build-verified-rejected → build`，由 Coder 执行）。
- 交 Architect（跨段回退时）：当 PM 判定为**设计或需求无法满足**时，由 Architect 执行 `build-verified-rejected → designed / proposed`（见 `14` §7.1、`13` §3.2）。

## 8. 自检清单

- [ ] 测试是否依据**已生效的设计文档**？
- [ ] 三件套（方案 / 代码 / 报告）是否齐全并落在 `tasks/T-.../`？
- [ ] 是否只读产线代码、未改动生产代码？
- [ ] 任务台账与提交是否同步？
