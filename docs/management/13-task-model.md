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
| `proposed` | 项目提案（需求说明）已提出。提案只回答"是否值得做"，不包含设计/实现方案。`has_code` 的声明属**交付范围自陈**，不属本句所排除的设计／实现方案（判定规则见 §5.2） | Architect |
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
| `build-verified` | 实现结果完成测试（测试线，审计批准后进入；**仅 `has_code = true` 的任务进入**） | Tester |
| `build-reviewed-approved` | PM 对交付段审计线结论的审批完成，结论为通过；`has_code = false` 的任务到此即为终态（见 §7.2） | PM |
| `build-reviewed-blocked` | PM 对交付段审计线结论的审批完成，结论为缺少某个条件，条件具备后即可继续。转移到阻塞阶段时必须指明缺少的条件 | PM |
| `build-reviewed-rejected` | PM 对交付段审计线结论的审批完成，结论为实现不被接受。返工路径：默认返回 `build`，重新交付实现；若结论为**设计或需求无法满足**，则回退到 `designed` 或 `proposed`（由 Architect 执行） | PM |
| `build-reviewed-deferred` | PM 对交付段审计线结论的审批完成，结论为延迟处理，仅表示排序或优先级关系 | PM |
| `build-verified-approved` | PM 对交付段测试线结论的审批完成，结论为通过（本行仅适用于 `has_code = true` 的任务；`has_code = false` 不进入 `build-verified*` 状态，见 §7.2） | PM |
| `build-verified-blocked` | PM 对交付段测试线结论的审批完成，结论为缺少某个条件，条件具备后即可继续。转移到阻塞阶段时必须指明缺少的条件（本行仅适用于 `has_code = true` 的任务；`has_code = false` 不进入 `build-verified*` 状态，见 §7.2） | PM |
| `build-verified-rejected` | PM 对交付段测试线结论的审批完成，结论为不通过。返工路径：默认返回 `build`（**由 Coder 执行**），修复缺陷并重新交付；若结论为**设计或需求无法满足**，则回退到 `designed` 或 `proposed`（由 Architect 执行）（本行仅适用于 `has_code = true` 的任务；`has_code = false` 不进入 `build-verified*` 状态，见 §7.2） | PM |
| `build-verified-deferred` | PM 对交付段测试线结论的审批完成，结论为延迟处理，仅表示排序或优先级关系（本行仅适用于 `has_code = true` 的任务；`has_code = false` 不进入 `build-verified*` 状态，见 §7.2） | PM |

> `in_progress` 状态废止：执行属于隐藏状态，不在文本中展现；交付前任务在书面上保持其门禁通过状态。
> 所有 `deferred` 状态仅表示排序或优先级关系，不依赖其他任务完成。


### 2.4 blocked 状态的定义与操作约束

#### 2.4.1 进入 `*-blocked` 的约束条件

任务仅在同时满足以下全部条件时，方可由 PM 判定为 `*-blocked`（`proposed-blocked`、`designed-blocked`、`build-reviewed-blocked`、`build-verified-blocked`）：

1. **阻塞条件是外部依赖**：导致任务无法继续的原因，属于提交者当前无法通过修改本任务文件来消除的条件，包括但不限于：用户对治理文档的审批、用户对提案的明确同意、外部系统就绪、上游任务完成、法规或合同约束等。
2. **无需修改当前文件**：进入 blocked 时，本任务当前 `output_contracts` 指定的所有文件，**不需要任何角色进行修改、新增、删除或回滚**。
3. **不需要提交者动作**：提交者无需、也不能通过修改当前任务的任一文件来解决阻塞。

若存在需要对本任务正在处理的文件进行修改的情况，PM **不得**判定 `*-blocked`，而应判定 `*-rejected`，要求提交者修改后重新提交。

#### 2.4.2 blocked 期间的操作约束

任务进入任意 `*-blocked` 状态后，应遵守以下约束：

