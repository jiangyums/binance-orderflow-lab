# T-20261103-001 设计 — 任务模型 `has_code` 必填字段与非代码任务的终态分支

> 设计人：Architect:Qoder-A（依 `tasks/T-20261103-001/proposal.md` 与提案段审批报告 §4）
> 审批输入：`tasks/T-20261103-001/review-proposal-report.md`（P1／P2）、`tasks/T-20261103-001/proposal-approval-report.md`（结论 `approved`，§3 设计段必办 J-9）

## 0. 基线与取证口径

- 行号口径：Python `splitlines()` 文本态。实测基线行数：`13`＝556、`14`＝347、`15`＝266、`12`＝103、`AGENTS.md`＝189、`agents/tester.md`＝56、`agents/pm.md`＝40+、`agents/coder.md`＝60+、`.kilo/agents/tester.md`＝35、`.opencode/agents/coder.md`＝33。
- 文本基线提交：`13`／`14` 取 `ee4f2d5` 之后，`15`／`12`／`AGENTS.md`／`agents/` 取 `1ddeb4e` 之后；`3ce2a35`（提案审批）只动任务目录，未触治理文档（实测 `git show --stat` 文件集为 `tasks/T-20261103-001*`）。
- 每个变更项同时给出**行号**与**该行起首字面片段**（内容锚）。行号会随他人提交漂移，内容锚不会；交付前依 `14` §6.5 重取基线并逐行比对（proposal.md §4 壬 甲）。
- 本仓库文件构成实测（`git ls-files`，200 个跟踪文件）：`.py` 97／`.md` 56／`.go` 38／`.exe` 2／`.gitignore` 1／`.yaml` 1／`.toml` 1／`.txt` 1／`.mod` 1／`.sum` 1／`.ini` 1。§5.2 的清单以该构成为对账对象（J-9）。

## 1. 对提案审计意见与审批意见的响应

| 来源 | 意见 | 处置 |
|---|---|---|
| 审计 P1／审批 §1 第 1 项（转设计段 J-9） | `has_code = true` 的成员类型判定边界未界定，免测试分支与防绕过控制不可一致复核 | **闭合于 M-3b**（新增 `13` §5.2「`has_code` 的判定」）：正面清单 5 类＋负面清单 4 类＋缺省三则（未登记类型 fail-closed 取 `true`／字段缺失判「不可判」／声明与实际冲突以实际为准），配 §7 判据 J-9 的 11 类扩展名逐一归类对账 |
| 审计 P2／审批 §1 第 2 项（延后） | 未量化工期；与在治任务时序未确认 | 时序：M-27＋§6 交付顺序写明与 T-20261102-001 的先后关系（该任务现处 `build-reviewed-approved`，其测试线即本规则的首个实例，见 §3 庚）。工期：§6 给出按变更项的**顺序与依赖**，但**不给出量化人日**——本仓库无历史工时登记可依据，给数即编数（`15` 无工时条款）；改为交付段以「单次提交＋实际文件集对账（J-11）」控制规模 |
| 审批 §3 结论 | `approved`，无返工要求 | 本设计不改动提案文本；提案 §0.2 的载体枚举在实测中被证实**非穷尽**，设计阶段补入 **6 个新载体文件＋5 处既存载体的未列小节（共 11 处）**（见 §4 表内「新增？」列与 §9 未含项首条披露） |

## 2. 本任务自身的 `has_code` 预判值（声明，非字段写入）

依 M-3 的判定规则对**本任务自身**作预判：`output_contracts` 成员为 `tasks/T-20261103-001/proposal.md`、`design.md`、任务台账及若干治理 `.md`／手册文本，全部落入 §5.2 负面清单第 1、2 类，正面清单零命中 ⇒ **预判 `has_code = false`**。

- 该值本轮**不写入台账字段**：M-3 的文本随本任务 build 才落盘，生效更在用户批准之后；在字段生效前写入等于用未生效文本为当前登记作证（提案 §8 同句）。
- 由此产生一个必须如实呈报的时序事实：**本任务自身不受它自己提议的分支管辖**。在规则生效前，本任务仍按现行 `13:173` 走测试线，而它的交付物全是文档——Tester 将面对一个没有代码的测试对象。这正是提案 §2 证据 7／10 描述缺口的再次发生，也是 §3 庚 需要用户裁定的直接原因。

## 3. 须裁项采纳结论登记（proposal.md §4）

| 项 | 议题 | 采纳 | 落实位置 | 效力 |
|---|---|---|---|---|
| 甲-1 | 提案段声明义务与 `13:45` 的相容性 | **甲** | M-1、M-4、M-5、M-6 | Architect 建议；PM 审批报告 §4 第 1 项要求设计段给出建议采纳结论，终裁在 PM／用户 |
| 甲-2 | 复用 `build-reviewed-approved` 还是新建终态 | **甲**（复用） | M-8～M-24 全部按复用形态书写 | 同上。`13:54-59`「不得另创新的审批态」只辖审批结论四态，本项不触碰该禁令，不作扩大解释 |
| 丙 | 成熟度映射 | **乙**（改第 3 级含义，级数与「五级」标题不变） | M-13 | 同上 |
| 丁 | 既存任务追溯 | **甲**（不溯及）＋「缺失不得推定」句 | M-3 缺省第 2 则、M-26 | 同上 |
| 戊 | `assignees.verifier` 取值 | **丙**（允许省略该键） | M-7 | 同上 |
| 己 | 防以 `has_code = false` 规避测试 | **甲**（交付段程序性复核＋禁止转移句） | M-11、M-17 | 同上 |
| 庚 | T-20261020-001／T-20261102-001 的结案 | **交用户裁定，Architect 不代判**（裁定材料见下） | 未落实 | 待裁 |
| 辛 | 范围扩围 | **甲**（治理载体全纳入） | M-27（台账 `output_contracts` 字段订正，本轮执行） | 依审批报告 §4 第 3 项指令执行 |
| 壬 | 与 T-20261102-001 同载体的复发通道 | **甲**（build 前重取基线逐行比对） | §0 末条＋J-12 | Architect 建议 |

**庚 的裁定材料（只呈「是否写入／实质结论」，不代判）**

1. `T-20261020-001`：实测 `tasks/T-20261020-001.md:6` ＝ `build-reviewed`，`:13` 的 `output_contracts` 全为 `.md`，目录内**无** `test-plan.md`／`tests/`／`test-report.md`。若新规则生效且**不溯及**（丁 甲），它仍须按现行 `13:173` 进测试线。
2. `T-20261102-001`：实测 `tasks/T-20261102-001.md:6` ＝ `build-reviewed-approved`（PM 记录行写「下一步 Tester 测试线（`build-verified`）」），`:13` 全为 `.md`，目录内同样无 `test-*` 产物。它已经站在测试线入口上。
3. 三个可选处置（互斥，且各自需要一条独立裁定记录）：
   - (a) 生效后由 PM 对这两个任务出具「`has_code = false`」的裁定性记录行，使其以 `build-reviewed-approved` 结案；
   - (b) 不溯及，两任务按现行测试线走完，Tester 就「无测试对象」出具报告（该报告本身会成为规则缺口的新证据）；
   - (c) 只裁 `T-20261102-001`（已在测试线入口），`T-20261020-001` 单独处置。
4. 依赖关系：本设计**任何一条变更项都不以庚 的结论为前提**，庚 只影响这两个既存任务的结案，不影响新规则文本。故庚 未裁不阻塞本任务 `build`；但若采 (a)，需要一条对既存台账的追加记录（字段区订正依 `15` §4.3 第 5 条，记录行仍只追加）。

## 4. 变更矩阵（载体 × 变更项）

「新增」＝提案 §0.2 未列、设计阶段实测补入的载体。

