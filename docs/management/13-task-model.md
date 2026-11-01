# 13. 任务模型与治理流程

> 状态：生效

本文件定义项目内任务的标识、状态、字段、生命周期和追加记录规则，并规定治理流程中的状态转移、审批与测试流程、审批规则及项目治理文档流程。

## 1. 任务标识

所有任务必须使用统一标识：

```text
T-YYYYMMDD-NNN
```

例如：

```text
T-20261017-001
T-20261017-002
T-20261018-001
```

规则：

- `T` 固定为前缀，表示 Task。
- `YYYYMMDD` 表示任务创建时间日期。
- `NNN` 是当日递增编号。
- 任务编号一旦生成，不得修改。
- 任务 ID 用于所有状态记录、消息、自审和审计。

## 2. 任务状态

任务状态按阶段分为三段：提案段（解决"是否值得做"）、设计段（解决"如何做"）、交付段。
每一段内部又分为三段：生产、审计、批准。
批准是唯一有四种状态的：approved、blocked、rejected、deferred。

blocked 状态时必须明确指出阻塞的条件。当这些条件被消除时，该任务将继续执行——重新开始批准。

deferred 状态时如果没有给出任何说明，那么，下一个任务结束后，无论其是否成功，被 deferred 的这个任务将自动进入执行——重新开始批准。如果给出了需要延迟的排序，那么，在任务列表中的、排在该 deferred 任务之后的任务结束后，无论其是否成功，被 deferred 的这个任务将自动进入执行——重新开始批准。

### 2.1 提案段状态

| 状态 | 含义 | 角色 |
|---|---|---|
| `proposed` | 项目提案（需求说明）已提出。提案只回答"是否值得做"，不包含设计/实现方案 | Architect |
| `proposed-reviewed` | 项目提案完成审计 | Reviewer |
| `proposed-approved` | PM 对提案段审计结论的审批完成，结论为通过，可进入设计阶段 | PM |
| `proposed-blocked` | PM 对提案段审计结论的审批完成，结论为缺少某个条件，条件具备后即可继续。转移到阻塞阶段时必须指明缺少的条件 | PM |
| `proposed-rejected` | PM 对提案段审计结论的审批完成，结论为不被接受，需要修改后重新提交 | PM |
| `proposed-deferred` | PM 对提案段审计结论的审批完成，结论为延迟处理，仅表示排序或优先级关系 | PM |

> `proposed-rejected` 的返工路径：必须修改提案内容，重新提交到 `proposed`。重新进入 `proposed` 后，需重新经历 `proposed-reviewed → proposed-approved` 流程。

> **PM 审批结论状态收口：**  
> PM 的审批结论只能是 `approved / rejected / blocked / deferred` 四态之一。  
> “有条件通过”、“部分通过”、“通过但需补充”等表达不能作为独立审批结论。  
> 若存在条件、缺陷或未满足要求，**不得另创新的审批态**，应转为：
> - 需要修改后重新提交：`rejected`；
> - 缺少某个条件、条件具备后即可继续：`blocked`，并必须在状态记录的原因字段中明确指明缺少的条件。

### 2.2 设计段状态

| 状态 | 含义 | 角色 |
|---|---|---|
| `designed` | 设计/实现方案完成。设计回答"如何做" | Architect |
| `designed-reviewed` | 实现方案完成审计 | Reviewer |
| `designed-approved` | PM 对设计段审计结论的审批完成，结论为通过，可进入交付阶段 | PM |
| `designed-blocked` | PM 对设计段审计结论的审批完成，结论为缺少某个条件，条件具备后即可继续。转移到阻塞阶段时必须指明缺少的条件 | PM |
| `designed-rejected` | PM 对设计段审计结论的审批完成，结论为不被接受，需要修改后重新设计 | PM |
| `designed-deferred` | PM 对设计段审计结论的审批完成，结论为延迟处理，仅表示排序或优先级关系 | PM |

> `designed-rejected` 的返工路径：默认必须修改设计方案，重新提交到 `designed`。重新进入 `designed` 后，需重新经历 `designed-reviewed → designed-approved` 流程。若结论为**需求无法满足**，则回退到 `proposed`（由 Architect 执行），重新审定需求并重新经历提案段流程。
> `proposed-approved → designed` 的入口转移：设计过程本身属于隐藏状态，不单独建模；`designed` 仅表示设计完成、可送审。

