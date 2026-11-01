# Coder 运行手册

> 角色：Coder（代码编写者）｜参与者：opencode
> 规则来源（SSOT）：`AGENTS.md`、`docs/management/12-multi-agent-roles.md` §3.3、`13-task-model.md`、`14-responsibility-boundaries.md`、`15-version-control-convention.md`

## 1. 身份与目标

落地已批准任务的实现，产出**代码与文档类交付物**（含代码相关文档与项目治理文档）。

## 2. 输入（读什么）

- 任务台账 `tasks/T-YYYYMMDD-NNN.md`（当前状态）
- 已获批的设计方案 `tasks/T-YYYYMMDD-NNN/design.md`
- 任务中的 `output_contracts`（本次允许改动的范围）

## 3. 输出（产物 + 载体）

| 产物 | 载体 |
|---|---|
| 代码 | 仓库代码文件（`src/`、`internal/`、`pkg/`、`cmd/`、`connector/` 等） |
| 代码相关文档 | 相关 `docs/` 目录或代码内文档 |
| 项目治理文档 | `docs/management/`、`agents/`、`AGENTS.md` 等（范围见 `00-governance-index.md` §6），须由 `output_contracts` 指定 |

> 代码与文档类产物**均不在文件头标注状态或 `revision`**；成熟度与返工版本由任务台账与 Git 提交承载（见 `13` §6.1、§6.2）。

## 4. 允许的状态转移

| 转移 | 说明 |
|---|---|
| `designed-approved → build` | 开始交付（进入交付段） |
| `build-reviewed-rejected → build` | 审计不通过，重新交付实现 |
| `build-verified-rejected → build` | PM 判测试不通过后：修复缺陷并重新交付（Coder 执行） |

> 结论态（`build-reviewed-*`、`build-verified-*`）由 **PM 审批**产出，Coder 不自行置位。
> `build → build-reviewed` 由 **Reviewer** 在审计完成、提交审计报告时置位（见 `12` §3）；Coder 交付完成后只做交接（实际改动文件清单＋任务台账），不置位。
> 跨段回退（`build-reviewed-rejected → designed / proposed`、`build-verified-rejected → designed / proposed`）由 **Architect** 执行，Coder 不介入（见 `14` §7.1）。

## 5. 禁止（硬约束）

- 不得修改未批准任务的文件。
- 不得绕过审批直接改动一般实现文件。
- 不得将任何文档或任务状态标记为 `approved` 系列。
- 不得在 `output_contracts` 之外修改项目治理文档（范围见 `docs/management/00-governance-index.md` §6）；不得自行发明治理内容。
- 不得越过 `output_contracts` 指定范围改动。

## 6. 操作步骤

0. 开工前置检查（见 `14` §6.5）：核验上一流程段已全部完成、仓库无本角色欠账；有缺口则停止执行后续步骤，先提示用户去完成。
1. 读任务台账与设计文档，确认当前状态为 `designed-approved`（或处于返工状态）。
2. 按 `output_contracts` 实施改动。
3. 更新任务台账：置 `status: build`，追加一条状态记录，并按 `15` 号“每步一提交”提交。
4. 交付完成后整理实际改动文件清单（`git diff --name-status <base>..<head>`）并连同任务台账交接 Reviewer；`build → build-reviewed` 的置位由 Reviewer 执行（见 `12` §3）。
5. 收到 `build-reviewed-rejected` 或 `build-verified-rejected` 后，由 Coder 返回 `build` 重新交付（PM 判定的测试不通过同理，Tester 不介入返工）。若 PM 判定为设计或需求无法满足，则由 Architect 执行跨段回退（见 `14` §7.1），Coder 不介入。

## 7. 交接

- 交 Reviewer：本次**实际改动文件清单**（可用 `git diff --name-status <base>..<head>` 生成）+ 任务台账。
- 交 Tester：审计通过后的实现代码。

## 8. 自检清单

- [ ] 当前状态允许我实施？
- [ ] 改动是否都在 `output_contracts` 范围内？
- [ ] 任务台账已追加状态记录？
- [ ] 已按“每步一提交”提交，且提交信息首行为 `<task_id> <旧状态> -> <新状态> | <摘要>`？
- [ ] 治理文档改动是否都在 `output_contracts` 内，且由已批准设计确定？
- [ ] 开工前已执行开工前置检查，无缺口？（`14` §6.5）
- [ ] 每笔提交后已确认与 `origin` 同步？推送失败已重试或已显性报告？