| 载体 | 变更项 | 新增？ |
|---|---|---|
| `docs/management/13-task-model.md` | M-1、M-2、M-3、M-4、M-8、M-9、M-10、M-11、M-12、M-13、M-14、M-15、M-16、M-17、M-18、M-19、M-20、M-21 | 部分（M-12 `13:553-554` 附录 A、M-10 的 `13:164`、M-14 的 `13:351`） |
| `docs/management/12-multi-agent-roles.md` | M-5、M-18、M-19 | 否 |
| `docs/management/14-responsibility-boundaries.md` | M-20、M-21、M-22、M-25、M-26（变更记录行） | 否 |
| `docs/management/15-version-control-convention.md` | M-7、M-23、M-26（附录 B 行） | 部分（M-23 `15:155` 分支合并点） |
| `AGENTS.md` | M-6、M-22、M-24 | 部分（M-24 的 `AGENTS.md:178`「8. …（终态）」） |
| `agents/architect.md` | M-5 | **是** |
| `agents/tester.md` | M-19 | **是** |
| `agents/pm.md` | M-20 | **是** |
| `agents/coder.md` | M-21 | **是** |
| `.kilo/agents/tester.md` | M-19 | **是** |
| `.opencode/agents/coder.md` | M-21 | **是** |
| `tasks/T-20261103-001.md`（本台账） | M-27 | 否（提案已含台账） |

## 5. 变更项全文

以下每条给出：载体｜锚点（行号＋内容锚）｜操作｜待写入文本。表格单元内的 `｜` 均为全角分隔符，不代表单元格换行；待写入文本按原样照登，`{}` 内为待 Coder 照抄的花括号内容。

### 组 A — 字段与判定（J-9）

**M-1**｜`docs/management/13-task-model.md:276`｜内容锚：行首 `- 必填：\`task_id\``｜整行替换：

```markdown
- 必填：`task_id`／`title`／`status`／`created_at`／`updated_at`／`revision`／`assignees`／`input_contracts`／`output_contracts`／`has_code`
```

**M-2**｜`docs/management/13-task-model.md:290`｜内容锚：`\`output_contracts\` | array | 任务产出`｜在该行之后插入一行：

```markdown
| `has_code` | boolean | 本任务交付物是否含代码；判定规则见 §5.2。由 Architect 在提案段声明并给出依据，交付段由 Reviewer 按 §5.2 复核（见 `12` §3.5） |
```

**M-3**｜`docs/management/13-task-model.md`｜内容锚：§5.1 说明表末行 `| \`verifier\` | 负责验证产物的人 |`（现 `:315`）与 `## 6. 任务产物（交付物）`（现 `:317`）之间的空行（`:316`）｜在两者之间插入 M-3a 与 M-3b（顺序：先 M-3a 再 M-3b，均带前置空行）：

**M-3a**（戊 丙）：

```markdown
> `has_code = false` 的任务**可以省略** `verifier` 键；省略不视为字段缺失缺陷，也不表示验证被跳过——该任务的交付验证由交付段审计（Reviewer）与 PM 审批承担（见 §7.2）。含代码的任务仍应写明 `verifier`。
```

**M-3b**（J-9 主体）：

````markdown
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
````

**M-4**｜`docs/management/13-task-model.md:45`｜内容锚：行含 `提案只回答"是否值得做"，不包含`｜在该表格单元内、该行原句之后追加一句（甲-1 甲）：

```markdown
| `proposed` | 项目提案（需求说明）已提出。提案只回答"是否值得做"，不包含设计/实现方案。`has_code` 的声明属**交付范围自陈**，不属本句所排除的设计／实现方案（判定规则见 §5.2） | Architect |
```

（整行替换，其余单元文本原样保留。）

**M-5**｜`docs/management/12-multi-agent-roles.md:50` 与 `agents/architect.md:10`｜内容锚分别为 `- 职责：整理需求、提出任务、设计方案、明确输入/输出契约。` 与 `整理需求、提出任务、设计方案、明确输入 / 输出契约。`｜两处各追加同一义务句（甲-1）：

```markdown
- 职责：整理需求、提出任务、设计方案、明确输入/输出契约，并在提案段声明 `has_code` 及可核对的依据（依据须指向 `output_contracts` 的成员类型，见 `13` §5.2）。
```

`agents/architect.md:10` 采同型措辞，句末引用指向 `13` §5.2。

**M-6**｜`AGENTS.md:45`｜内容锚：`| \`output_contracts\` | 任务产出 |`｜在其后插入一行（与 M-2 同语义，措辞按根协议表列数收窄）：

```markdown
| `has_code` | 本任务交付物是否含代码（判定见 `13` §5.2），由 Architect 在提案段声明 |
```

**M-7**｜`docs/management/15-version-control-convention.md:94`｜内容锚：`- output_contracts: [...]`｜在其后插入一行：

```markdown
- has_code: <true|false>（必填；判定与缺失处理见 `13` §5.2）
```

### 组 B — 终态分支

**M-8**｜`docs/management/13-task-model.md:81`、`:82`｜内容锚：`:81` 含 `实现结果完成测试（测试线，审计批准后进入）`，`:82` 含 `PM 对交付段审计线结论的审批完成`｜两行整行替换（甲-2 甲）：

```markdown
| `build-verified` | 实现结果完成测试（测试线，审计批准后进入；**仅 `has_code = true` 的任务进入**） | Tester |
| `build-reviewed-approved` | PM 对交付段审计线结论的审批完成，结论为通过；`has_code = false` 的任务到此即为终态（见 §7.2） | PM |
```

**M-9**｜`docs/management/13-task-model.md:173`｜内容锚：`| \`build-reviewed-approved\` | \`build-verified\` | 审计线通过，进入测试阶段 |`｜整行替换：

```markdown
| `build-reviewed-approved` | `build-verified` | 审计线通过，进入测试阶段（**仅 `has_code = true`**；`has_code = false` 无此转移，其终态即本状态） |
```

**M-10**｜`docs/management/13-task-model.md:164`｜内容锚：`| \`designed-approved\` | \`build\` | 进入交付，代码交付 |`｜整行替换：

```markdown
| `designed-approved` | `build` | 进入交付；交付物形态由 `has_code` 决定（见 §5.2、§6 表 `build` 行） |
```

**M-11**｜`docs/management/13-task-model.md`｜内容锚：§3.3 围栏内末行 `  - 测试线不会反过来回退到审计阶段。`（现 `:202`）之后、围栏闭合行 `` ``` ``（现 `:203`）之前｜插入（己 甲；围栏内为纯文本，不加行内代码标记）：

```text
免测试终态分支不得用于规避测试（判定见 §5.2）：
  - has_code 字段缺失的任务不得置位 build-reviewed-approved。
  - has_code = false 且 output_contracts 或实际落地文件命中 §5.2 正面清单任一类的任务，不得置位 build-reviewed-approved：Reviewer 在 build-reviewed 报告中记为 P1，PM 依 §2.3 判 build-reviewed-rejected。
  - 交付段按实际落地文件复核提案段声明（见 12 §3.5），复核结论与声明不一致时以复核结论为准。
```

**M-12**｜`docs/management/13-task-model.md:142-144`（§3.1 图）｜内容锚：`:142` ＝ `       └── build-reviewed-approved`、`:144` ＝ `                 └── build-verified-approved`｜以 `:142`–`:144` 三行替换为五行（原缩进风格保持）：

```text
       └── build-reviewed-approved
            ├── build-verified
            │    └── build-verified-approved          （has_code = true 的终态）
            └── 任务完成（final）                       （has_code = false 的终态：免测试线）
```

**M-13**｜`docs/management/13-task-model.md:351`、`:353`（§6.1 成熟度表）｜内容锚：`:351` 含 `` `build`（代码交付） ``、`:353` 含 `对审计阶段的审批已完成（文档类）`｜两行整行替换（丙 乙；标题「五级」与级数不变）：

```markdown
| 1 | 供审计稿 | 已提交、进入审计与审批流程 | `proposed`（提案）/`designed`（设计）/`build`（交付） |
| 3 | 审定稿 | 对审计阶段的审批已完成（文档类交付与免测试任务的终态亦在此级） | `proposed-approved`／`designed-approved`／`build-reviewed-approved` |
```

**M-14**｜`docs/management/13-task-model.md:330`、`:333`（§6 交付物表）＋表下注｜内容锚：`:330` 含 `| \`build\` | 代码 + 代码相关文档 |`、`:333` 含 `| \`build-verified\` | 测试验收报告 |`｜两行整行替换，并在 `:339` 的四态注之后追加一条注：

```markdown
| `build` | 交付物：`has_code = true` 为代码＋代码相关文档；`has_code = false` 为文档类交付物（见 §5.2） | Coder | 仓库代码文件＋相关 `docs/`，或 `docs/`／治理文档文本 |
| `build-verified` | 测试验收报告（仅 `has_code = true` 的任务产出本行交付物） | Tester | `tasks/T-XXXX/test-plan.md`、`tasks/T-XXXX/tests/`、`tasks/T-XXXX/test-report.md` |
```