### 2.3 交付段状态

| 状态 | 含义 | 角色 |
|---|---|---|
| `build` | 代码已交付 | Coder |
| `build-reviewed` | 实现结果完成审计（审计线） | Reviewer |
| `build-verified` | 实现结果完成测试（测试线，审计批准后进入） | Tester |
| `build-reviewed-approved` | PM 对交付段审计线结论的审批完成，结论为通过 | PM |
| `build-reviewed-blocked` | PM 对交付段审计线结论的审批完成，结论为缺少某个条件，条件具备后即可继续。转移到阻塞阶段时必须指明缺少的条件 | PM |
| `build-reviewed-rejected` | PM 对交付段审计线结论的审批完成，结论为实现不被接受。返工路径：默认返回 `build`，重新交付实现；若结论为**设计或需求无法满足**，则回退到 `designed` 或 `proposed`（由 Architect 执行） | PM |
| `build-reviewed-deferred` | PM 对交付段审计线结论的审批完成，结论为延迟处理，仅表示排序或优先级关系 | PM |
| `build-verified-approved` | PM 对交付段测试线结论的审批完成，结论为通过 | PM |
| `build-verified-blocked` | PM 对交付段测试线结论的审批完成，结论为缺少某个条件，条件具备后即可继续。转移到阻塞阶段时必须指明缺少的条件 | PM |
| `build-verified-rejected` | PM 对交付段测试线结论的审批完成，结论为不通过。返工路径：默认返回 `build`（**由 Coder 执行**），修复缺陷并重新交付；若结论为**设计或需求无法满足**，则回退到 `designed` 或 `proposed`（由 Architect 执行） | PM |
| `build-verified-deferred` | PM 对交付段测试线结论的审批完成，结论为延迟处理，仅表示排序或优先级关系 | PM |

> `in_progress` 状态废止：执行属于隐藏状态，不在文本中展现；交付前任务在书面上保持其门禁通过状态。
> 所有 `deferred` 状态仅表示排序或优先级关系，不依赖其他任务完成。

## 3. 任务状态机

### 3.1 状态机图

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
  └── build-reviewed
       └── build-reviewed-approved
            └── build-verified
                 └── build-verified-approved
```

### 3.2 主要允许转移

| 当前状态 | 允许后续状态 | 条件 |
|---|---|---|
| `proposed` | `proposed-reviewed` | 提案完成审计 |
| `proposed-reviewed` | `proposed-approved` | 审计结论：通过 |
| `proposed-reviewed` | `proposed-rejected` | 审计结论：提案不被接受 |
| `proposed-reviewed` | `proposed-blocked` | 审计发现阻塞项 |
| `proposed-reviewed` | `proposed-deferred` | 提案延迟处理 |
| `proposed-approved` | `designed` | 设计完成，可进入审计（设计过程为隐藏状态） |
| `designed` | `designed-reviewed` | 设计完成审计 |
| `designed-reviewed` | `designed-approved` | 审计结论：通过 |
| `designed-reviewed` | `designed-rejected` | 审计结论：方案不被接受 |
| `designed-reviewed` | `designed-blocked` | 审计发现阻塞项 |
| `designed-reviewed` | `designed-deferred` | 设计延迟处理 |
| `designed-rejected` | `designed` | 需重新修改设计方案并重新进入设计 |
| `designed-rejected` | `proposed` | 需求无法满足，需回退提案段重新审定需求（**由 Architect 执行**） |
| `designed-approved` | `build` | 进入交付，代码交付 |
| `build` | `build-reviewed` | 实现结果送交审计 |
| `build-reviewed` | `build-reviewed-approved` | 审计结论：通过 |
| `build-reviewed` | `build-reviewed-rejected` | 审计结论：实现不被接受 |
| `build-reviewed` | `build-reviewed-blocked` | 审计发现阻塞项 |
| `build-reviewed` | `build-reviewed-deferred` | 审计延迟处理 |
| `build-reviewed-rejected` | `build` | 需重新交付实现 |
| `build-reviewed-rejected` | `designed` | 设计方案无法满足，需回退设计段重新审定设计（**由 Architect 执行**） |
| `build-reviewed-rejected` | `proposed` | 需求无法满足，需回退提案段重新审定需求（**由 Architect 执行**） |
| `build-reviewed-approved` | `build-verified` | 审计线通过，进入测试阶段 |
| `build-verified` | `build-verified-approved` | 测试结论：通过 |
| `build-verified` | `build-verified-rejected` | 测试结论：不通过 |
| `build-verified` | `build-verified-blocked` | 测试发现阻塞项 |
| `build-verified` | `build-verified-deferred` | 测试延迟处理 |
| `build-verified-rejected` | `build` | 需重新测试或修复（**由 Coder 执行**） |
| `build-verified-rejected` | `designed` | 设计方案无法满足，需回退设计段重新审定设计（**由 Architect 执行**） |
| `build-verified-rejected` | `proposed` | 需求无法满足，需回退提案段重新审定需求（**由 Architect 执行**） |

> 各转移的执行角色见 `12-multi-agent-roles.md`《角色边界》与 §4《审批状态转移》。

### 3.3 禁止转移

```text
未列入允许转移表的转移一律禁止。
proposed 不能直接变为 designed。
designed 不能直接变为 build。
无审计结论时，状态不得跳过审计门禁。
被拒状态不得绕过返工路径直接进入下一段：
  - proposed-rejected 不能直接变为 designed。
  - designed-rejected 不能直接变为 build。
  - build-reviewed-rejected 不能直接变为 build-verified。
  - build-verified-rejected 不能直接变为 build-reviewed。
