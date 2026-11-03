# T-20261102-001 设计段审批报告

- 任务：T-20261102-001 治理变更—PM 审批报告落盘范围与命名定性
- 审批对象：`tasks/T-20261102-001/design.md`
- 审批依据：`tasks/T-20261102-001/review-design-report.md`（Reviewer:copilot 设计审计报告）
- 审批人：PM:Cline
- 审批阶段：`designed-reviewed`
- **审批结论：`rejected`**

---

## 1. 问题

**P0 阻断项**

- `tasks/T-20261102-001/design.md` §11（R-4「用户拒绝批准」条目）——状态映射与条款引用错误。R-4 将「用户拒绝批准」对应到 `build-verified-blocked/deferred` 并引用 `13` §3.4；实测 §3.4 规定的是「已有 blocked 状态的恢复转移」，从 `build-verified` 进入结论态的允许转移在 §3.2（`13:174-177`）。且 `13` §2.4.1 明定：若需修改本任务文件，不得判 `blocked`（否则违 §2.4.2 文件冻结），应判 `rejected`；`deferred` 表排序/优先级，与「拒绝」语义不符。修改建议：删除 §3.4 引用，按 §3.2 重写；「用户拒绝批准」正确落点为 `build-verified-rejected`（必要时回退设计/提案段），并按 §2.4.1 排除 `blocked`。

**P1 应修项**

- `tasks/T-20261102-001/design.md` §4（M-11）——未给出可审定、可执行的变更文本。M-11 仅称「在 `15` 附录 B 新增一行、同型字段、内容指向 M-1～M-9」，未给字段值或拟写内容；而 M-10 已给完整行文本。依 `14` §6.4，Coder 须按已批准设计落盘、不得自行发明文本，故 M-11 不足以作为无歧义交付输入。修改建议：比照 M-10，补出 `15` 附录 B 新增行的完整字段文本。
- `tasks/T-20261102-001/design.md` §11（回滚订正载体，审计 P2-1）——设计将 `git revert` 降为应急路径、称正式订正应「追加变更行＋订正记录行」，但未定义订正记录行的载体与形制；§6 又指出既存状态记录格式不允许无状态转移注记行，相关载体仍列戊-5 待裁。修改建议：在设计中显式闭合（纳入戊-5，或在 §11 直写载体）。

**P2 建议项**

- `tasks/T-20261102-001/design.md` §10（七项须裁戊-1～戊-7 未决）——其中戊-1（`AGENTS.md:27` 扩围）、戊-2（`13` §6 补列）属 `output_contracts` 范围裁定；未决则目标四一致性与对应验收判据（J1 的 AGENTS.md 行、戊-2 补列行）不能启用。建议：返工时先取得裁定，或将每个选项收敛为「择一即闭合」的形态。

---

## 2. 审计意见核对表（对照 `review-design-report.md`）

| # | 审计意见 | 处置 | 理由 |
|---|---|---|---|
| 1 | **P1**「用户拒绝时状态及引用不符状态模型」 | **修复** | 见 §1 P0；返工 Architect |
| 2 | **P1**「M-11 未给出可审定文本」 | **修复** | 见 §1 P1；返工 Architect |
| 3 | **P2**「回滚后订正载体与裁定项未闭合」 | **修复** | 见 §1 P1；可并入戊-5 |
| — | 审计「总体判断：当前稿不足以作为无歧义 build 输入」 | **采纳** | — |

---

## 3. 审计覆盖缺口

| 领域／对象 | 是否已审计 | 未覆盖原因 | 建议审计对象与时机 |
|---|---|---|---|
| 实际修改后的规则文本（J1–J8 判据落实） | 未覆盖 | 尚未 build | 交付段 `build-verified` |
| 审批报告公开披露边界（戊-6） | 未覆盖 | 待裁 | 设计段修订 / 用户裁定后 |
| 戊-1～戊-7 条件扩围对 `output_contracts` 与验收范围的影响 | 未覆盖 | 未作选择 | 设计段修订时 |

---

## 4. 结论、条件与返工

- **结论**：`rejected`（方案不被接受，需修改后重新设计）。**非 `blocked`**——依 `13` §2.4.1，本设计需修改其 `output_contracts` 内文件，禁用 `blocked`。
- **条件**：无（非 `blocked`）。
- **返工归属**：**Architect:Qoder-A**，同段返工 `designed-rejected -> designed`（`13` §3.2）。

## 5. 返工裁定记录（戊-1～戊-7；已由 PM/用户裁定，2026-11-03）