```markdown
> `has_code = false` 的任务不产出本表的 `build-verified` 行交付物，并以 `build-reviewed-approved` 结案（§7.2）；该任务的交付验证载体是 `build-reviewed` 审计报告与 `build-reviewed-approval-report.md`，**不是**「缺少一份测试报告」。
```

**M-15**｜`docs/management/13-task-model.md:371`、`:372`（§6.3）｜内容锚：`:371` ＝ `- Tester 测试代码，产出测试方案、测试代码与测试报告。`｜两行整行替换：

```markdown
- Tester 测试代码，产出测试方案、测试代码与测试报告；仅 `has_code = true` 的任务进入该线（见 §5.2、§7.2）。
- PM 审批**每一份**审计报告与测试报告（免测试任务无测试报告，其交付段审批对象为审计报告）；审批结论和状态转移记录在任务台账的状态记录行中。
```

**M-16**｜`docs/management/13-task-model.md:435-445`（§8 围栏）｜内容锚：围栏内末行 `治理文档文本由 Coder 落盘；未经 PM 审批不生效；PM 不编写治理文档（专职审批）。`（现 `:444`）之后、围栏闭合（现 `:445`）之前｜插入（目标三「旁路归位」）：

```text
治理文档类任务在状态机中的位置：其 has_code = false，交付段以 build-reviewed-approved 结案（§7.2），不进入测试线。
本节的「Coder 落盘 → PM 审批（生效）」描述治理文本的**生效环节**，不替代三段审计；生效的用户批准见 14 §9 与 14 §5.1，其与本节的归属差异为既存余量，本变更不重开（见任务设计稿未含项）。
```

**M-17**｜`docs/management/13-task-model.md:449-473`（§9 完整流程示例）｜内容锚：围栏起始 `` ```text ``（现 `:449`）前、`## 9. 完整流程示例`（现 `:447`）后｜两处插入：

（a）在 `:448` 空行之后、`:449` 围栏之前加一句限定：

```markdown
以下示例为 `has_code = true` 的任务（走测试线）：
```

（b）在围栏闭合（现 `:473`）之后新增一段第二例：

````markdown
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
````

**M-18**｜`docs/management/13-task-model.md:199-202`／`12:76-83`｜Reviewer 复核项（己 甲，与 M-11 配对）｜在 `12-multi-agent-roles.md:81`（内容锚：`交付审计时（\`build → build-reviewed\`），审查实现是否能够达到技术方案目标`）之后插入一行：

```markdown
- 允许：交付审计时按 `13` §5.2 复核 `has_code` 声明与 `output_contracts`／实际落地文件的成员类型是否一致，并在审计报告中单列该复核结论（含代码却声明 `false` 者按 P1 呈报）。
```

**M-19**｜Tester 侧三处（`12:69`、`13:371` 已由 M-15 覆盖、`agents/tester.md`、`.kilo/agents/tester.md`）：

- `docs/management/12-multi-agent-roles.md:69`｜内容锚：`- 职责：依据已生效的设计文档对代码进行测试，交付测试结果（对应测试线`｜整行替换：

```markdown
- 职责：依据已生效的设计文档对代码进行测试，交付测试结果（对应测试线 `build-reviewed-approved` → `build-verified`；**仅 `has_code = true` 的任务**，判定见 `13` §5.2）。
```

- `agents/tester.md:8`（内容锚：`依据**已生效的设计文档**对代码进行测试`）之后新增一段；`agents/tester.md:31`（内容锚：`审计线通过后进入测试（Tester 唯一置位的状态）`）整行替换：

```markdown
> Tester 只参与 `has_code = true` 的任务（判定见 `13` §5.2）。`has_code = false` 的任务在 `build-reviewed-approved` 结案，不进入测试线，Tester 不介入、也不因其缺席而被记为缺项。
```

```markdown
| `build-reviewed-approved → build-verified` | 审计线通过后进入测试（Tester 唯一置位的状态；仅 `has_code = true` 的任务） |
```

- `.kilo/agents/tester.md:2`、`:25`｜内容锚：`:2` 含 `依据已生效设计文档测试代码`、`:25` 含 `只在任务处于 \`build-reviewed-approved\` 时介入测试`｜两行整行替换：

```markdown
description: Tester（测试者）— 依据已生效设计文档测试代码（仅 has_code = true 的任务），交付测试方案/代码/报告
```

```markdown
- 只在任务处于 `build-reviewed-approved` **且该任务 `has_code = true`** 时介入测试；`has_code = false` 的任务在该状态结案，不进入测试线（判定见 `13` §5.2）。
```

**M-20**｜PM 侧两处（`14:57`、`agents/pm.md:33`）：

- `docs/management/14-responsibility-boundaries.md:57`｜内容锚：`- 职责：依据已生效的设计文档对代码进行测试，交付测试结果（对应测试线`｜整行替换（与 M-19 首条同型，出处改为 `13` §5.2）：

```markdown
- 职责：依据已生效的设计文档对代码进行测试，交付测试结果（对应测试线 `build-reviewed-approved` → `build-verified`；仅 `has_code = true` 的任务，判定见 `13` §5.2）。
```

- `agents/pm.md:33`｜内容锚：`审批交付**测试线**结论`｜整行替换：

```markdown
| `build-verified → build-verified-approved / -rejected / -blocked / -deferred` | 审批交付**测试线**结论（仅 `has_code = true` 的任务；`has_code = false` 时交付段止于上一行审计线结论，PM 依 `13` §7.2 认其结案） |
```

**M-21**｜Coder 侧三处（`agents/coder.md:58`、`.opencode/agents/coder.md:2`／`:33`）：

```markdown
- 交 Tester：审计通过后的实现代码（`has_code = true` 时）；`has_code = false` 的任务无此交接，交付审计后由 PM 结案。
```

```markdown
description: Coder（代码编写者）— 落地已批准任务的实现，产出交付物（代码或文档，按任务 has_code 判定，见 13 §5.2）
```

```markdown
- 交 Tester：审计通过后的实现代码（`has_code = true` 的任务）。
```

**M-22**｜状态图与置位权两处（`14:199`、`14:237` 注、`AGENTS.md:86`）：

- `docs/management/14-responsibility-boundaries.md:199`｜内容锚：`- \`Tester\` 可以置位 \`build-reviewed-approved → build-verified\``｜整行替换：

```markdown
- `Tester` 可以置位 `build-reviewed-approved → build-verified`（仅 `has_code = true` 的任务，判定见 `13` §5.2），并追加台账状态记录行；不得置位任何 `*-approved` 结论态（见 `13-task-model.md` §2.3）。
```

- `docs/management/14-responsibility-boundaries.md:237`（§7.1 传递图围栏闭合行，内容锚：该行上一行 `:236` ＝ `终态（build-verified-approved）`）之后插入一段注：

```markdown
> `has_code = false` 的任务在上图「PM 审批审计线结论（`build-reviewed-approved`）」处即为终态，Tester 与测试线环节不出现（`13` §5.2／§7.2）。
```

- `AGENTS.md:85-86`｜内容锚：`:85` ＝ `build-verified-approved`、`:86` ＝ `  └── 任务完成（final）`｜两行替换为五行：

```text
build-verified-approved
  └── 任务完成（final｜has_code = true）

build-reviewed-approved
  └── 任务完成（final｜has_code = false：免测试线）
```

**M-23**｜`docs/management/15-version-control-convention.md:155`｜内容锚：`到达 \`build-verified-approved\` 时合并回 \`master\``｜该句整句替换（保留同段其余文字）：

```markdown
若将来出现**并行**任务，可改为每任务一分支 `task/T-YYYYMMDD-NNN`，到达**任务终态**（`13` §7.2：`has_code = true` 为 `build-verified-approved`，`has_code = false` 为 `build-reviewed-approved`）时合并回 `master`；此时 `git diff master...task/T-YYYYMMDD-NNN` 即该任务全部改动。
```

**M-24**｜`AGENTS.md` 流程步骤与示例四处（`:106-107` 后、`:173`、`:174`、`:178`）：

- 在 `:107`（内容锚：`T-20261017-001 build-verified -> build-verified-approved | verdict=通过`）之后插入一行示例：

