# 15. 版本控制约定（用 git 管项目）

> 状态：生效
> 适用范围：本项目全部治理与实现资产。
> **重要：本文件约定已生效，当前状态为「生效」。** 实施约定见 §11 过渡路线图。

本文件定义如何用 git 管理本项目，并与 `13-task-model.md`《任务模型》衔接：**任务状态以任务台账为权威，文件改动以 git 为事实来源**。

---

## 1. 定位

git 与 13 号文件是互补关系：

| 关注点 | 权威载体 |
|---|---|
| 任务状态（当前值）与状态历史 | 仓库内**任务台账**（见 §4） |
| “上一步改了哪些文件” | **git** 的提交与 diff（见 §7） |
| 任务状态的语义与转移规则 | `13-task-model.md`《任务模型》 |

二者以 `<task_id>` 与提交的一一对应关系衔接。

---

## 2. 与治理原则的对应

| 治理条款 | 本约定的落点 |
|---|---|
| `01-governance-principles.md` §1 追加原则 | 台账只追加行；git 历史不可改写 |
| `02-document-lifecycle.md` 落盘＝进入指定文件载体 | 一次提交即一次落盘 |
| `05-change-control.md` 变更记录 | 提交信息 + trailer |
| `06-reference-policy.md` §2/§3 | 以 `<task_id>` 与提交锚点引用，不依赖行号/轮次 |
| `09-audit-policy.md` 文件校验 | `git show` / blob hash 可校验 |
| `13-task-model.md` §9/§10 追加记录 | 台账行即记录；每步一提交 |

---

## 3. 纳管范围

### 3.1 纳入版本控制

- 治理与协议：`docs/`（含 `docs/management/`）、`AGENTS.md`、`.clinerules/`、`agents/`、`.opencode/agents/`、`.kilo/agents/`、`.github/agents/`
- 实现与配置：`src/`、`internal/`、`pkg/`、`cmd/`、`connector/`、`bin/`、`configs/`、`tests/`
- 任务台账：`tasks/`

> **纳管范围 ≠ 治理文档范围**：§3.1 规定「哪些文件纳入版本控制」，「什么算项目治理文档」见 `00-governance-index.md` §6。二者不是同一集合——纳管范围还包括实现、配置、测试等全部受管文件。

### 3.2 排除（写入 `.gitignore`）

- 可再生成或体积大者：`data/`、`research/results/`、`research/tfi_flow3/store/`、`node_modules/`、`.pytest_cache/`、`__pycache__/`
- 工具本地状态：`.opencode/index/`、`.opencode/node_modules/`、`.opencode/package*.json`、`.opencode/bun.lock`、`.kilo/node_modules/`、`.kilo/package*.json`、`.kilo/*lock*`、`.kilo/agent-manager.json`
- 二进制产物：`*.exe`、`*.db`、`*.db-shm`、`*.db-wal`
- 临时输出：`_out.txt`、`_tmp_out.txt`、`_check5m.txt`（按需）

> `.opencode/`、`.kilo/` **整目录不再排除**：二者的 `agents/*.md` 是 opencode / kilo 的角色加载入口（治理资产，见 `agents/README.md` §4），须纳入版本控制；仅排除其下可再生成的工具状态。

> 任务产物**一律直接落盘到最终载体**（`tasks/T-YYYYMMDD-NNN/…`），不设草稿专用目录，故 `tasks/` 整体纳入版本控制（见 `13-task-model.md` §6.1）。

### 3.3 二进制存档

- 需要留档且无法文本化的（如 `docs/*.docx`）使用 **git-lfs**；若暂不需要，先排除、后续再纳管。

---

## 4. 状态事实来源：任务台账

### 4.1 位置与粒度

每个任务一个台账文件：

```text
tasks/T-YYYYMMDD-NNN.md
```

任务的**产物**（需求说明、设计、审计报告、测试方案/代码/报告等）存放在同名目录下（见 `13-task-model.md` §6）：

```text
tasks/T-YYYYMMDD-NNN/
```

### 4.2 结构

```markdown
# T-YYYYMMDD-NNN <标题>

- task_id: <任务 ID>
- title: <任务标题>
- status: <当前状态>
- created_at: <创建时间>
- updated_at: <更新时间>
- revision: <修订版本>
- assignees: { "proposer": "...", "reviewer": "...", "executor": "...", "verifier": "..." }
- input_contracts: [...]
- output_contracts: [...]
- description: <可选>
- dependencies: <可选>
- approval_chain: <可选>
- risk: <可选>

## 状态记录（append-only）
T-YYYYMMDD-NNN proposed -> proposed-reviewed by Reviewer:copilot | 提案审计完成
T-YYYYMMDD-NNN proposed-reviewed -> proposed-approved by PM:Cline | decision=提案通过
```