1. **文件冻结**：本任务当前 `output_contracts` 指定的所有文件，不得由任何角色进行修改、新增、删除或回滚。该冻结自状态记录行落盘时生效，直至状态转移出 `*-blocked` 为止。
2. **允许的动作**：blocked 期间，仅允许以下与本任务文件无关的动作：审计记录、状态追加记录（由 PM 或相关角色按 §10、§11 执行）、与其他任务无关的文件编辑、治理文档的非本任务相关修订。
3. **状态转移条件**：当阻塞条件被消除时，任务方可转移出 `*-blocked` 并继续执行。状态转移必须附带一条追加记录（见 §10、§11）。

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
            ├── build-verified
            │    └── build-verified-approved          （has_code = true 的终态）
            └── 任务完成（final）                       （has_code = false 的终态：免测试线）
```

### 3.2 主要允许转移

| 当前状态 | 允许后续状态 | 条件 |
|---|---|---|
| `proposed` | `proposed-reviewed` | 提案完成审计 |
| `proposed-reviewed` | `proposed-approved` | 审计结论：通过 |
| `proposed-reviewed` | `proposed-rejected` | 审计结论：提案不被接受（重新提交到 `proposed` 属同段返工；`proposed-rejected → proposed` 由 §13.1 对 §7.3 箭头式条目的纳入规则进入全集 `A`，非 §2.1 表后说明） |
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
| `designed-approved` | `build` | 进入交付；交付物形态由 `has_code` 决定（见 §5.2、§6 表 `build` 行） |
| `build` | `build-reviewed` | 实现结果送交审计 |
| `build-reviewed` | `build-reviewed-approved` | 审计结论：通过 |
| `build-reviewed` | `build-reviewed-rejected` | 审计结论：实现不被接受 |
| `build-reviewed` | `build-reviewed-blocked` | 审计发现阻塞项 |
| `build-reviewed` | `build-reviewed-deferred` | 审计延迟处理 |
| `build-reviewed-rejected` | `build` | 需重新交付实现 |
| `build-reviewed-rejected` | `designed` | 设计方案无法满足，需回退设计段重新审定设计（**由 Architect 执行**） |
| `build-reviewed-rejected` | `proposed` | 需求无法满足，需回退提案段重新审定需求（**由 Architect 执行**） |
| `build-reviewed-approved` | `build-verified` | 审计线通过，进入测试阶段（**仅 `has_code = true`**；`has_code = false` 无此转移，其终态即本状态） |
| `build-verified` | `build-verified-approved` | 测试结论：通过（仅 `has_code = true` 的任务有此转移，见 §7.2） |
| `build-verified` | `build-verified-rejected` | 测试结论：不通过 |
| `build-verified` | `build-verified-blocked` | 测试发现阻塞项 |
| `build-verified` | `build-verified-deferred` | 测试延迟处理 |
| `build-verified-rejected` | `build` | 需重新测试或修复（**由 Coder 执行**） |
| `build-verified-rejected` | `designed` | 设计方案无法满足，需回退设计段重新审定设计（**由 Architect 执行**） |
| `build-verified-rejected` | `proposed` | 需求无法满足，需回退提案段重新审定需求（**由 Architect 执行**） |

> 各转移的执行角色按 §13.2 派生规则读：等于该转移目标状态在 §2.1／§2.2／§2.3「角色」列的取值。

### 3.3 禁止转移

```text
未列入允许转移表的转移一律禁止（§13.1 所定义的允许转移全集 `A` 为本禁令的唯一允许范围）。
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
测试线必须在审计线批准后进入（仅 has_code = true 的任务有测试线，见 §7.2）：
  - build 不能直接进入 build-verified。
  - build-verified 不能直接进入 build-reviewed。
  - 测试线不会反过来回退到审计阶段。（has_code = false 的任务不进入测试线，见 §7.2）
免测试终态分支不得用于规避测试（判定见 §5.2）：
  - has_code 字段缺失的任务不得置位 build-reviewed-approved。
  - has_code = false 且 output_contracts 或实际落地文件命中 §5.2 正面清单任一类的任务，不得置位 build-reviewed-approved：Reviewer 在 build-reviewed 报告中记为 P1，PM 依 §2.3 判 build-reviewed-rejected。
  - 交付段按实际落地文件复核提案段声明（见 12 §3.5），复核结论与声明不一致时以复核结论为准。
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
| `build-verified-blocked` | `build-verified-approved` | 阻塞条件已消除，重新进入批准流程，批准结果是通过（仅 `has_code = true` 的任务有此转移，见 §7.2） |
| `build-verified-blocked` | `build-verified-rejected` | 阻塞条件已消除，重新进入批准流程，批准结果是不接受 |
| `build-verified-deferred` | `build-verified-deferred` | 延迟处理结束，重新进入批准流程，批准结果是延期 |
| `build-verified-deferred` | `build-verified-approved` | 延迟处理结束，重新进入批准流程，批准结果是通过（仅 `has_code = true` 的任务有此转移，见 §7.2） |
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
交付审批（测试线，仅 has_code = true 的任务）：build-verified → build-verified-approved / build-verified-rejected / build-verified-blocked / build-verified-deferred
              （has_code = false 的任务无测试线审批：交付审批（审计线）的 approved 即终态，见 §7.2）
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