```text
T-20261017-002 build-reviewed -> build-reviewed-approved by PM:Cline | decision=通过；本任务 has_code=false，据此结案（13 §7.2）
```

- `:173`｜内容锚：`3. Tester 依据已生效的设计文档测试代码，交付测试结果。`｜替换：

```markdown
3. Tester 依据已生效的设计文档测试代码，交付测试结果（仅 `has_code = true` 的任务；`has_code = false` 的任务不经测试线）。
```

- `:174`｜内容锚：`4. PM 审批 Reviewer、Tester 的输出结果。`｜替换：

```markdown
4. PM 审批 Reviewer 的输出结果；任务走测试线时一并审批 Tester 的输出结果。
```

- `:178`｜内容锚：`8. 任务状态更新为 \`build-verified-approved\`（终态）。`｜替换：

```markdown
8. 任务状态更新为终态：`has_code = true` 为 `build-verified-approved`；`has_code = false` 为 `build-reviewed-approved`（免测试线，`13` §7.2）。
```

**M-25**｜`docs/management/13-task-model.md:390-392`（§7.2 任务终点）｜内容锚：`:392` ＝ `任务的终态为 \`verified\`（即 \`build-verified-approved\`），到达即表示**任务完成**；**最终验收等同于任务完成**。`｜该行整行替换（本变更的收口句）：

```markdown
任务有两个终态，由任务台账的 `has_code` 字段决定唯一分支（判定见 §5.2，二者互斥且穷尽）：

- `has_code = true`：终态为 `build-verified-approved`（即旧词汇 `verified`），须走完测试线；**最终验收等同于任务完成**。
- `has_code = false`：终态为 `build-reviewed-approved`，交付段审计线通过并经 PM 审批后即**任务完成**，不进入 `build-verified`，无测试线产物。
- `has_code` 缺失或不可判：任务**无终态可取**，停在 `build-reviewed`／`build-reviewed-approved` 之前的可判状态并须先补判定（§5.2 缺省处理第 2 则）。
```

**M-26**｜变更记录两行（依「各文档自有变更表只记本文件改动」的既存裁定）：

- `docs/management/14-responsibility-boundaries.md` §11 变更表末行之后（内容锚：现 `:322` 行首 `| 2026-11-03 | \`13\` §6 交付物表、\`14\` §6.2 |`）追加一行：

```markdown
| 2026-11-04 | `13-task-model.md` §2.1／§2.3／§3.1／§3.2／§3.3／§4／§5／§5.2（新增）／§6／§6.1／§6.3／§7.2／§8／§9／附录 A、`12-multi-agent-roles.md` §3.2／§3.4／§3.5、`14-responsibility-boundaries.md` §2.4／§6.4／§7.1、`15-version-control-convention.md` §4.2／§6.2、`AGENTS.md` §2／§2 示例／§4、`agents/architect.md`／`agents/tester.md`／`agents/pm.md`／`agents/coder.md`、`.kilo/agents/tester.md`、`.opencode/agents/coder.md` | T-20261103-001：纯文档类任务在现行状态机下没有合法终态（`13:173` 测试线无条件、`13:392` 单终态），与 `13` §8 治理文档流程相抵 | 新增必填字段 `has_code`（§5 字段表与 §5.2 判定：正面 5 类／负面 4 类／缺省三则，含缺失「不可判」与未登记类型 fail-closed）；确立双终态（§7.2），`has_code = false` 免测试线以 `build-reviewed-approved` 结案；§3.2 进测试线条件化、§3.3 增防绕过禁止句、§6.1 成熟度第 3 级纳入该终态、§5.1 允许 `verifier` 省略；角色手册与加载入口同步条件化 | 经用户批准后生效 |
```

- `docs/management/15-version-control-convention.md` 附录 B 表末（内容锚：现 `:265` 行首 `| 2026-11-03 | 本文件 §10 PM 行 |`）追加一行，修改对象写「本文件 §4.2 结构模板／§6.2」：

```markdown
| 2026-11-04 | 本文件（`15-version-control-convention.md`）§4.2 台账结构模板、§6.2 分支合并点 | T-20261103-001：新增必填字段 `has_code` 须进台账模板；并行分支的合并触发点原写作单一终态，与双终态分支不符 | §4.2 模板增 `- has_code: <true|false>` 行；§6.2 合并触发点改为「到达任务终态（`13` §7.2 双分支）」 | 经用户批准后生效 |
```

**M-27**｜本任务台账 `tasks/T-20261103-001.md` 的 `output_contracts` 字段扩围（依 `15` §4.3 第 5 条，字段区非 append-only；辛 甲／审批报告 §4 第 3 项）｜**由本设计轮执行**，不等 build。扩围后须与 §4 变更矩阵的载体列**逐一对应**（J-11）。

### 不改清单（登记理由，供审计判定是否成立）

| 载体 | 不改的理由 |
|---|---|
| `13:447` 之后的 §10／§11 记录格式与 `:499` 示例 | 示例只演示记录行语法，不声明终态唯一性；`:499` 的 `build-reviewed-approved -> build-verified` 仍是 `has_code = true` 的合法转移 |
| `13` §12.5／`14` §10.5／`15` §12.3「新任务必须有明确的 `input_contracts`、`output_contracts` 和 `assignees`」 | 该句是最低要件列举、不声称穷尽必填集；必填集的唯一出处是 `13` §5（M-1／M-2） |
| `15:163` 里程碑标签示例 `task/.../build-verified-approved` | 命名示例，M-23 已在合并触发点处写明双终态；该处若穷举两种标签会使示例臃肿 |
| `AGENTS.md:30` 角色表 Tester 行「仅验证已获批任务」 | 未含代码前提，与新分支不冲突 |
| `14:185-188`（Tester 读写权限条目） | 权限本身不因分支改变；条件化只落在置位权（M-22）与职责句（M-20） |
| `agents/architect.md:32-39` 状态转移表 | 未列 `build-reviewed-approved → build-verified`，与本变更无冲突 |
| `.clinerules/pm-role.md` | 实测无终态／测试线表述（9 行，仅加载令与首屏硬约束） |
| `docs/management/11-governance-open-items.md` 的「终态」3 处 | 属既存开放项登记文脉，非状态机规则表述 |

## 6. 交付顺序与角色边界

1. **本轮（设计段，Architect）**：M-27（台账 `output_contracts` 扩围）＋台账 `status: proposed-approved → designed` 追加记录；不触碰任何治理文档本体。
2. **build（Coder，依 `13` §8 由 Coder 落盘治理文本）**：按 **组 A → 组 B → M-26** 的顺序单次提交完成全部落地，理由：`13` §5.2 的判定句是被引用项，先落字段与判定再落引用处，避免中途出现指向不存在小节的引用；变更表（M-26）最后落，使其「修改内容」列能如实描述已完成的全部改动。**不做多点切分**（避免 `T-20261102-001` 交付审计中 J8 型「提交切分偏差」复发）。
3. **交付前**：依 `14` §6.5 重取 `13`／`14`／`15`／`12`／`AGENTS.md` 基线并逐行比对本设计锚点（壬 甲）；锚点内容有变即停止并回到设计段。
4. **build-reviewed（Reviewer）**：交付审计，含 M-18 的 `has_code` 复核结论单列项与 J-9 对账。
5. **测试线**：本任务自身按 §2 的说明仍受现行规则管辖——若庚 未裁，则 `has_code = false` 的本任务在现行 `13:173` 下仍须 Tester 置位 `build-verified`。**这一处矛盾须在交付段呈报，不得由 Architect 单方推定。**
6. **生效**：全部文本为治理文档，生效时间统一写「经用户批准后生效」（沿用 `14:322`／`15:265` 的既存措辞形制）；`14`／`15` 本身仍属草案，其新增文本不改变草案／生效的既有分层。

## 7. 验收判据（设计稿定稿，替换提案 §7 草案）