段间转移不得绕过审计门禁：
  - designed-reviewed 不能直接变为 build。
  - build-reviewed 不能直接变为 build-verified。
测试线必须在审计线批准后进入：
  - build 不能直接进入 build-verified。
  - build-verified 不能直接进入 build-reviewed。
  - 测试线不会反过来回退到审计阶段。
```

### 3.4 恢复转移规则

| 当前状态 | 恢复后状态 | 条件 |
|---|---|---|
| `proposed-blocked` | `proposed-blocked` | 阻塞条件已消除，重新进入批准流程，批准结果是继续阻塞 |
| `proposed-blocked` | `proposed-deferred` | 阻塞条件已消除，重新进入批准流程，批准结果是延期 |
| `proposed-blocked` | `proposed-approved` | 阻塞条件已消除，重新进入批准流程，批准结果是通过 |
| `proposed-blocked` | `proposed-rejected` | 阻塞条件已消除，重新进入批准流程，批准结果是不接受 |
| `proposed-deferred` | `proposed-deferred` | 延迟处理结束，重新进入批准流程，批准结果是延期 |
| `proposed-deferred` | `proposed-approved` | 延迟处理结束，重新进入批准流程，批准结果是通过 |
| `proposed-deferred` | `proposed-rejected` | 延迟处理结束，重新进入批准流程，批准结果是不接受 |
| `proposed-deferred` | `proposed-blocked` | 延迟处理结束，重新进入批准流程，批准结果是继续阻塞 |
| `designed-blocked` | `designed-blocked` | 阻塞条件已消除，重新进入批准流程，批准结果是继续阻塞 |
| `designed-blocked` | `designed-deferred` | 阻塞条件已消除，重新进入批准流程，批准结果是延期 |
| `designed-blocked` | `designed-approved` | 阻塞条件已消除，重新进入批准流程，批准结果是通过 |
| `designed-blocked` | `designed-rejected` | 阻塞条件已消除，重新进入批准流程，批准结果是不接受 |
| `designed-deferred` | `designed-deferred` | 延迟处理结束，重新进入批准流程，批准结果是延期 |
| `designed-deferred` | `designed-approved` | 延迟处理结束，重新进入批准流程，批准结果是通过 |
| `designed-deferred` | `designed-rejected` | 延迟处理结束，重新进入批准流程，批准结果是不接受 |
| `designed-deferred` | `designed-blocked` | 延迟处理结束，重新进入批准流程，批准结果是继续阻塞 |
| `build-reviewed-blocked` | `build-reviewed-blocked` | 阻塞条件已消除，重新进入批准流程，批准结果是继续阻塞 |
| `build-reviewed-blocked` | `build-reviewed-deferred` | 阻塞条件已消除，重新进入批准流程，批准结果是延期 |
| `build-reviewed-blocked` | `build-reviewed-approved` | 阻塞条件已消除，重新进入批准流程，批准结果是通过 |
| `build-reviewed-blocked` | `build-reviewed-rejected` | 阻塞条件已消除，重新进入批准流程，批准结果是不接受 |
| `build-reviewed-deferred` | `build-reviewed-deferred` | 延迟处理结束，重新进入批准流程，批准结果是延期 |
| `build-reviewed-deferred` | `build-reviewed-approved` | 延迟处理结束，重新进入批准流程，批准结果是通过 |
| `build-reviewed-deferred` | `build-reviewed-rejected` | 延迟处理结束，重新进入批准流程，批准结果是不接受 |
| `build-reviewed-deferred` | `build-reviewed-blocked` | 延迟处理结束，重新进入批准流程，批准结果是继续阻塞 |
| `build-verified-blocked` | `build-verified-blocked` | 阻塞条件已消除，重新进入批准流程，批准结果是继续阻塞 |
| `build-verified-blocked` | `build-verified-deferred` | 阻塞条件已消除，重新进入批准流程，批准结果是延期 |
| `build-verified-blocked` | `build-verified-approved` | 阻塞条件已消除，重新进入批准流程，批准结果是通过 |
| `build-verified-blocked` | `build-verified-rejected` | 阻塞条件已消除，重新进入批准流程，批准结果是不接受 |
| `build-verified-deferred` | `build-verified-deferred` | 延迟处理结束，重新进入批准流程，批准结果是延期 |
| `build-verified-deferred` | `build-verified-approved` | 延迟处理结束，重新进入批准流程，批准结果是通过 |
| `build-verified-deferred` | `build-verified-rejected` | 延迟处理结束，重新进入批准流程，批准结果是不接受 |
| `build-verified-deferred` | `build-verified-blocked` | 延迟处理结束，重新进入批准流程，批准结果是继续阻塞 |

## 4. 审批状态转移

审批贯穿三段门禁与两条交付线，各段同型：

```text
提案审批：proposed-reviewed → proposed-approved / proposed-rejected / proposed-blocked / proposed-deferred
提案被拒后：proposed-rejected → proposed  (重新提交提案重新审计)