每个任务包含以下字段，分级必填：

- 必填：`task_id`／`title`／`status`／`created_at`／`updated_at`／`revision`／`assignees`／`input_contracts`／`output_contracts`／`has_code`
- 选填（缺省视为空）：`description`／`dependencies`／`approval_chain`／`risk`

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
| `has_code` | boolean | 本任务交付物是否含代码；判定规则见 §5.2。由 Architect 在提案段声明并给出依据，交付段由 Reviewer 按 §5.2 复核（见 `12` §3.5） |
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

> `has_code = false` 的任务**可以省略** `verifier` 键；省略不视为字段缺失缺陷，也不表示验证被跳过——该任务的交付验证由交付段审计（Reviewer）与 PM 审批承担（见 §7.2）。含代码的任务仍应写明 `verifier`。

### 5.2 `has_code` 的判定

`has_code` 只由该任务 `output_contracts` 列出的**交付物成员**决定，与任务所属领域、是否顺带修改过既有代码无关。判定按下列两张清单，清单未覆盖的情形按「缺省处理」办。

**正面清单（任一成员命中即 `has_code = true`）**

1. 实现源码：编译器／解释器消费的源文件（本仓库现量：`*.go`、`*.py`；`*.ipynb` 视同源码，因其单元格为可执行代码）；
2. 测试代码：`*_test.go`、`test_*.py` 及 `tests/` 目录下的可执行测试脚本；
3. 可执行脚本与运行入口：`*.sh`、`*.ps1`、`*.bat`、`Makefile` 中被直接调用的目标；
4. 构建与依赖配置（改变构建／安装行为者）：`go.mod`、`go.sum`、`package.json`、`requirements.txt`、`Dockerfile`、`*.ipynb` 的 pipeline 配置；
5. 生成物与迁移：由生成器产出并作为交付物本体的代码、数据库迁移脚本、被跟踪的二进制产物（如 `*.exe`）。

**负面清单（不据以判 `true`）**

1. 文档类：`*.md`、`*.txt`、`*.pdf`——**含 `.md` 内的代码块与示例代码**，文档内嵌代码不构成代码交付物；
2. 任务台账与任务产物目录内的报告（`tasks/**/*.md`）；
3. 纯仓库／编辑器配置（不承载可执行逻辑）：`.gitignore`、`.gitattributes`、`.editorconfig`、`*.ini`、`*.toml`、`*.yaml`；若某份配置承载可执行逻辑（CI 步骤、生成器指令），改按正面清单第 4 类计；
4. 数据与模型产物（作为数据而非实现交付时）：`*.npz`、`*.csv`、`*.parquet`、`*.log`。

**缺省处理（按序适用，三条）**

1. 成员类型未在上列任一清单登记 ⇒ **fail-closed 取 `true`**（进入测试线），并由 Reviewer 在交付审计报告中记「类型未登记」，供后续治理任务补列清单。
2. `has_code` 字段缺失 ⇒ 判为**不可判**：不得置位 `build-reviewed-approved`，不得进入任何终态；缺失**不得**读作 `false`，也不得据缺失走免测试分支。
3. 提案段声明与 `output_contracts`／实际落地文件成员类型冲突 ⇒ **以实际成员类型为准**；提案段声明是义务性自陈，不是最终取值来源，交付段复核可推翻它。

> 规避禁令：若某段代码的用途是进入仓库运行、却只写进 `.md` 代码块，该任务按**正面清单第 1 类**计入 `true`；负面清单第 1 类不保护这种写法。