| 项 | 议题 | 裁定 | 需动作 |
|---|---|---|---|
| 戊-1 | `AGENTS.md:27` 是否扩围 | **追认纳入** | 无（已随提交 `1ddeb4e` 实施） |
| 戊-2 | `13` §6 表是否补列审批报告 | **纳入** | 改 `13` §6（见 §6.2）＋ 台账 `output_contracts` 扩围 |
| 戊-3 | `build-decision.md` 归口 | **并存＋交叉引用** | 改 `14` §6.2（见 §6.3） |
| 戊-4 | 变更行「生效时间」列填写时机 | **维持「经用户批准后生效」** | 无 |
| 戊-5 | 改名事实的记录载体 | **甲**：记入 `T-20261102-001` 的 build 记录行原因字段（`T-20261020-001.md` 零改动） | 待 build 行（见 §6.6） |
| 戊-6 | 审批报告内容边界／公开披露 | **增入**内容边界句 | 改 `14` §6.2（见 §6.4） |
| 戊-7 | 生效前各段审批报告落盘者 | **追认已解决** | 无（PM 已补落本任务 proposal／design 两份报告） |

## 6. 返工规格（Architect 须写入修订稿；精确文本）

### 6.1 修 P0 — R-4（`design.md` §11 现 `:173` 整行替换为）

```markdown
- R-4 用户拒绝批准：文本已落盘但未生效 ⇒ 处置为在 M-10 变更行追加「未生效」说明行（新增行，不改既存行）；任务按 `13` §3.2 由 `build-verified` 判 `build-verified-rejected`（**不适用 `blocked`**——依 `13` §2.4.1，需修改本任务文件时不得判 `blocked`；`deferred` 表排序，非拒绝）；若结论为设计/需求无法满足，则回退 `designed`／`proposed`（由 Architect 执行）。
```

### 6.2 戊-2 — `docs/management/13-task-model.md` §6 交付物表

四行 PM 结论行的「载体」补列审批报告：

```markdown
| `proposed-approved` | 审批结论 | PM | 任务台账；`tasks/T-XXXX/proposal-approval-report.md` |
| `designed-approved` | 审计结论 | PM | 任务台账；`tasks/T-XXXX/design-approval-report.md` |
| `build-reviewed-approved` | 审计结论 | PM | 任务台账；`tasks/T-XXXX/build-reviewed-approval-report.md` |
| `build-verified-approved` | 审计结论 | PM | 任务台账；`tasks/T-XXXX/build-verified-approval-report.md` |
```

并在该表下方加注（覆盖四态，避免为每个结论态逐一加行）：

```markdown
> PM 的四态结论（`approved`／`rejected`／`blocked`／`deferred`）均产出审批报告，统一落盘为 `tasks/T-XXXX/<阶段>-approval-report.md`（命名对照见 `14` §6.2）；本表仅列载体主项。
```

> 配套：本任务 `output_contracts` 扩围至 `docs/management/13-task-model.md`（字段订正，`15` §4.3.5）。

### 6.3 戊-3 — `docs/management/14-responsibility-boundaries.md` §6.2（对照表后加句）

```markdown
> `build-verified` 线的返工／阻塞／延迟决定另见 `13` §6 的 `tasks/T-XXXX/build-decision.md`；该形制与本节的 `<阶段>-approval-report.md` **并存，不互替**。
```

### 6.4 戊-6 — `docs/management/14-responsibility-boundaries.md` §6.2（加一条）

```markdown
- 审批报告仅载审计意见处置、四态结论、审计覆盖缺口与返工归属，**不得含凭据、密钥或未脱敏数据**（本仓库为公开仓库，审批报告随提交即公开）。
```

### 6.5 对齐「已实施」现实（必须——否则审计将再次判「设计与仓库不符」）

在 `design.md` §0 基线或 §8 交付顺序注明：

```markdown
> 变更项 M-1～M-11 已由**用户直接授权**实施（提交 `1ddeb4e`）；`tasks/T-20261020-001/approval-report.md` 已 `git mv` 改名为 `proposal-approval-report.md`。本设计稿据此修订，描述**已发生的实施**，不再表述为「待实施」。
```

### 6.6 戊-5 — 记录行文本（待 build 记录行存在时写入 `T-20261102-001` 记录行原因字段；`T-20261020-001.md` 不动）

```text
… | 交付：依用户裁定对 tasks/T-20261020-001/approval-report.md 执行 git mv 改名（一次性例外覆盖 13 §6.2，例外不入规则文本）；并落戊-1/戊-2/戊-3/戊-6 治理改动
```

## 7. 状态转移（返工入口）

```text
designed-rejected -> designed           by Architect:Qoder-A | 按本报告 §5／§6 修订 design.md 并置 designed
designed -> designed-reviewed           by Reviewer:copilot   | 设计审计
designed-reviewed -> designed-approved  by PM:Cline           | 审批通过
```

---

> 本报告为**任务产物**，落盘于 `tasks/T-20261102-001/design-approval-report.md`，不属于项目治理文档。
> 依据：`12` §3.1 PM 输出、`14` §5.1 审批范围、`14` §6.2 审批报告落盘。