| 判据 | 可机械核对的形式 |
|---|---|
| J-1 | `13` §5 必填清单含 `` `has_code` ``（该行命中 1 次）；字段表新增行存在，类型列为 `boolean` |
| J-2 | `13` §5.2 存在，正面清单恰 5 类、负面清单恰 4 类、缺省处理恰 3 则（按小节内编号行计数，取自脚本） |
| J-3 | `13:392` 原句「任务的终态为 \`verified\`」在 `13` 命中 0；§7.2 改写后含两个终态条目与「缺失／不可判无终态」条 |
| J-4 | `13` §3.2 的 `build-reviewed-approved → build-verified` 条件句含 `has_code = true`；§3.3 出现 M-11 三条禁止句 |
| J-5 | 成熟度表（`13` §6.1）第 3 级含 `` `build-reviewed-approved` ``，标题仍为「（五级）」，级数仍 5 |
| J-6 | **（v2，返工轮按审批报告 §5 第 3 项整体重写；取代前轮「文件级矩阵归属」表述）** 行级判据：以 §10.2 的检索式 R1–R9 在扫描域（`docs/management/`＋`agents/`＋`.clinerules/`＋`.kilo/agents/`＋`.opencode/agents/` 全部 `.md`＋`AGENTS.md`）逐行重跑；谓词 P＝该行含 `has_code`、或引 `§5.2`／`§7.2`、或该行位于 `13` §5.2 小节内。**每一命中行**要么满足 P，要么逐行登记在 §10.4「行级豁免登记表」并附成立理由；二者必居其一，出现任何未登记的命中行即判 FAIL 并回设计段。计数（命中行数与行-串对数）取自脚本并并列报告。**禁止以「命中文件在矩阵内」代替行级核对**——前轮正是以此漏掉 §7.3（根因见 §10.1） |
| J-7 | `12` §3.5 出现 M-18 复核条目；`AGENTS.md` §2 状态图出现两个 `任务完成（final｜…）` 行 |
| J-8 | 两个既存任务台账 `tasks/T-20261020-001.md`、`tasks/T-20261102-001.md` 对本任务交付提交 `git diff` 为空（丁 甲；除非庚 采 (a) 并另给裁定记录） |
| **J-9** | **（审批报告 §3 指定的硬判据）**`13` §5.2 两张清单与本仓库 `git ls-files` 实测扩展名全集对账：11 类扩展名／无扩展名条目（`.py` `.md` `.go` `.exe` `.gitignore` `.yaml` `.toml` `.txt` `.mod` `.sum` `.ini`）逐一可归类；未登记类型由缺省第 1 则显式接住（fail-closed `true`），且缺省第 2 则写明「缺失＝不可判、不得读作 `false`」、缺省第 3 则写明冲突时以实际成员为准。三则缺一即判未闭合 |
| J-10 | `14` §11 与 `15` 附录 B 各新增一行且五字段（时间／修改对象／修改原因／修改内容／生效时间）齐；`15` 行的修改对象为「本文件…」 |
| J-11 | 集合对账，两个差集均须为空：记 A＝交付提交的实际改动文件集（`git diff --name-status <base>..<head>`）、B＝本台账 `output_contracts`、C＝本任务 build 之前的轮次已提交的前序产物（`tasks/T-20261103-001/proposal.md`、`tasks/T-20261103-001/design.md`）。① `A \ B = ∅`（无越范围改动）；② `B \ (A ∪ C) = ∅`（除前序产物外无未落地成员）。**采「两个差集」而非「互为等集」**：build 提交不改动 `proposal.md`／`design.md`，若要求 `A ≡ B` 则该判据首运必 FAIL；若返工轮改动了 C 中任一文件，须在设计段返工记录里点名后由 ① 继续辖制 |
| J-12 | 治理文档基线未被他任务覆盖：交付提交的父提交上，M-1～M-26 未涉及的行与 `ee4f2d5`／`1ddeb4e` 之后版本逐行相等（壬 甲） |

## 8. 风险与回滚

- R-1 绕过测试 → M-11 三条禁止句＋M-18 复核单列＋J-4／J-6 对账；残余：判定依赖 `output_contracts` 的诚实列举，已由缺省第 3 则（以实际成员为准）封住「少列文件」这条通道。
- R-2 取值二义（`false` 与缺失混读）→ M-3 缺省第 2 则＋M-25 第三条「无终态可取」；J-9 明确该则为闭合要件。
- R-3 同载体覆盖（与 T-20261102-001 争 `13` §6）→ 该任务 M-12 已落地，本设计以落地后文本为基线（§0）；其后续返工复发通道由 M-27 扩围＋J-12 控制。
- R-4 一致性面遗漏 → 提案 §0.2 实测被证非穷尽（设计阶段补入 **6 个新载体文件＋5 处既存载体的未列小节，共 11 处**，见 §9 首条与 §4「新增？」列），故本设计的收口手段不是「列全」而是 **J-6 的七串全量重跑对账**（含本轮预跑基线）：任何未登记的命中行要么进矩阵，要么进不改清单，否则判未闭合。
- R-5 本任务自我指涉（提议免测试线却自身要走测试线）→ §2、§6 第 5 步如实呈报，交庚 裁定；Architect 不推定。
- R-6 公开仓库披露 → 本设计与后续报告只含规则文本、行号与实测计数；依 `14:178` 内容边界句自查；提交前对**本角色落地文件集**跑凭据扫描并报告命中数（扫描式随提交披露，声明非穷尽）。
- 回滚：本变更全为治理文本与台账字段。回滚依既存形制两处留痕——变更表**追加**一行回滚记录（不删既存历史行）＋下一次合法状态转移记录行的原因字段注明；文本回滚用 `git revert`，不用改写历史提交。

## 9. 未含项与余量（不作推定）

- **提案 §0.2 的枚举被实测证伪为「非穷尽」**（提案当时已声明非穷尽）：设计阶段新发现 **6 个新载体文件**（`agents/architect.md`、`agents/tester.md`、`agents/pm.md`、`agents/coder.md`、`.kilo/agents/tester.md`、`.opencode/agents/coder.md`）＋ **5 处既存载体的未列小节**（`13:164`、`13:351`、`13:553-554` 附录 A、`AGENTS.md:178`、`15:155`），合计 11 处，已并入矩阵。逐条属「新增」还是「提案 §0.2 已含载体的未列小节」以 §4 表「新增？」列为准。
- `13` 附录 A（`:553-554`）「`completed`／`verified` → 全局终态」只在 §7.2 改写后靠**读推**保持一致，本轮未加脚注：M-19 未覆盖附录 A。若审计认为该附录须显式加注，属设计段返工项，不在本轮自行扩项。
- 未量化工时（审批 P2 延后项，本设计给顺序与依赖，不给日数）。
- 未重开「治理文档编写责任归属」的既存冲突（`13` §8 vs `14` §9），M-16 只写明状态机归位并显式指向该余量。
- 未写入本任务的 `has_code` 字段行（§2）。
- 未裁庚，未代用户裁 §3 任何一项；甲-1／甲-2／丙／丁／戊／己／壬 的「采纳」为 Architect 建议，终裁在 PM／用户。
- 台账 `status:` 快照存在既存滞后：PM 审批提交 `3ce2a35` 追加了 `proposed-reviewed -> proposed-approved` 记录行但未更新 `status:` 行（依 `15` §4.3 第 1 条应随转移更新）。本轮置 `designed` 时该滞后被一并闭合，**未修改任何历史记录行**。
- **本轮首次提交前的自我更正（四处，均在 design.md 自身，逐条登记）**：
  1. §7 J-11 原写作「`output_contracts` 与交付提交的实际改动文件集**互为等集**」——按本任务的实际提交切分（`proposal.md`／`design.md` 在 build 之前的轮次已各自提交，不再出现在交付提交的文件集里），该表述**首次运行即 FAIL**，属会造出假 FAIL 的判据；已改为「两个差集均为空」并显式定义 A／B／C。
  2. 「新发现 7 处载体」的计数与该条自身枚举的 11 项不符（亦与 §4「新增？」列不符）——已按「6 个新载体文件＋5 处既存载体的未列小节」订正，同步改到 §1 响应表、§8 R-4 与本节首条。
  3. §7 J-6 的扫描范围原写作「§4 矩阵全部载体」——用矩阵自身作扫描域去证明矩阵无漏项是**自证循环**，漏项永远命不中；已改为比矩阵更宽的目录全集，并规定「命中文件不在矩阵内即判矩阵有漏项」。
  4. §1 响应表的「闭合于 M-3」指得不准：J-9 的主体是 **M-3b**（`13` §5.2），M-3a 只是 `verifier` 省略句；已改为「闭合于 M-3b」。
  5. §7 J-6 的检索串由 5 串扩为 **7 串**（加 `测试代码`／`测试方案`——`.kilo/agents/tester.md:2`、`13:371` 一类表述用的是「测试代码」，原五串命不中它们），并按「写前取基线」纪律补入本轮预跑读数（26 个 `.md`／49 命中行／62 行-串对／分布逐文件列出）。预跑结果同时是本设计的**前提核验**：七串无任何命中文件落在 §4 矩阵之外，故矩阵在本轮未出现新增漏项；该读数只说明「七串口径下无漏项」，不声明七串穷尽语义。
  上述五处均为对本轮**尚未提交**产物的修订，没有第三方读过旧表述；修订后的文本即本轮提交版本。

---

## 10. 返工轮 1（`build-reviewed-rejected → designed`）

> 本节由 PM:Cline 的交付审计段审批报告（`tasks/T-20261103-001/build-reviewed-approval-report.md`，提交 `e769ba9`）§5 返工规格第 1／2／3 项触发。规格第 4 项（交 Coder 重落盘、交 Reviewer 复审计）不属本节。
> **前轮文本保留为历史记录**：§4 矩阵、§5 变更项 M-1～M-27、§7 判据的前轮表述除下文明示的一处替换（§7 J-6）外**一律不回改**；与本节冲突处以本节为准。
> **行号口径**：本节行号为返工取证时点（HEAD `e769ba9`，2026-11-04）的 Python `splitlines()` 文本态读数——`13` 624 行／`14` 350 行／`15` 268 行／`12` 104 行／`AGENTS.md` 194 行／`agents/tester.md` 67 行。**M-1～M-26 落地后行号已整体后移**（`13` 由 556 → 624），故前轮矩阵与「不改清单」中的行号现已失效；本节每项变更一律给出**内容锚**，行号只作定位起点。

### 10.1 驳回要点与根因（设计侧，认账）

| # | PM／Reviewer 认定 | 根因（在我这一侧） |
|---|---|---|
| 1 | P0：`13` §7.3 主链（`:445-448`）与常见分支（`:465`）仍无条件导向测试线，与已落地的 §2.3／§3.2／§7.2 冲突 | §4 变更矩阵**结构性遗漏** §7.3——提案 §0.2 列了 §7.3 载体，我在设计阶段把它判给「M-12 附录 A／M-9 §3.2」一类，未把主链图与分支表单列为变更项 |
| 2 | P0：J-6 未通过，台账所记「矩阵外未覆盖命中 0」与实测不符 | 我把 J-6 的核对单位定在**文件级**（「命中文件不在矩阵内即判漏项」）。文件在矩阵内 ⇒ 该行级缺口永远命不中。我的预跑读数「无任何命中文件落在 §4 矩阵之外」当时**为真**，但它是文件级真命题，被当作行级保证使用——这是判据缺陷，不是取数错误 |
| 3 | P1：附录 A（`:621-622`）单终态未衔接 §7.2；`14:325` 变更记录列附录 A 为已修改而实际未改 | 我在 §9 把附录 A 登记为「靠读推保持一致，不加脚注，若审计要求则属返工项」——审计确实要求了，代价由交付段承担；且 M-26 只规定「追加变更行」的形制，未规定「变更行的修改对象枚举 ⊆ 实际改动文件集」，使记录与实际可以背离 |
| 4 | （本轮我自查新增，非 PM 提出）检索串口径含子串噪声与结构性漏检 | 「任务完成」命中「不依赖其他**任务完成**」「上游**任务完成**」（`13:92`／`:101`／`14:79`），属假命中；反之 §7.3 注句 `:473` 与 `agents/tester.md:50` 的操作步骤行**不含任一检索串**，是假阴性。故 §10.2 改为具名正则并新增结构式 R9 |

### 10.2 行级判据口径 v2（检索式与谓词）

检索式（固定，审计须逐条使用同一正则；`\s` 为正则空白）：

| 编号 | 正则 | 用意 |
|---|---|---|
| R1 | `build-verified-approved` | 旧唯一终态的显名 |
| R2 | `表示任务完成` | 「任务完成」的**规则义**用法（排除「其他任务完成」类子串噪声） |
| R3 | `任务完成（final` | 状态图的 final 标注 |
| R4 | `测试线` | 测试线的规范性表述 |
| R5 | `进入测试` | 转移说明文字 |
| R6 | `对代码进行测试` | Tester 职责句 |
| R7 | `测试代码` | 产物／职责列举 |
| R8 | `测试方案` | 产物／职责列举 |
| R9 | `build-reviewed-approved\s*(→\|->)\s*build-verified(?!-)` | **结构式**：不依赖关键词，直接抓「审计通过→测试线」这条边（`:473`、`agents/tester.md:50` 即由此抓出） |

**谓词 P（命中行的豁免条件，三选一即成立）**：① 该行含 `has_code`；② 该行引 `§5.2` 或 `§7.2`；③ 该行位于 `13` §5.2 小节内（该小节本身即判定来源）。

**本轮预跑读数（HEAD `e769ba9`，口径 v2，脚本计数）**：扫描域 26 个 `.md`｜命中 **64 行／89 行-串对**｜其中不满足 P 者 **38 行**（`13` 21／`agents/tester.md` 6／`AGENTS.md` 5／`14` 4／`15` 2）。38 行每行由 §10.3 的某一 M 项或 §10.4 的登记表覆盖；覆盖映射见下。**这一句在写入本节时曾记为 40 行／`13` 23 行**——那是只套用谓词 P 的第 ①② 支、漏套第 ③ 支（「行在 §5.2 小节内」）所得；补上第 ③ 支后 `13:332`（正面清单第 2 类「测试代码」）与 `13:346`（缺省处理第 1 则「进入测试线」）落入豁免，二者本身即判定条款、无需再加前提。差值 2 行、涉及载体 1 件，已按本节口径重跑核正。
**与 PM／Reviewer 读数的并列登记**：同一提交上、前轮七串口径得 26 文件／61 行／84 对。口径 v2 与它的差＝R2／R3 精确化去掉的假命中＋R9 新增的假阴性行＋P③ 豁免的 §5.2 两行。**两个读数都保留，不因口径变更而宣称对方取数有误**。

**行级覆盖映射（38 行 → 处置项，取证脚本逐行核对）**：

| 载体 | 不满足 P 的行 | 处置项 |
|---|---|---|
| `13` | `:86` `:87` `:88` `:89` | M-30 |
| `13` | `:175` `:240` `:243` | M-31 |
| `13` | `:200` `:203` | M-32 |
| `13` | `:260` | M-33 |
| `13` | `:371` | M-34 |
| `13` | `:394` | M-35 |
| `13` | `:447` `:448` | M-28a（主链块 `:445`–`:448` 四行整体替换，命中两行随块消除） |
| `13` | `:465` | M-28b |
| `13` | `:473` | M-28c |
| `13` | `:518` `:520` | M-36 |
| `13` | `:567` | M-37 |
| `13` | `:621` `:622` | M-29a |
| `AGENTS.md` | `:81` `:86` | M-38 |
| `AGENTS.md` | `:110` `:111` `:179` | M-39 |
| `agents/tester.md` | `:8` `:23` `:24` `:35` `:49` `:50` | M-41 |
| `14` | `:234` `:236` | M-40 |
| `14` | `:321` `:335` | §10.4（历史变更行，不回改） |
| `15` | `:75` | §10.4（目录结构说明，不声明进入条件） |
| `15` | `:164` | M-42 |

映射为**满射且无余行**：38 行全部有归属，§10.3／§10.4 未指向任一命中行的处置项另列如下——M-35 的 `13:393`、M-36 的 `13:516`、M-40 的 `14:232`、M-38 的 `AGENTS.md:80` 均**非命中行**，加注只出于同块读者推定的一致性（各节已就地标明「非命中行」）。

### 10.3 返工轮变更项 M-28 ～ M-42（逐字待写入文本）

统一形制：**内容锚**为定位与唯一性判据（该行原文片段）；「追加句」＝在该行原文**末尾**原样接写给定文本、不改原文；「整行替换」＝以给定文本替换该行。```text 块内按原文照登，未加反引号处即不加。