**追溯**：本字段自本节规则**生效之日**起对新建任务必填。生效日已建台账的任务不溯及补填，其 `has_code` 按缺省处理第 2 则判为「不可判」。

## 6. 任务产物（交付物）

每个状态对应明确的交付物、生产者与载体。载体路径中的 `T-XXXX` 指具体任务 ID。

| 状态 | 交付物 | 生产者 | 载体 |
|---|---|---|---|
| （任务建立） | 任务台账 | Architect | `tasks/T-XXXX.md` |
| `proposed` | 需求说明（提案） | Architect | `tasks/T-XXXX/proposal.md` |
| `proposed-reviewed` | 提案审计报告 | Reviewer | `tasks/T-XXXX/review-proposal-report.md` |
| `proposed-approved` | 审批结论 | PM | 任务台账；`tasks/T-XXXX/proposal-approval-report.md` |
| `designed` | 设计方案（实现方案） | Architect | `tasks/T-XXXX/design.md` |
| `designed-reviewed` | 设计审计报告 | Reviewer | `tasks/T-XXXX/review-design-report.md` |
| `designed-approved` | 审计结论 | PM | 任务台账；`tasks/T-XXXX/design-approval-report.md` |
| `build` | 交付物：`has_code = true` 为代码＋代码相关文档；`has_code = false` 为文档类交付物（见 §5.2） | Coder | 仓库代码文件＋相关 `docs/`，或 `docs/`／治理文档文本 |
| `build-reviewed` | 交付审计报告 | Reviewer | `tasks/T-XXXX/review-build-report.md` |
| `build-reviewed-approved` | 审计结论 | PM | 任务台账；`tasks/T-XXXX/build-reviewed-approval-report.md` |
| `build-verified` | 测试验收报告（仅 `has_code = true` 的任务产出本行交付物） | Tester | `tasks/T-XXXX/test-plan.md`、`tasks/T-XXXX/tests/`、`tasks/T-XXXX/test-report.md` |
| `build-verified-approved` | 审计结论（仅 `has_code = true` 的任务产出本行交付物，见 §7.2） | PM | 任务台账；`tasks/T-XXXX/build-verified-approval-report.md` |
| `build-verified-rejected` | 审计报告 | PM | 任务台账、`tasks/T-XXXX/build-decision.md` |
| `build-verified-blocked` | 审计报告 | PM | `tasks/T-XXXX/build-decision.md` |
| `build-verified-deferred` | 审计报告 | PM | `tasks/T-XXXX/build-decision.md` |

> PM 的四态结论（`approved`／`rejected`／`blocked`／`deferred`）均产出审批报告，统一落盘为 `tasks/T-XXXX/<阶段>-approval-report.md`（命名对照见 `14` §6.2）；本表仅列载体主项。

> `has_code = false` 的任务不产出本表的 `build-verified` 行交付物，并以 `build-reviewed-approved` 结案（§7.2）；该任务的交付验证载体是 `build-reviewed` 审计报告与 `build-reviewed-approval-report.md`，**不是**「缺少一份测试报告」。

> 注：本表描述「状态 → 交付物」的对应关系，**不记录成熟度**；各状态的成熟度见 §6.1，其记录载体为任务台账与 Git 提交。
>
> 任务台账在 `proposed` 置位的同一轮创建，与 `proposal.md` 同轮落盘；建立时即写入首条状态记录行（旧状态取值见 §10）。

### 6.1 产物成熟度（五级）

成熟度**不**由产物文件标注；成熟度由**任务台账**与 **Git 提交**联合保存。各状态的成熟度如下：

| 级 | 成熟度 | 含义 | 达到条件（状态变体） |
|---|---|---|---|
| 1 | 供审计稿 | 已提交、进入审计与审批流程 | `proposed`（提案）/`designed`（设计）/`build`（交付） |
| 2 | 审计稿 | 审计已完成，审计结论已出具 | `proposed-reviewed`／`designed-reviewed`／`build-reviewed` |
| 3 | 审定稿 | 对审计阶段的审批已完成（文档类交付与免测试任务的终态亦在此级） | `proposed-approved`／`designed-approved`／`build-reviewed-approved` |
| 4 | 测试验收稿 | 测试验收已完成 | `build-verified`（仅 `has_code = true`；免测试任务的最终级见第 3 级／§7.2） |
| 5 | 最终稿 | 对测试验收的审批已完成，为最终结论 | `build-verified-approved`（仅 `has_code = true`；免测试任务的最终级见第 3 级／§7.2） |