设计审批：designed-reviewed → designed-approved / designed-rejected / designed-blocked / designed-deferred
设计被拒后：designed-rejected → designed  (重新设计后重新审计)
              designed-rejected → proposed  (需求无法满足，回退提案段；由 Architect 执行)

交付审批（审计线）：build-reviewed → build-reviewed-approved / build-reviewed-rejected / build-reviewed-blocked / build-reviewed-deferred
交付审批（测试线）：build-verified → build-verified-approved / build-verified-rejected / build-verified-blocked / build-verified-deferred
交付被拒后：build-reviewed-rejected → build  (重新交付后重新审计)
              build-reviewed-rejected → designed  (设计无法满足，回退设计段；由 Architect 执行)
              build-reviewed-rejected → proposed  (需求无法满足，回退提案段；由 Architect 执行)
              build-verified-rejected → build  (由 Coder 执行：修复缺陷并重新交付)
              build-verified-rejected → designed  (设计无法满足，回退设计段；由 Architect 执行)
              build-verified-rejected → proposed  (需求无法满足，回退提案段；由 Architect 执行)
```

说明：

```text
PM 根据审计、测试的结论进行审批。

各审批段中，rejected 状态后的返工路径默认回退至对应段起点；结论为设计或需求无法满足时，回退至更早的段（由 Architect 执行），见 §3.2。
```

## 5. 任务字段

每个任务至少包含以下字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `task_id` | string | 任务唯一标识 |
| `title` | string | 任务标题 |
| `description` | string | 任务背景、目标和范围 |
| `status` | string | 当前状态 |
| `created_at` | ISO 8601 | 创建时间 |
| `updated_at` | ISO 8601 | 最后更新时间 |
| `revision` | integer | 任务修订号，从 `1` 开始 |
| `assignees` | object | 责任人和角色 |
| `input_contracts` | array | 任务依赖的输入 |
| `output_contracts` | array | 任务产出 |
| `dependencies` | array | 依赖的其他任务 ID |
| `approval_chain` | object | 审批、执行、验证链路 |
| `risk` | string | 风险和限制 |

### 5.1 责任人字段

推荐使用角色标签和参与者 ID 组合：

```json
{
  "proposer": "Architect:Qoder-A",
  "reviewer": "PM:Cline",
  "executor": "Coder:opencode",
  "verifier": "Tester:kilo"
}
```

说明：

| 字段 | 含义 |
|---|---|
| `proposer` | 提出任务的人 |
| `reviewer` | 负责评审方案的人 |
| `executor` | 负责落地实现的人 |
| `verifier` | 负责验证产物的人 |

## 6. 任务产物（交付物）

每个状态对应明确的交付物、生产者与载体。载体路径中的 `T-XXXX` 指具体任务 ID。

| 状态 | 交付物 | 生产者 | 载体 |
|---|---|---|---|
| `proposed` | 需求说明（提案） | Architect | `tasks/T-XXXX/proposal.md` |
| `proposed-reviewed` | 提案审计报告 | Reviewer | `tasks/T-XXXX/review-proposal-report.md` |
| `proposed-approved` | 审批结论 | PM | 任务台账（见 §10 状态记录格式） |
| `designed` | 设计方案（实现方案） | Architect | `tasks/T-XXXX/design.md` |
| `designed-reviewed` | 设计审计报告 | Reviewer | `tasks/T-XXXX/review-design-report.md` |
| `designed-approved` | 审计结论 | PM | 任务台账 |
| `build` | 代码 + 代码相关文档 | Coder | 仓库代码文件 + 相关 `docs/` |
| `build-reviewed` | 交付审计报告 | Reviewer | `tasks/T-XXXX/review-build-report.md` |
| `build-reviewed-approved` | 审计结论 | PM | 任务台账 |
| `build-verified` | 测试验收报告 | Tester | `tasks/T-XXXX/test-plan.md`、`tasks/T-XXXX/tests/`、`tasks/T-XXXX/test-report.md` |
| `build-verified-approved` | 审计结论 | PM | 任务台账 |
| `build-verified-rejected` | 审计报告 | PM | 任务台账、`tasks/T-XXXX/build-decision.md` |
| `build-verified-blocked` | 审计报告 | PM | `tasks/T-XXXX/build-decision.md` |
| `build-verified-deferred` | 审计报告 | PM | `tasks/T-XXXX/build-decision.md` |

> 注：本表描述「状态 → 交付物」的对应关系，**不记录成熟度**；各状态的成熟度见 §6.1，其记录载体为任务台账与 Git 提交。

### 6.1 产物成熟度（五级）

成熟度**不**由产物文件标注；成熟度由**任务台账**与 **Git 提交**联合保存。各状态的成熟度如下：

| 级 | 成熟度 | 含义 | 达到条件（状态变体） |
|---|---|---|---|
| 1 | 供审计稿 | 已提交、进入审计与审批流程 | `proposed`（提案）/`designed`（设计）/`build`（代码交付） |
| 2 | 审计稿 | 审计已完成，审计结论已出具 | `proposed-reviewed`／`designed-reviewed`／`build-reviewed` |
| 3 | 审定稿 | 对审计阶段的审批已完成（文档类） | `proposed-approved`／`designed-approved` |
| 4 | 测试验收稿 | 测试验收已完成 | `build-verified` |
| 5 | 最终稿 | 对测试验收的审批已完成，为最终结论 | `build-verified-approved` |

> 记录说明：任务台账的 `status:` 行与状态记录行记录当前状态；每一步状态转移对应一次 Git 提交；提交信息与 trailer（`Task-Id`／`Actor`／`State-From`／`State-To`）携带状态移行详情。**产物文件本身不得写入与成熟度相关的状态标注。**

### 6.2 版本与返工规则（由任务台账 + Git 承载）

**产物文件**（`proposal.md`、`design.md`、`test-report.md`、源码文件等）**不得在文件头标注成熟度或状态**。版本与返工方式如下：

- **返工版本号`revision`**：由任务台账的 `revision:` 字段记录，返工时递增；提交信息必须说明“第 N 轮返工”。
- **返工采用同文件覆盖**：产物在原载体上就地修订，不新建 `proposal-v2.md` 等文件；版本历史由 Git 保留（`git log` / `git diff` 可追溯每轮返工的差异）。
- **载体路径一经确定不再变更**：草案阶段即写入最终路径，送审后不改路径；状态升级不改路径，只改台账与 Git 记录。

### 6.3 其他说明

- Architect 产出一律**直接落盘到最终载体**；在 `Drafting proposal` 阶段，文件直接落到 `tasks/T-XXXX/proposal.md`，不经过“状态标注”环节。
- Reviewer 审计上述全部产物（提案、设计、代码与代码相关文档），产出对应审计报告。
- Tester 测试代码，产出测试方案、测试代码与测试报告。
- PM 审批**每一份**审计报告与测试报告；审批结论和状态转移记录在任务台账的状态记录行中。
- 载体路径、提交与追溯约定见 `15-version-control-convention.md`。

## 7. 任务生命周期

### 7.1 任务起点

任务的产生有两种场景：

1. 用户与架构师讨论需求，架构师认为该需求有存在的意义、且未被现有其他项目满足；
2. 架构师在进行技术方案 / 实现方案设计时，认为应将现有项目分解为若干子任务。

两种场景下，任务在正式化之前处于**隐藏状态 `Drafting proposal`（提案中）**：架构师与用户讨论项目提案 / 需求说明。**该阶段的草案直接落盘到最终载体** `tasks/T-XXXX/proposal.md`，**不在文件内标注任何状态或 `revision`**；用户明确同意提案后，架构师将状态置为 `proposed`，下一流程进入提案审计（`proposed → proposed-reviewed`）。**不设草稿专用目录**（见 §6.1）。

架构师与用户确认提案后，将状态置为 `proposed`，下一流程进入提案审计（`proposed → proposed-reviewed`）。用户对提案的确认属于 Architect 的内部工作规范，不进入 PM / Reviewer 的审批链路，PM 不对该环节出具审批结论。

> `proposed` 状态的提交人是 **Architect**（在用户确认提案后置位）；**审批人**为 **PM**，在 `proposed-reviewed` 之后依据 Reviewer 的审计报告进行四态审批。用户对提案的确认属于 Architect 的内部工作规范，不作为 PM / Reviewer 的检查环节，也不在任务台账中设置单独核对项。

### 7.2 任务终点

任务的终态为 `verified`（即 `build-verified-approved`），到达即表示**任务完成**；**最终验收等同于任务完成**。

### 7.3 失败与返工

`blocked` / `rejected` / `deferred` 的含义与处理见 §2 与 §3.4 恢复转移规则。

任务主链如下：

```text
proposed → proposed-reviewed → proposed-approved → designed
        → designed-reviewed → designed-approved → build
        → build-reviewed → build-reviewed-approved → build-verified
        → build-verified-approved
