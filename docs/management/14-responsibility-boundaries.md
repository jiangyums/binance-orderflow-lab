# 14. 责任边界

> 状态：生效

## 1. 责任边界原则

为了避免多 agent 协作中的责任不清，项目责任必须明确到具体角色。

基本原则：

```text
1. 谁负责设计，谁负责确认设计；
2. 谁负责实现，谁负责验证实现；
3. 谁负责审查，谁负责承担审查风险；
4. 谁负责审批，谁承担审批责任；
5. 谁负责记录，谁承担记录责任。
```

---

## 2. 角色边界

### 2.1 PM（项目经理 / 审批人）

- 职责：
  1. 根据 Reviewer、Tester 的输出结果进行审批。
  2. 编写项目治理文档（其**生效须用户审批**，见 §5.1）。
  3. 审批项目治理文档之外的文档和代码（范围见 §5.1）。
  4. 对审计意见逐条核对，明确标注“修复”“无视”“延后”。
  5. 补充未被审计的领域，指出“应当被审计”的对象。
  6. 审批结论必须使用四态：`approved / rejected / blocked / deferred`；不得使用“有条件通过”“部分通过”“通过但需补充”等非四态结论。
- 写权限：见 §6.2（只读审批）。
- 输出：
  - 审批结论：四态之一；
  - 审批报告：落盘到 `tasks/T-YYYYMMDD-NNN/approval-report.md`；
  - 项目治理文档：范围见 `00-governance-index.md` §6。

---

### 2.2 Architect（架构师）

- 职责：整理需求、提出任务、设计方案、明确输入/输出契约。
- 写权限：见 §6.4（通用写权限）。
- 说明：获得 `designed-approved` 后，任务进入交付段（`build`）；该转移由 **Coder** 执行（见 `13-task-model.md` §2.3）。

---

### 2.3 Coder（代码编写者）

- 职责：落地已批准任务的实现。
- 写权限：见 §6.4（通用写权限）。

---

### 2.4 Tester（测试者）

- 职责：依据已生效的设计文档对代码进行测试，交付测试结果（对应测试线 `build-reviewed-approved` → `build-verified`）。
- 写权限：见 §6.3（只读验证）。

---

### 2.5 Reviewer（审查员）

- 职责：依据已生效的文档对代码和文档进行审查，在代码测试以外的领域找到问题（对应三段审计线：`proposed-reviewed` 提案审计、`designed-reviewed` 设计审计、`build-reviewed` 交付审计）。
- 写权限：见 §6.1（只读审查）。

---

## 3. 通用约束

以下约束对全部角色一律适用，优先于各角色的具体描述：

```text
1. 不越权：只执行本角色职责范围内的动作，不代替他人产出产物或结论。
2. 不代替他人结论：approved 系列状态由 PM 依审批结论触发，任何角色不得自行置位。
3. 只在本角色范围动作：改动文件不得超出本角色允许的路径与载体范围。
4. 边界有疑义时保守：拿不准是否越界时，视为越界，停下并请求 PM 裁定。
5. 阻塞即指因：置位任何 `*-blocked` 状态时，必须写明缺少的条件（条件须可验证），并记入任务台账的状态记录行（见 `13-task-model.md` §2）。
6. 延迟仅表序：`*-deferred` 仅表示排序或优先级关系，不依赖其他任务完成，也不得当作实质暂停（见 `13-task-model.md` §2、§2.3）。
```

> 本节只规定通用底线，各角色的**写权限**清单见 §6；§2 只述职责与产物，不含写权限。

---

## 4. 责任分离

为避免责任不清，应遵守以下原则：

```text
1. 谁提出任务，谁负责任务提出。
2. 谁设计方案，谁负责确认设计。
3. 谁审查，谁负责提出问题。
4. 谁测试，谁负责验证结果。
5. 谁审批，谁承担审批责任。
6. 谁记录，谁承担记录责任。
```

---