**M-28**｜`docs/management/13-task-model.md` §7.3 三处（审批规格第 1 项）

- **M-28a**（主链 ```text 块，现 `:445-448`｜内容锚：`        → build-reviewed → build-reviewed-approved → build-verified`）：将该块内自 `proposed → proposed-reviewed` 起的四行整体替换为：

```text
proposed → proposed-reviewed → proposed-approved → designed
        → designed-reviewed → designed-approved → build
        → build-reviewed → build-reviewed-approved
        ├─（has_code = true）→ build-verified → build-verified-approved（测试线终态）
        └─（has_code = false）→ 免测试线，build-reviewed-approved 即终态（见 §7.2）
```

- **M-28b**（常见分支，现 `:465`｜内容锚：`build-reviewed-approved → build-verified                  （审计通过，进入测试阶段）`）：整行替换为两行：

```text
build-reviewed-approved → build-verified                  （仅 has_code = true：审计通过，进入测试阶段；见 §5.2／§7.2）
build-reviewed-approved → 终态                             （has_code = false：免测试线，本状态即任务终态；见 §7.2）
```

- **M-28c**（§7.3 末注句，现 `:473`｜内容锚：`Tester 只置位 `build-reviewed-approved → build-verified``）：整行替换为：

> `build-verified` 及其四个结论态由 **PM 审批**产出（见 §2.3 角色列），且**仅对 `has_code = true` 的任务存在**；Tester 只置位 `build-reviewed-approved → build-verified`（`has_code = false` 无此转移，见 §5.2／§7.2）。PM 判 `build-verified-rejected` 后的返工**默认由 Coder 执行**（退回 `build`），Tester 不再介入；若结论为设计或需求无法满足，则由 Architect 执行回退（退回 `designed` 或 `proposed`）。

**M-29**｜附录 A 与变更记录（审批规格第 2 项，采「**补作修改**」路线：使 `14:325` 所列对象与实际改动相符，不回改既存历史行）

- **M-29a**（`13` 附录 A 现 `:621`／`:622`｜内容锚：`| \`completed\` | \`build-verified-approved\` | 全局终态 |` 与 `| \`verified\` | \`build-verified-approved\` | 测试通过后进入终态 |`）：两行整行替换为：