```

常见分支：

```text
proposed-reviewed → proposed-rejected / proposed-blocked / proposed-deferred
proposed-rejected → proposed                            （重新提交提案后重新审计）

designed-reviewed → designed-rejected / designed-blocked / designed-deferred
designed-rejected → designed                            （重新设计后重新审计）
designed-rejected → proposed                           （需求无法满足，回退提案段；由 Architect 执行）

build-reviewed → build-reviewed-rejected / build-reviewed-blocked / build-reviewed-deferred
build-reviewed-rejected → build                           （重新交付后重新审计）
build-reviewed-rejected → designed                       （设计无法满足，回退设计段；由 Architect 执行）
build-reviewed-rejected → proposed                       （需求无法满足，回退提案段；由 Architect 执行）
build-reviewed-approved → build-verified                  （审计通过，进入测试阶段）

build-verified → build-verified-rejected / build-verified-blocked / build-verified-deferred
build-verified-rejected → build                          （由 Coder 执行：修复缺陷并重新交付）
build-verified-rejected → designed                      （设计无法满足，回退设计段；由 Architect 执行）
build-verified-rejected → proposed                      （需求无法满足，回退提案段；由 Architect 执行）
```

> `build-verified` 及其四个结论态由 **PM 审批**产出（见 §2.3 角色列）；Tester 只置位 `build-reviewed-approved → build-verified`。PM 判 `build-verified-rejected` 后的返工**默认由 Coder 执行**（退回 `build`），Tester 不再介入；若结论为设计或需求无法满足，则由 Architect 执行回退（退回 `designed` 或 `proposed`）。

每次状态转移都必须附带一条追加记录。

## 8. 项目治理文档流程

```text
PM 编写项目治理文档
  ↓