## 5. 审批边界

### 5.1 PM 的审批范围

PM 可以审批：由任务参与者产生的、用于落地实现、验证和决策的成果（业务/实现/代码/文档相关成果），但不得审批项目治理文档本身。

PM 可以审批：包括但不限于：

```text
1. Reviewer 的输出结果。
2. Tester 的输出结果。
3. 其余的文档和代码。
```

项目治理文档本身 指：`00-governance-index.md` §6 规定的范围。

这些文件必须由 PM 编写，交由用户审批。PM 不得自行审批项目治理文档本身。

PM 的审批结论必须使用四态：`approved / rejected / blocked / deferred`。  
“有条件通过”、“部分通过”、“通过但需补充”等表达不得作为审批结论；  
如存在条件、缺陷或未满足要求，应按场景转为 `rejected` 或 `blocked`，不得另创审批态。

审批报告中必须包含“审计意见核对表”与“审计覆盖缺口”：
- 审计意见核对表：逐条标注“修复”“无视”“延后”；
- 审计覆盖缺口：指出尚未被审计的领域、建议的审计对象与完成时间。

> **任务台账不属于「项目治理文档」**（见 `00-governance-index.md` §6）：`tasks/T-YYYYMMDD-NNN.md` 是任务状态的**事实来源**（见 `15-version-control-convention.md` §4），由触发状态转移的角色追加记录、PM 追加审批结论（见 `agents/pm.md` §5 例外一），不适用「PM 编写、用户审批」的治理文件流程。

---

## 6. 权限边界

> 本节是全部角色**写权限**的唯一规范出处；§2 的角色边界只述职责与产物，涉及写权限一律以本节为准。
> 本节与 `agents/pm.md` §5、`15-version-control-convention.md` §10 表述不一致时，以本节为准。

### 6.1 只读审查

- `Reviewer` 只能读文件，不能修改工作区文件。
- `Reviewer` 不能提出解决方案。
- `Reviewer` 不能直接落地实现。
- **例外**：`Reviewer` 在提交审查报告时置位审计状态、写入审计报告与台账记录行（见 §6.4）。

---

### 6.2 只读审批

- `PM` 可以在**审计结论已出具**的前提下执行审批：依审计/测试结论置位任务台账中对应的 `*-approved` 状态，
  且**不得改动产物文件内的任何状态标注**（产物文件本就不标注状态；成熟度由任务台账与 Git 提交承载，见 `13` §6.1）。
- `PM` **仅在用户明确要求时**，可修改被点名的那一个项目治理文档本身（范围见 `00-governance-index.md` §6），
  并可对该文件执行 `git add` / `git commit`；治理文档的生效仍须用户审批。
- `PM` 可以写入任务台账 `tasks/T-YYYYMMDD-NNN.md` 的 `status` 行与状态记录行，
  并**仅对该文件**执行 `git add` / `git commit`；除台账文件与本节第 2 条所述文件外，不得写入或提交任何文件。
- 审批结论必须是四态：`approved / rejected / blocked / deferred`。  
  不得使用“有条件通过”“部分通过”“通过但需补充”等非四态结论；  
  如存在条件或未满足项，按 `rejected` 或 `blocked` 处理，不得另创审批态。
- 审批时必须逐条覆核审计意见，并在审批报告中标注“修复”“无视”“延后”；  
  同时补充“审计覆盖缺口”，指明未被审计、应当被审计的领域与建议完成时间。
- 审批报告必须落盘为 `tasks/T-YYYYMMDD-NNN/approval-report.md`，与对应状态记录行同步提交。
- 除上述各项外，`PM` 不得修改任何文档与代码。

---

### 6.3 只读验证

- `Tester` 可以读取已生效设计文档、实现代码和测试产物。
- `Tester` 可以编写测试用例、运行测试、生成测试报告。
- `Tester` 不能提供解决方案。
- `Tester` 不能修改未批准的实现/生产代码。