### 4.3 规则

1. `status:` 行是该任务当前状态的**唯一快照**，随转移更新（只改这一行）。
2. “状态记录”区**只追加、不修改、不删除**（符合 `13` §11 追加记录规则）。
3. 记录行格式遵循 `13` §10 状态记录格式：`<task_id> <旧状态> -> <新状态> by <角色>:<参与者ID> | <原因/动作>`。
4. 每追加一条记录 = 完成一次状态转移。
5. 字段区（`## 状态记录` 之前的 `- ` 行）随任务演进更新，不受 append-only 约束；append-only 仅适用于「状态记录」区。

---

## 5. 提交模型

### 5.1 每步一提交

- **一次状态转移 = 一次提交**；台账行的追加与本次改动**同处该提交**。
- 禁止把多步转移压进一次提交。

### 5.2 提交信息

首行：

```text
<task_id> <旧状态> -> <新状态> | <摘要>
```

机器可读 trailer：

```text
Task-Id: T-20261018-001
Actor: Coder:opencode
State-From: build
State-To: build-reviewed
```

`Actor` 取值见 `12-multi-agent-roles.md`《角色标签与参与者映射》。

---

## 6. 分支与标签

### 6.1 选定模型：主干直线

当前多 agent 为**串行**执行，不存在并行冲突，故在 `master` 上逐步提交：

```text
master: … ── 第1步 ── 第2步 ── 第3步 ── …
```

### 6.2 可选（暂不启用）：每任务一分支

若将来出现**并行**任务，可改为每任务一分支 `task/T-YYYYMMDD-NNN`，到达 `build-verified-approved` 时合并回 `master`；此时 `git diff master...task/T-YYYYMMDD-NNN` 即该任务全部改动。

### 6.3 里程碑标签（可选）

可对关键节点打标签，便于稳定引用：

```text
task/T-YYYYMMDD-NNN/proposed-approved
task/T-YYYYMMDD-NNN/build-verified-approved
```

---

## 7. 改动文件的追踪（“上一步改了什么”）

因“每步一提交”且台账受版本控制，**追加某行台账的那次提交，即该步的改动提交**。下游 agent 使用：

```bash
git log --grep="T-20261018-001" --oneline   # 定位该任务各步提交
git show --stat <sha>                        # 该步改动的文件
git diff --name-status <sha>^..<sha>         # 精确清单（新增/修改/删除）
```

如需硬锚定，可在台账记录行尾附加可选字段 `commit=<sha>`。

---

## 8. 多 agent 协作

- 执行模型：**串行**。同一时刻只有一个 agent 处于写入态。
- 每步开始前：同步仓库（拉取最新提交）。
- 每步结束：提交（必要时推送）。
- 交接：下游 agent 通过 `git log --grep=<task_id>` 与 `git show` 获取上一步改动。
- `AGENTS.md` §3 的消息包作为**通知**；**git 与任务台账为事实来源**。

---

## 9. 审计对接

- 审计（`09-audit-policy.md`）可对提交做校验：

```bash
git show --stat <sha>
git diff <sha>^..<sha>
git rev-parse <sha>^{tree}
```

- 台账行与提交一一对应，可核对“状态记录是否完备”。

---

## 10. 权限

遵循 `14` §6.0「落盘即提交」统一原则：凡被授权落盘某文件的角色，即同时被授权对该文件（及对应的任务台账）执行 `git add` / `git commit` / `git push`；各角色 git 写权仅限本角色被允许落盘的那批文件。

- `PM`：原则上仅可执行只读 git 命令（`log` / `diff` / `show` 等）；写入与 `git add` / `git commit` / `git push` 依 §6.0，与其落盘范围一致——任务台账 `tasks/T-YYYYMMDD-NNN.md` 的状态行/记录行，以及本角色审批报告 `tasks/T-YYYYMMDD-NNN/<阶段>-approval-report.md`（见 `agents/pm.md` §5、`14` §6.2）。
- `Architect`：对 `tasks/T-YYYYMMDD-NNN/proposal.md`、`design.md` 及对应任务台账依 §6.0 提交/推送。
- `Coder`：对当前任务 `output_contracts` 指定范围内落盘的交付物（含代码与文档，含项目治理文档）及对应任务台账依 §6.0 提交/推送。
- `Tester`：对 `test-plan.md`、`tests/`、`test-report.md` 及对应任务台账依 §6.0 提交/推送。
- `Reviewer`：对审计报告（`review-proposal-report.md` / `review-design-report.md` / `review-build-report.md`）及对应任务台账依 §6.0 提交/推送。
- 各角色不得对范围外文件执行提交/推送；提交遵循 §5「每步一提交」、§8「每步结束提交/推送」。