| `completed` | `build-verified-approved` | **旧状态词汇迁移语境**下的映射（本表整体仅用于历史词汇对照，见本节标题）；新规则的任务终态按 §7.2 双分支，`has_code = false` 的任务终态为 `build-reviewed-approved`，**不得据本行推定单一终态** |
| `verified` | `build-verified-approved` | 同上：该映射仅适用 `has_code = true`（测试通过后进入终态）；`has_code = false` 见 §7.2 |

- **M-29b**（`docs/management/14-responsibility-boundaries.md` §11 变更表末行之后追加一行｜内容锚：现 `:325` 行首 `| 2026-11-04 | \`13-task-model.md\` §2.1／§2.3／§3.1`）：追加：

| 2026-11-04 | T-20261103-001 返工轮：`13` §2.3／§3.2／§3.3／§3.4／§4／§6／§6.1／§7.3／§9／§10／附录 A、`AGENTS.md` §2 状态图／§2 示例／§4 步骤 4、`14` §7.1 责任传递图、`15` §6.3 里程碑标签、`agents/tester.md` §1／§3／§4／§6 | 交付审计判 `build-reviewed-rejected`：`13` §7.3 主链与常见分支仍无条件导向测试线（J-6 行级失败），附录 A 单终态表述未衔接 §7.2；本行同时使上一行的「修改对象」枚举与实际改动相符 | 生命周期各段的测试线表述统一加 `has_code = true` 前提并补 `has_code = false` 终态分支；附录 A 两行标明旧词汇迁移语境并交叉引用 §7.2；示例行与角色手册操作步骤就地标注适用前提 | 经用户批准后生效 |

**M-30**｜`13` §2.3 状态表四行（现 `:86`–`:89`｜内容锚各行的说明列分别含 `结论为通过`／`结论为缺少某个条件`／`结论为不通过。返工路径`／`结论为延迟处理，仅表示排序或优先级关系`，且四行的状态列依次为 `build-verified-approved`／`-blocked`／`-rejected`／`-deferred`）：四行说明列**末**各追加同一句：

（本行仅适用于 `has_code = true` 的任务；`has_code = false` 不进入 `build-verified*` 状态，见 §7.2）

**M-31**｜`13` §3.2 一行＋§3.4 两行（现 `:175`／`:240`／`:243`｜内容锚：`| \`build-verified\` | \`build-verified-approved\` | 测试结论：通过 |`、`| \`build-verified-blocked\` | \`build-verified-approved\` | 阻塞条件已消除，重新进入批准流程，批准结果是通过 |`、`| \`build-verified-deferred\` | \`build-verified-approved\` | 延迟处理结束，重新进入批准流程，批准结果是通过 |`）：三行说明列末各追加：

（仅 `has_code = true` 的任务有此转移，见 §7.2）

> `:240` 与 `:243` 的尾串「批准结果是通过」重复出现，故锚点取**整行原文**（上列三行各自唯一），不得用短串批量替换。

**M-32**｜`13` §3.3 禁止列表（```text 块内，现 `:200`／`:203`）：`:200`「测试线必须在审计线批准后进入：」末追加`（仅 has_code = true 的任务有测试线，见 §7.2）`；`:203`「  - 测试线不会反过来回退到审计阶段。」末追加`（has_code = false 的任务不进入测试线，见 §7.2）`。

**M-33**｜`13` §4 审批链（```text 块内，现 `:260`｜内容锚：`交付审批（测试线）：build-verified → build-verified-approved`）：把该行行首标签 `交付审批（测试线）` 改为 `交付审批（测试线，仅 has_code = true 的任务）`（其余原样），并在其后插入一行：

              （has_code = false 的任务无测试线审批：交付审批（审计线）的 approved 即终态，见 §7.2）

**M-34**｜`13` §6 交付物表（现 `:371`｜内容锚：产物列 `审计结论`、状态列 `build-verified-approved`、载体列 `tasks/T-XXXX/build-verified-approval-report.md` 的整行）：产物列末追加`（仅 `has_code = true` 的任务产出本行交付物，见 §7.2）`。

**M-35**｜`13` §6.1 成熟度表（现 `:393`／`:394`｜内容锚：`| 4 | 测试验收稿 | 测试验收已完成 | ` 起行、`| 5 | 最终稿 | 对测试验收的审批已完成，为最终结论 | ` 起行）：两行「达到条件」列末各追加`（仅 `has_code = true`；免测试任务的最终级见第 3 级／§7.2）`。（`:393` 非 J-6 命中行，随行为一致性一并加注。）

**M-36**｜`13` §9 流程示例（现 `:516`／`:518`／`:520`｜内容锚：`Tester 测试实现结果（build-verified）`、`PM 审批测试线结论（build-verified-approved）`、`  终态（build-verified-approved）`）：三行末各追加`（has_code = true）`。

**M-37**｜`13` §10 记录行示例（现 `:567`｜内容锚：`T-20261017-001 build-reviewed-approved -> build-verified by Tester:kilo`）：行末追加` | 测试完成（示例任务 has_code = true）`。

**M-38**｜`AGENTS.md` §2 状态图（现 `:80`／`:81`／`:86`｜内容锚：独立成行的 `build-verified`、`  ├── build-verified-approved`、独立成行的 `build-verified-approved`（其后即 `  └── 任务完成（final｜has_code = true）`））：三行整行替换为 `build-verified（仅 has_code = true 的任务进入）`、`  ├── build-verified-approved（has_code = true）`、`build-verified-approved（has_code = true 的任务终态）`。

**M-39**｜`AGENTS.md` §2 示例与 §4 步骤（现 `:110`／`:111`／`:179`）：`:110` 行末追加`（示例任务 has_code = true）`；`:111` 行末追加`（has_code = true）`；`:179`（内容锚：`4. PM 审批 Reviewer 的输出结果；任务走测试线时一并审批`）整行替换为：

4. PM 审批 Reviewer 的输出结果；仅 `has_code = true` 的任务走测试线并一并审批 Tester 的输出结果（`has_code = false` 免测试线，见 `13` §7.2）。

**M-40**｜`docs/management/14-responsibility-boundaries.md` §7.1 责任传递图（现 `:232`／`:234`／`:236`｜内容锚：`Tester 测试实现结果（build-verified）`、`PM 审批测试线结论（build-verified-approved）`、`终态（build-verified-approved）`）：三行末各追加`（`has_code = true`）`。（`:232` 非命中行，与 `:234`／`:236` 同块，一并加注以免读者按该块推定必经测试线。）