> 记录说明：任务台账的 `status:` 行与状态记录行记录当前状态；每一步状态转移对应一次 Git 提交；提交信息与 trailer（`Task-Id`／`Actor`／`State-From`／`State-To`）携带状态移行详情。**产物文件本身不得写入与成熟度相关的状态标注。**

### 6.2 版本与返工规则（由任务台账 + Git 承载）

**产物文件**（`proposal.md`、`design.md`、`test-report.md`、源码文件等）**不得在文件头标注成熟度或状态**。版本与返工方式如下：

- **返工版本号`revision`**：由任务台账的 `revision:` 字段记录，返工时递增；提交信息必须说明“第 N 轮返工”。
- **返工采用同文件覆盖**：产物在原载体上就地修订，不新建 `proposal-v2.md` 等文件；版本历史由 Git 保留（`git log` / `git diff` 可追溯每轮返工的差异）。
- **载体路径一经确定不再变更**：草案阶段即写入最终路径，送审后不改路径；状态升级不改路径，只改台账与 Git 记录。

### 6.3 其他说明

- Architect 产出一律**直接落盘到最终载体**；在正式化之前的对话讨论阶段（任务尚未置 `proposed`），讨论不落盘任何文件；置 `proposed` 时，文件落盘到 `tasks/T-XXXX/proposal.md`，不经过“状态标注”环节。
- Reviewer 审计上述全部产物（提案、设计、代码与代码相关文档），产出对应审计报告。
- Tester 测试代码，产出测试方案、测试代码与测试报告；仅 `has_code = true` 的任务进入该线（见 §5.2、§7.2）。
- PM 审批**每一份**审计报告与测试报告（免测试任务无测试报告，其交付段审批对象为审计报告）；审批结论和状态转移记录在任务台账的状态记录行中。
- 载体路径、提交与追溯约定见 `15-version-control-convention.md`。

## 7. 任务生命周期

### 7.1 任务起点

任务的产生有两种场景：

1. 用户与架构师讨论需求，架构师认为该需求有存在的意义、且未被现有其他项目满足；
2. 架构师在进行技术方案 / 实现方案设计时，认为应将现有项目分解为若干子任务。

用户下达创建任务且架构师确认已理解需求时，架构师在同一轮内创建任务台账 `tasks/T-XXXX.md` 与提案 `tasks/T-XXXX/proposal.md`，并将状态置为 `proposed`；两者同轮落盘，不设草稿专用目录或草稿专用态。正式化之前的对话讨论不落盘任何文件。

用户对提案的确认属于 Architect 的内部工作规范，不进入 PM / Reviewer 的审批链路，不在任务台账中设置单独核对项。

> `proposed` 状态的提交人是 **Architect**（用户确认提案后置位）；**审批人**为 **PM**，在 `proposed-reviewed` 之后依据 Reviewer 的审计报告进行四态审批。

### 7.2 任务终点

任务有两个终态，由任务台账的 `has_code` 字段决定唯一分支（判定见 §5.2，二者互斥且穷尽）：

- `has_code = true`：终态为 `build-verified-approved`（即旧词汇 `verified`），须走完测试线；**最终验收等同于任务完成**。
- `has_code = false`：终态为 `build-reviewed-approved`，交付段审计线通过并经 PM 审批后即**任务完成**，不进入 `build-verified`，无测试线产物。
- `has_code` 缺失或不可判：任务**无终态可取**，停在 `build-reviewed`／`build-reviewed-approved` 之前的可判状态并须先补判定（§5.2 缺省处理第 2 则）。
- 终态与中间态共用 `build-reviewed-approved` 这一状态值：判定任务是否结束须并读台账 `has_code`，不得仅凭 `status` 判定。

### 7.3 失败与返工

`blocked` / `rejected` / `deferred` 的含义与处理见 §2 与 §3.4 恢复转移规则。

任务主链如下：