---

### 6.4 通用写权限

- `Architect` 可以提交项目提案或需求说明（置 `proposed`）与设计文档（置 `designed`），产物直接落盘到 `tasks/T-YYYYMMDD-NNN/`（见 `13-task-model.md` §6.1）。
- `Coder` 可以落地已批准任务的实现代码，且改动不得超出当前任务 `output_contracts` 指定的文件范围。
- `Coder` 与 `Architect` 均不得将任何文档或任务状态标记为 `approved` 系列（该系列由 PM 依审批结论触发，见 §3 第 2 条）。
- `Reviewer` 可以在提交审查报告时置位对应审计状态（`proposed-reviewed` / `designed-reviewed` / `build-reviewed`），并追加台账状态记录行。
- `Tester` 可以置位 `build-reviewed-approved → build-verified`，并追加台账状态记录行；不得置位任何 `*-approved` 结论态（见 `13-task-model.md` §2.3）。
- 任何角色均不得修改未经审批的实现 / 生产代码，不得修改任务台账中非本角色应写的行（台账写入规则见 `15-version-control-convention.md` §4.3）。

---

## 7. 责任传递

### 7.1 责任传递图

```text
Architect:Qoder-A 提出任务（proposed）
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

返工分支（状态语义见 `13-task-model.md` §2、§7.3；`*-blocked` / `*-deferred` 的处理见 §3 第 5、6 条）：

```text
proposed-reviewed  → proposed-rejected  → proposed     （Architect 返工重提提案）
designed-reviewed  → designed-rejected  → designed     （Architect 返工重做设计）
build-reviewed     → build-reviewed-rejected → build    （Coder 返工重交付）
build-verified     → build-verified-rejected → build    （Coder 返工修复缺陷；Tester 不再介入）
```

跨段回退（PM 判「设计 / 需求无法满足」时，由 Architect 执行，见 `13-task-model.md` §3.2）：

```text
designed-rejected     → proposed     （Architect 回退提案段重提需求）
build-reviewed-rejected → designed    （Architect 回退设计段重做设计）
build-reviewed-rejected → proposed    （Architect 回退提案段重提需求）
build-verified-rejected → designed    （Architect 回退设计段重做设计）
build-verified-rejected → proposed    （Architect 回退提案段重提需求）
```

> 返工归属判定由 **PM** 在审批时做出并记入台账状态记录行（见 `agents/pm.md` §4）：同段返工回原产出角色，跨段回退交 Architect。

---

## 8. 责任归属索引

本节**不重复**角色职责的表述，仅给出查阅入口。

| 关心的问题 | 唯一出处 |
|---|---|
| 某角色的职责、产出、禁止事项 | `12-multi-agent-roles.md` §3.1–§3.5；各角色手册 `agents/*.md` |
| 某责任由谁承担（角色 × 阶段） | `12-multi-agent-roles.md` §3、`13-task-model.md` §2.3（状态表含承担角色） |
| 责任在流程中如何传递、失败时回流给谁 | 本文件 §7（责任传递） |
| 任务状态语义与允许／禁止的转移 | `13-task-model.md` §2、§3 |
| 谁负最终责任 | 本文件 §9 |
| 任务台账的写入责任 | `15-version-control-convention.md` §4.3 |

> 本文件 §2 只述各角色的职责与产物摘要，**不构成独立的职责来源**；与 `12` §3 冲突时以 `12` §3 为准。

---

## 9. 最终责任

最终责任由：

```text
PM
```

承担。具体包括：

```text
- 审批
- 治理文档的编写（其**生效须用户审批**，见 §5.1）
- 审批结论
- 审批结论记录在台账中的最终把关（各角色记录各自触发的状态转移，见 `13-task-model.md` §11 追加记录规则）
```

---

## 10. 最小变更约束

1. 只新增责任边界和任务状态模型相关文件。
2. 不删除或重写已有管理文档。
3. 历史记录只追加，不覆盖。
4. 不引入外部任务系统。
5. 新任务必须有明确的 `input_contracts`、`output_contracts` 和 `assignees`。

---

## 11. 变更记录

依《变更控制》（`05-change-control.md`）每次变更须记时间／修改对象／修改原因／修改内容／生效时间。

| 时间 | 修改对象 | 修改原因 | 修改内容 | 生效时间 |
|-|-|-|-|-|
| 2026-10-20 | 本批治理修订：`14-responsibility-boundaries.md`、`13-task-model.md`、`12-multi-agent-roles.md`、`15-version-control-convention.md`、`agents/pm.md`、`agents/architect.md`、`agents/coder.md`、`agents/tester.md`、`agents/reviewer.md` | 统一写权限口径、状态转移口径与 PM 职责边界，消除文档间的职责与转移冲突 | `14` §2 写权限改为引用 §6、§2.1 措辞改为「生效须用户审批」、§3 增补 `blocked`/`deferred` 语义、§6 新增「权限边界」整节（§6.1 补 Reviewer 例外、§6.2 改写为四条、§6.4 补台账记录行）、§7.1 增补返工分支与跨段回退、§8 原职责表改为「责任归属索引」、§9 与 §8 对齐、§11 增本节；`13` 增 5 条 `*-rejected → designed/proposed` 跨段回退并删除直接跨段转移；`12` 修正 Tester 测试线起点为 `build-reviewed-approved → build-verified`、补 PM 治理文档提交权与 Architect 跨段回退、订正指向 `14` §2.1 的失效引用；`15` 与 `agents/pm.md` 补齐 PM 对被点名治理文档的提交权；`agents/architect.md` §4 补 5 条跨段回退；`agents/coder.md`、`agents/tester.md` 明确跨段回退由 Architect 执行、Coder/Tester 不介入；`agents/reviewer.md` 删除直接跨段回退 | `14` / `15` / `agents/*`：未定（待用户审批）；`12` / `13`：经用户授权修订，生效时间待确认 |
| 2026-10-20 | Reviewer 角色分配：`agents/reviewer.md`、`agents/README.md`、`AGENTS.md`、`.github/agents/reviewer.agent.md`（新增）、`12-multi-agent-roles.md`、`13-task-model.md`、`00-governance-index.md`、`15-version-control-convention.md` | Reviewer 角色此前无工具加载入口（人工指定），无法实际执行审计线；按用户要求将 Reviewer 角色分配给 VS Code Copilot | 新增 VS Code Copilot 的 Reviewer 加载入口 `.github/agents/reviewer.agent.md`（agent 定义，提示词正文指向 `agents/reviewer.md`）；参与者由「未指定」改为 VS Code Copilot（`Reviewer:copilot`）；`00` §6 载体表增 `.github/agents/`；`15` §3.1 纳管范围增 `.github/agents/`；`12` §2 角色表与 §4 映射表、`13` §10/§11 示例中的 `Reviewer:xxx` 统一改为 `Reviewer:copilot` | `agents/*` / `12` / `13` / `00` / `15`：经用户授权修订，生效时间待确认 |

> 本批修订涉及的治理文件此前**未纳入版本控制**（`docs/management/`、`agents/`、`AGENTS.md` 尚无基线提交），首次纳管后其差异可由 git 追溯；为不依赖 git diff 作为唯一差异依据，逐文件改动见下方「修订明细」。

### 11.1 修订明细

| 文件 | 状态 | 修订内容 |
|---|---|---|
| `14-responsibility-boundaries.md` | 草案 | §2.1 措辞改为「生效须用户审批」；§2.1–§2.5 写权限改为引用 §6；§3 增第 5、6 条（`blocked` 指因、`deferred` 仅表序）；§6 新增「权限边界」整节（§6.1 补 Reviewer 例外、§6.2 改写为四条、§6.4 补台账记录行）；§7.1 增返工分支与跨段回退；§8 原职责表删除、改为「责任归属索引」；§9 与 §8 对齐；新增 §11 |
| `13-task-model.md` | 生效 | §2.2/§2.3 返工路径改为「默认」并增补跨段回退分支；§3.2 增 5 条 `*-rejected → designed/proposed`（由 Architect 执行）；§4 审批状态转移增补 5 条；§7.3 常见分支增补 5 条；§3.3 禁止转移表删除 `designed-reviewed → proposed`、`build-reviewed → designed` 两条直接跨段转移 |
| `12-multi-agent-roles.md` | 生效 | §3.1 删除「用户审批项目治理文档」伪职责，补 PM 治理文档提交权；§3.2 补 Architect 跨段回退；§3.4 Tester 测试线起点修正为 `build-reviewed-approved → build-verified`；§2 角色表与 §3.1 中指向 `14` §2.1 的引用改指 §6.2 |
| `15-version-control-convention.md` | 草案 | §10 权限拆为「例外一／例外二」，补 PM 对被点名治理文档的写入与 `git add`/`git commit`；§4.3 修正指向 `13` §9／§10 的失效引用（应为 §10 状态记录格式、§11 追加记录规则）；新增附录 B 变更记录 |
| `agents/pm.md` | 草案 | §4 增返工归属判定规则；§5:44 提交权默认禁止改为「仅例外一、例外二」；§5:45 补限定语；§5:48 例外二补提交权并明确「被点名的那一个」 |
| `agents/architect.md` | 草案 | §4 允许的状态转移删 2 条直接跨段转移、增 5 条 `*-rejected → designed/proposed`；§6 步骤 5 补跨段回退路径 |
| `agents/coder.md` | 草案 | §4 增「跨段回退由 Architect 执行，Coder 不介入」；§6 步骤 5 补跨段回退分支 |
| `agents/tester.md` | 草案 | §4 增跨段回退由 Architect 执行的说明；§7 交接增「交 Architect（跨段回退时）」 |
| `agents/reviewer.md` | 草案 | §4 允许的状态转移删 2 条直接跨段回退 |
| `AGENTS.md` | 生效 | §1 角色分工表中指向 `14` §2.1 的失效引用改指 §6.2 |
| `.github/agents/reviewer.agent.md` | 生效（新增） | 新建 VS Code Copilot 的 Reviewer agent 定义：frontmatter `name: Reviewer` / `description` / `tools: ['read','search','edit']` / `agents: []`；正文为加载令（强制读 `AGENTS.md` 与 `agents/reviewer.md`）、只读审查权限、允许写入的两处载体、三段审计线状态转移与考核维度 |
| `agents/reviewer.md` | 草案 | 头部参与者由「未指定（可选）」改为「VS Code Copilot（`Reviewer:copilot`）」，并标注工具加载入口 `.github/agents/reviewer.agent.md` |
| `agents/README.md` | 草案 | §1 层次图补 `.github/agents/reviewer.agent.md`；§2 手册索引表 Reviewer 行补参与者与加载入口；§4 加载机制表 Reviewer 行由「人工指定」改为 VS Code Copilot |
| `00-governance-index.md` | 生效 | §6 载体表增 `.github/agents/`（VS Code Copilot 的 agent 定义） |
| `12-multi-agent-roles.md` | 生效 | §2 角色表 Reviewer 默认参与者由「可选」改为「VS Code Copilot」；§4 映射表 `Reviewer:未指定` → `Reviewer:copilot` |
| `13-task-model.md` | 生效 | §10 状态记录示例、§11 追加记录示例中的 `Reviewer:xxx` 统一为 `Reviewer:copilot` |
| `15-version-control-convention.md` | 草案 | §3.1 纳管范围增 `.github/agents/`；§4 状态记录示例的 `Reviewer:xxx` 改为 `Reviewer:copilot`；附录 B 增本批变更记录 |