**M-41**｜`agents/tester.md`（现 `:8`／`:23`／`:24`／`:35`／`:49`／`:50`）：`:8`（内容锚 `依据**已生效的设计文档**对代码进行测试`）末追加`（仅 `has_code = true` 的任务；判定见 `13` §5.2，`has_code = false` 在 `build-reviewed-approved` 结案，见 `13` §7.2）`；`:23`／`:24` 载体列末各追加`（仅 `has_code = true` 的任务产出）`；`:35`（内容锚 `> 测试结论态（`）末追加`（这些结论态仅对 `has_code = true` 的任务存在，见 `13` §7.2）`；`:49`（内容锚 `2. 编写测试方案 → 测试代码`）末追加`（仅 `has_code = true` 的任务执行本步）`；`:50`（内容锚 `3. 更新任务台账并提交`）末追加`（仅 `has_code = true`；`has_code = false` 无此转移，见 `13` §7.2）`。

**M-42**｜`docs/management/15-version-control-convention.md` §6.3 标签示例（现 `:164`｜内容锚：`task/T-YYYYMMDD-NNN/build-verified-approved`）：整行替换为两行：

task/T-YYYYMMDD-NNN/build-verified-approved   # has_code = true 的终态
task/T-YYYYMMDD-NNN/build-reviewed-approved   # has_code = false 的终态（13 §7.2）

### 10.4 行级豁免登记表（谓词 P 之外的全部命中行，逐行）

| 命中行（内容锚） | 处置与成立理由 |
|---|---|
| `14:321`（内容锚：`\| 2026-10-20 \| 本批治理修订：`） | **历史变更记录行**：记述 2026-10-20 那次修订当时所改对象与其时的状态机形制；变更表 append-only，回改等于篡改历史。新规则由 M-29b 新行承载 |
| `14:335`（内容锚：`\| \`13-task-model.md\` \| 生效 \| §2.2/§2.3 返工路径`） | **本轮重新指认（原 `:335` → 现 `:335`，内容锚＝`14` §11「修订明细」中 `13-task-model.md` 那一行）**：该行记述 2026-10-20 那次修订，含「`§7.3` 常见分支增补 5 条」等既往表述，属历史行，append-only，不得回改。**注：返工实测发现本节初版此处内容锚写的是另一行（`\| \`12-multi-agent-roles.md\` \| 生效 \| §3.1 删除`），该行不含 R1–R9 任一命中、本不属豁免对象**；按 §10.4「双向差集为空」的对账义务，初版锚点经复跑已订正为本行 |
| `15:75`（内容锚：`任务的**产物**（需求说明、设计、审计报告、测试方案/代码/报告等）`） | 目录结构说明，不声明进入条件；测试产物仅在测试线存在时产出，已由 `13` §6（M-34）与 §7.2 限定 |

**对账义务**：交付后按 §10.2 口径重跑，**不满足 P 的命中行集合须与本表逐行相等（双向差集为空）**；出现本表之外的未满足行即判 J-13 FAIL 并回设计段。

### 10.5 §4 变更矩阵订正（追加，不回改前轮表）

| 载体 | 返工轮新增变更项 | 前轮是否已列该载体 |
|---|---|---|
| `docs/management/13-task-model.md` | M-28（§7.3）、M-29a（附录 A）、M-30～M-37 | 是——但 §7.3／附录 A 的**小节**未入矩阵＝P0 根因 |
| `docs/management/14-responsibility-boundaries.md` | M-29b（§11 变更表新行）、M-40（§7.1 图） | 是——§7.1 图前轮仅 M-22 覆盖注句，未覆盖图体 |
| `AGENTS.md` | M-38（§2 状态图）、M-39（§2 示例／§4 步骤 4） | 是——前轮 M-22／M-24 未覆盖示例行 |
| `docs/management/15-version-control-convention.md` | M-42（§6.3 标签示例） | 是——§6.3 前轮入「不改清单」，本轮改为加注 |
| `agents/tester.md` | M-41（§1／§3／§4／§6） | 是——前轮 M-19 只覆盖 :8／:31 两句，未做行级覆盖 |

前轮「不改清单」中与本轮冲突的两行据此刻销并由本节取代：① `15:163`（现 `:164`）标签示例「不改」→ 改 M-42 加注；② `13` 附录 A「靠读推保持一致、不加脚注」→ 改 M-29a 加注。**其余「不改清单」行的理由仍成立，但其行号引用已随 M-1～M-26 落地而漂移，审计时按内容锚核对。**

### 10.6 返工交付边界（Coder）

1. **M-1～M-27 已随 `3faf1d1` 落地，返工交付只执行 M-28～M-42**；重复执行前轮项会造成双份文本插入。
2. **单次提交**（承 §6 第 2 步），顺序：`13`（M-28 → M-37，按节次自前向后）→ `AGENTS.md`（M-38／M-39）→ `14`（M-40）→ `15`（M-42）→ **M-29b 最后落**，使变更行的「修改对象」列如实描述已完成的全部改动。
3. **交付前重取基线**（壬 甲／`14` §6.5）：对六件载体重取 HEAD 文本并逐条比对本节内容锚；任一锚失配或不唯一即停止并回设计段。
4. `output_contracts`：M-28～M-42 的载体全部已在台账 14 项内，**无需扩围**。

### 10.7 判据增补（返工轮）

| 判据 | 可机械核对的形式 |
|---|---|
| **J-6** | 以本节 v2 文本整体取代 §7 原 J-6 行：行级谓词 P ＋ §10.4 登记表，双向差集为空 |
| **J-13** | `13` §7.3 节内匹配 R9 的每一行均含 `has_code`；同节存在 `has_code = false` 的终态分支行（M-28a／M-28b／M-28c 逐项对账，3 处齐） |
| **J-14** | 变更记录与实际相符：M-29b 新行的「修改对象」枚举 ⊆ 返工提交 `git diff --name-status` 文件集；且 `13` 附录 A 在返工提交中**确有改动**（使 `14:325` 所列对象成立） |
| **J-15** | 前轮落地文本未被回改：返工提交的 diff 不得删除 §5.2 小节、§7.2 双终态句、§3.3 三条禁止句（以文本片段断言，不以行数断言） |

### 10.8 本轮未含项与余量（不作推定）

- 台账 `:24`（Coder 交付记录行）所载「J-6 按上述口径闭合」「矩阵外未覆盖命中 **0**」是**文件级结论**，与行级实测不符（PM 报告 §1 已认定）。该行属 append-only 历史记录，**我不回改他人记录行**，订正由本节与本轮新记录行承载；依 `14` §6.2，交付段的自陈不等于实质满足。
- `14:325` 的「列了附录 A 而实际未改」采**补作修改**路线（M-29a），不删列；若审计认为仍须删列，属设计段返工项。
- §10.2 的 R1–R9 **不声明穷尽**：它们针对本轮已发现的假命中与假阴性两类失效模式，无法保证覆盖未来的表述变体（例如不含「测试线」三字的义务句）。结构性补强（状态机图与转移表的机器对账）超出本任务范围，登记为**未决余量**。
- §10.4 三行的理由仍待审计判定；其中 `14:321`／`14:335` 依赖「变更表 append-only」这一既存纪律——若审计不认同该纪律辖及历史行的**说明列**，则须改判为「加注」并追加 M 项。
- 本轮对 design.md **已提交文本**的句内修订仅一处：§7 的 J-6 行被 v2 整体取代（依审批报告 §5 第 3 项「补强 J-6」的授权）；§5 变更项 M-1～M-27、§4 矩阵、§9 未含项的前轮文本均未回改，返工内容全部以 §10 追加。
- §10 系本轮新写、尚未提交；其中 §10.2 的预跑读数在同轮内自我更正一次（「不满足 P 者 40 行／`13` 23 行」→「38 行／`13` 21 行」，根因＝漏套谓词 P 第 ③ 支），并补入行级覆盖映射表。该更正在提交前完成，不属对已落地文本的回改。
- 未裁庚，未重开 `13` §8／`14` §9 归属冲突，未写 `has_code` 字段行（承 §2／§9）。
- 台账 `status:` 现滞后一格（记录行末条为 `build-reviewed-rejected`，`:6` 仍写 `build-reviewed`），本轮置 `designed` 时一并闭合，不改历史记录行。