用户审批项目治理文档
```

说明：

```text
PM 负责编写项目治理文档。
用户对项目治理文档进行审批。
```

## 9. 完整流程示例

```text
Architect:Qoder-A 提出任务 T-YYYYMMDD-NNN（proposed，仅需求说明）
  ↓
Reviewer 提案审计（proposed-reviewed）
  ↓
PM 审批提案（proposed-approved）
  ↓
Architect:Qoder-A 完成设计（designed）
  ↓
Reviewer 设计审计（designed-reviewed）
  ↓
PM 审批设计（designed-approved）
  ↓
Coder:opencode 交付代码（build）
  ↓
Reviewer 审计实现结果（build-reviewed）
  ↓
PM 审批审计线结论（build-reviewed-approved）
  ↓
Tester 测试实现结果（build-verified）
  ↓
PM 审批测试线结论（build-verified-approved）
  ↓
  终态（build-verified-approved）
```

## 10. 状态记录格式

> 状态记录的**载体**是任务台账文件 `tasks/T-XXXX.md`；提交与追溯约定见 `15-version-control-convention.md`。

状态变化记录格式为：

```text
T-YYYYMMDD-NNN <旧状态> -> <新状态> by <角色>:<参与者ID> | <原因/动作>
```
> 审批结论状态必须是四态之一：`approved / rejected / blocked / deferred`。  
> 不得使用“有条件通过”“部分通过”“通过但需补充”等非四态结论字样。  
> 若为 `rejected` 或 `blocked`，应在原因字段中指明本次不满足的条件或缺少的条件。

示例：

```text
T-20261017-001 proposed -> proposed-reviewed by Reviewer:copilot | 提案审计完成
T-20261017-001 proposed-reviewed -> proposed-approved by PM:Cline | decision=提案通过
T-20261017-001 designed -> designed-reviewed by Reviewer:copilot | 设计审计完成
T-20261017-001 designed-reviewed -> designed-approved by PM:Cline | decision=方案通过
T-20261017-001 build -> build-reviewed by Reviewer:copilot
T-20261017-001 build-reviewed-approved -> build-verified by Tester:kilo
```

角色标签可以是：

| 角色标签 | 说明 |
|---|---|
| `PM` | 项目经理 / 审批人 |
| `Architect` | 架构师 |
| `Coder` | 代码编写者 |
| `Tester` | 测试者 |
| `Reviewer` | 审查员 |

## 11. 追加记录规则

> 追加记录的**载体**是任务台账文件 `tasks/T-XXXX.md`；**时机**为每步一提交，见 `15-version-control-convention.md`。

任务状态变化必须追加记录，不覆盖历史。

每条记录至少包含：

| 字段 | 说明 |
|---|---|
| `task_id` | 任务 ID |
| 旧状态 | 转移前状态 |
| 新状态 | 转移后状态 |
| `actor` | 触发状态改变的人或系统 |
| `reason` | 原因或动作说明 |

示例：

```text
T-20261017-001 proposed-reviewed -> proposed-approved by PM:Cline | 审批结论=approved
T-20261017-001 designed-reviewed -> designed-blocked by Reviewer:copilot | 审批结论=blocked；缺少索引审定版本
```

## 12. 最小变更约束

1. 只新增任务模型相关文件。
2. 不删除或重写已有管理文档。
3. 历史记录只追加，不覆盖。
4. 不引入外部任务系统。
5. 新任务必须有明确的 `input_contracts`、`output_contracts` 和 `assignees`。

---

## 附录 A 旧状态词汇与新词汇对照

| 旧状态词汇 | 新状态词汇 | 说明 |
|---|---|---|
| `in_progress` | `build`（隐藏状态） | 执行属于隐藏状态，不单独建模 |
| `reviewed` | `*-reviewed` | 归并至各段 reviewed 状态 |
| `approved` | `*-approved` | 归并至各段 approved 状态 |
| `rejected` | `*-rejected` | 归并至各段 rejected 状态 |
| `completed` | `build-verified-approved` | 全局终态 |
| `verified` | `build-verified-approved` | 测试通过后进入终态 |

历史记录切换点：自本文件生效之日起，新任务采用新状态词汇；历史任务保留原状态词汇，跨系统迁移时按上表映射。