```text
proposed → proposed-reviewed → proposed-approved → designed
        → designed-reviewed → designed-approved → build
        → build-reviewed → build-reviewed-approved
        ├─（has_code = true）→ build-verified → build-verified-approved（测试线终态）
        └─（has_code = false）→ 免测试线，build-reviewed-approved 即终态（见 §7.2）
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
build-reviewed-approved → build-verified                  （仅 has_code = true：审计通过，进入测试阶段；见 §5.2／§7.2）
build-reviewed-approved → 终态                             （has_code = false：免测试线，本状态即任务终态；见 §7.2）

build-verified → build-verified-rejected / build-verified-blocked / build-verified-deferred
build-verified-rejected → build                          （由 Coder 执行：修复缺陷并重新交付）
build-verified-rejected → designed                      （设计无法满足，回退设计段；由 Architect 执行）
build-verified-rejected → proposed                      （需求无法满足，回退提案段；由 Architect 执行）
```

> `build-verified` 的四个结论态（`build-verified-approved`／`build-verified-rejected`／`build-verified-blocked`／`build-verified-deferred`）由 **PM 审批**产出，`build-verified` 进入态本身由 Tester 置位（均见 §2.3 角色列与 §13.2 派生规则），且**仅对 `has_code = true` 的任务存在**；Tester 只置位 `build-reviewed-approved → build-verified`（`has_code = false` 无此转移，见 §5.2／§7.2）。PM 判 `build-verified-rejected` 后的返工**默认由 Coder 执行**（退回 `build`），Tester 不再介入；若结论为设计或需求无法满足，则由 Architect 执行回退（退回 `designed` 或 `proposed`）。

每次状态转移都必须附带一条追加记录。

## 8. 项目治理文档流程

```text
项目治理文档文本由交付段执行者（Coder）依已批准设计落盘
  ↓
PM 审批项目治理文档（生效）
```

说明：

```text
治理文档文本由 Coder 落盘；未经 PM 审批不生效；PM 不编写治理文档（专职审批）。
治理文档类任务在状态机中的位置：其 has_code = false，交付段以 build-reviewed-approved 结案（§7.2），不进入测试线。
本节的「Coder 落盘 → PM 审批（生效）」描述治理文本的**生效环节**，不替代三段审计；生效的用户批准见 14 §9 与 14 §5.1，其与本节的归属差异为既存余量，本变更不重开（见任务设计稿未含项）。
```

## 9. 完整流程示例

以下示例为 `has_code = true` 的任务（走测试线）：

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
Tester 测试实现结果（build-verified）（has_code = true）
  ↓
PM 审批测试线结论（build-verified-approved）（has_code = true）
  ↓
  终态（build-verified-approved）（has_code = true）
```

非代码任务（`has_code = false`）在同一主链上于交付段提前结案，不出现 Tester 环节：

```text
Architect:Qoder-A 提出任务（proposed，声明 has_code = false）
  ↓
Reviewer 提案审计（proposed-reviewed）→ PM 审批（proposed-approved）
  ↓
Architect:Qoder-A 完成设计（designed）
  ↓
Reviewer 设计审计（designed-reviewed）→ PM 审批（designed-approved）
  ↓
Coder:opencode 交付文档（build）
  ↓
Reviewer 审计实现结果（build-reviewed）
  ↓
PM 审批审计线结论（build-reviewed-approved）
  ↓
  终态（build-reviewed-approved）