---

## 11. 过渡路线图

| 阶段 | 动作 | 前置条件 |
|---|---|---|
| Phase 0 | 只定文档（本文件） | — |
| Phase 1 | 纳管 + 基线提交 | 全部文档完工 + 用户授权 |
| Phase 2 | 固化本约定（本文件转“候选/生效”） | 用户审批 |
| Phase 3 | 启用“每步一提交 + 台账记状态” | Phase 1–2 完成 |
| Phase 4 | 视需要启用每任务分支 / 里程碑标签 / LFS | 出现并行任务等 |

---

## 12. 最小变更约束

1. 本文件只定义约定，不替代 `13-task-model.md`《任务模型》。
2. 实施 git 需用户另行授权；未授权前仓库保持现状。
3. 历史记录只追加，不覆盖。

---

## 附录 A 术语对照

| 术语 | 含义 |
|---|---|
| 主干 / trunk / `master` | 默认主线 |
| 提交（commit） | 一次改动快照，含唯一 SHA |
| 分支（branch） | 平行时间线 |
| 合并（merge） | 把分支并入主线 |
| 标签（tag） | 给某次提交起的稳定名字 |
| SHA | 提交的内容寻址标识 |
| trailer | 提交信息末尾的机器可读键值行 |
| `.gitignore` | 声明哪些文件不纳入版本控制的清单 |

---

## 附录 B 变更记录

依《变更控制》（`05-change-control.md`）每次变更须记时间／修改对象／修改原因／修改内容／生效时间。

| 时间 | 修改对象 | 修改原因 | 修改内容 | 生效时间 |
|-|-|-|-|-|
| 2026-11-01 | 本文件的载体范围（载体变化）：`docs/management/01`–`11`、`.clinerules/pm-role.md`、`.opencode/agents/coder.md`、`.kilo/agents/tester.md` | 修复 §3.1 纳管范围与仓库现状的缺口（上述治理资产此前未被 git 跟踪） | 将 14 个未跟踪治理文件纳入版本控制（提交 `18f4382`） | 2026-11-01（经用户批准后生效） |
| 2026-11-01 | 本文件（`15-version-control-convention.md`） | GOI-coder-govdoc-20261101：治理文档类任务在交付段无执行者（R-1）；PM 专职审批 | §10 权限：Coder 落盘范围扩至交付物（含治理文档）；PM 落盘范围缩为仅任务台账 | 2026-11-01（经用户批准后生效） |
| 2026-10-31 | 本文件（`15-version-control-convention.md`） | 与 `14` §6.0「落盘即提交」对齐：把 git 提交/推送权限从 PM 例外一/例外二式专项授权改为「落盘即提交」统一原则，一次性对齐所有角色 | §10 权限：以 §6.0 统一原则替换 PM 例外一/例外二与「其余……由被授权的执行角色完成」封闭句，并按角色列明各自的 git 落盘范围（Architect / Coder / Tester / Reviewer / PM） | 经用户批准落地 |
| 2026-10-20 | 本文件（`15-version-control-convention.md`） | 补齐 PM 对被点名治理文档的提交权，与 `14-responsibility-boundaries.md` §6.2、`agents/pm.md` §5 例外二对齐 | §10 权限：将 PM 的 git 写入权限拆为「例外一」（任务台账）与「例外二」（用户点名的那一个项目治理文档），后者明确包含写入与 `git add` / `git commit` | 未定（待用户审批） |
| 2026-10-20 | 本文件（`15-version-control-convention.md`） | Reviewer 角色分配给 VS Code Copilot，其加载入口须纳入版本控制 | §3.1 纳管范围增 `.github/agents/`（VS Code Copilot 的 agent 定义）；§4 状态记录示例的 `Reviewer:xxx` 改为 `Reviewer:copilot` | 未定（待用户审批） |
| 2026-11-03 | 本文件 §10 PM 行 | T-20261102-001：解除 PM 落盘审批报告的禁令与要求之矛盾 | §10 PM 行落盘范围增列本角色审批报告 `tasks/T-YYYYMMDD-NNN/<阶段>-approval-report.md`；命名对照见 `14` §6.2 | 经用户批准后生效 |