```

## 10. 状态记录格式

> 状态记录的**载体**是任务台账文件 `tasks/T-XXXX.md`；提交与追溯约定见 `15-version-control-convention.md`。

状态变化记录格式为：

```text
T-YYYYMMDD-NNN <旧状态> -> <新状态> by <角色>:<参与者ID> | <原因/动作>
```

> `<旧状态>` 与 `<新状态>` 的取值域是 §2 三张状态表的全部状态，外加唯一例外：任务台账的首条记录行，其 `<旧状态>` 写作字面量 `(新建)`。除此之外的任何旧状态取值一律非法。

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
T-20261017-001 build-reviewed-approved -> build-verified by Tester:kilo | 测试完成（示例任务 has_code = true）
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
| `completed` | `build-verified-approved` | **旧状态词汇迁移语境**下的映射（本表整体仅用于历史词汇对照，见本节标题）；新规则的任务终态按 §7.2 双分支，`has_code = false` 的任务终态为 `build-reviewed-approved`，**不得据本行推定单一终态** |
| `verified` | `build-verified-approved` | 同上：该映射仅适用 `has_code = true`（测试通过后进入终态）；`has_code = false` 见 §7.2 |

历史记录切换点：自本文件生效之日起，新任务采用新状态词汇；历史任务保留原状态词汇，跨系统迁移时按上表映射。

## 13. 执行角色派生规则、允许转移全集与用户指令的效力

> 本节是 §2 三张状态表「角色」列、§3.2／§3.4 两张转移表与 §7.3 分支陈述三者之间关系的唯一权威读法。本节与 §2／§3.2／§3.4／§7.3 的其他陈述不一致时，以本节为准。

**13.1 符号与全集**

- 状态全集 `S`：§2.1／§2.2／§2.3 三张表「状态」列的全部取值。
- 角色函数 `ρ`：任一状态在所属 §2 表「角色」列的取值。
- 允许转移全集 `A`：§3.2 与 §3.4 两张表的全部行，加上 §7.3「常见分支」及各状态表表后说明中以 `X → Y` 形式列出、且 `X` 与 `Y` 均属 `S` 的转移。`A` 之外的转移一律为表外转移，受 §3.3 首句禁止。
- 上条中「以 `X → Y` 形式列出」只在本节所列为限：除 §3.2／§3.4 表行与 §7.3 常见分支、§2.1／§2.2 表后说明之外，任何其他文本（含各角色运行手册、审批与审计报告、任务台账的历史记录行）中的转移表述不构成允许转移，也不新增 `A` 的元素。

**13.2 执行角色派生规则**

- 对 `A` 中任一转移，其执行角色等于该转移**目标状态**在 §2 表「角色」列的取值 `ρ(目标状态)`；本节是执行角色的唯一权威读法。
- 角色 `r` 的置位权：`P(r) = { e ∈ A : ρ(e 的目标状态) = r }`。
- 其他文本与本节的派生结果不一致时，以派生结果为准；不一致处应作为缺陷登记，不得作为置位依据。

**13.3 用户指令在状态机上的效力（规范性优先级句）**

- 用户指令在任务状态机上只构成**输入**、不构成转移：任何用户指令（含「代为继续」「重新设计」等改令）都不改变 §13.1 的允许转移全集 `A`、不改变角色函数 `ρ`、不扩大本角色的置位权，角色可执行的置位取值恒为 `P(本角色) ∩ { e ∈ A : e 的当前状态 = 任务台账现态 }`，被请求的动作不属于该集合即为越权、其处置唯一为拒绝并报告（见 §13.5），且 §3.3 的表外禁止与本节优先于 `14-responsibility-boundaries.md` §6.5 第 1 项末句「经用户明确改令方可代为继续」。
- 判定顺序（四步，先后固定）：① 读任务台账现态 `X` 与全集 `A`（§13.1）；② 读本角色置位权 `P(本角色)`（§13.2）；③ 取本角色在 `X` 下的动作集合（§13.4）；④ 用户指令只在该动作集合内选择执行哪一项——集合为空时执行 §13.5 的报告义务，不得置位、不得写入载体。
- 用户依治理程序修订 §2／§3.2／§3.4／§7.3 的文本后，`S`、`ρ`、`A` 的取值随修订后的文本改变；在本节之外，指令本身不改变这三个集合。

**13.4 动作集合与作用面**

- 角色 `r` 在状态 `X` 下的动作集合 = `{ e ∈ P(r) : e 的当前状态 = X }` ∪ `{ §6 交付物表中「状态 = X 且生产者 = r」那一行的载体 }`；§6 表无 `X` 行时，写入面按 `14-responsibility-boundaries.md` §6.4 本角色允许落盘的文件集判定，不因用户改令而扩大。
- 各角色只执行任务推进到的当下状态所允许的动作：动作集合非空时在其中选择；为空时不执行任何状态置位或载体写入。

**13.5 越界禁止与报告义务**

- 被请求的动作不属于本角色在现态下的动作集合，即为越权，不得执行；越权不因用户明确改令而变为可执行。
- 执行者须在同轮向用户报告三项：① 被拒动作与所涉条款；② 现态下本角色动作集合的读数；③ 合法入路（存在时逐条给出起始状态、转移与其执行角色；不存在时声明「无合法入路」并停止）。报告不代替执行，也不得因已报告而先行置位。