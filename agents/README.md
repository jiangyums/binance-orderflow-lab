# 角色运行手册（agent prompts）

本目录存放各 agent 的**运行手册（提示词）**。它是 `docs/management/` 规则的**角色切片投影**：规则是单一事实来源（SSOT），本目录只写“该角色要做什么、怎么做”。

## 1. 分层

```text
docs/management/12、13、14、15   ← SSOT（规则，权威）
        ↓ 角色切片 / 投影
agents/*.md                      ← 角色运行手册（= 提示词）
        ↓ 各工具加载
.clinerules/ + AGENTS.md（Cline）
AGENTS.md 原生注入 → agents/architect.md（Qoder）
.opencode/agents/（opencode）
.kilo/agents/（kilo）
agents/（Reviewer，SSOT 角色切片）
.github/agents/reviewer.agent.md（VS Code Copilot 的 Reviewer 加载入口）
```

## 2. 手册索引

| 角色 | 参与者 | 统一手册 | 工具加载入口 |
|---|---|---|---|
| PM（项目经理 / 审批人） | Cline | `agents/pm.md` | `.clinerules/pm-role.md`、`AGENTS.md`（原生注入） |
| Architect（架构师） | Qoder | `agents/architect.md` | `AGENTS.md`（原生注入） |
| Coder（代码编写者） | opencode | `agents/coder.md` | `.opencode/agents/coder.md`（agent 定义，提示词正文指向本手册） |
| Tester（测试者） | kilo | `agents/tester.md` | `.kilo/agents/tester.md`（agent 定义，提示词正文指向本手册） |
| Reviewer（审查员） | VS Code Copilot | `agents/reviewer.md` | `.github/agents/reviewer.agent.md`（agent 定义，提示词正文指向本手册） |

## 3. 编写原则

1. **指针优先**：引用规则文件名与章节，不复制全文，避免“两份真相”漂移。
2. **角色切片**：只写该角色涉及的状态与产物。
3. **与规则一致**：内容必须与 `docs/management/12/13/14/15` 一致；一致性由 Reviewer / PM 审计。

## 4. 加载

- 每个 agent 开始任务前，先读根目录 `AGENTS.md` 与本目录中自己的手册，再读手册引用的规则章节。
- **注入副本仅为线索，一律以文件本体为准**（上下文快照可能过期，见 `AGENTS.md` 的「刷新纪律」）。
- 加载机制（2026-10 验证）：

  | 工具 | 原生加载 `AGENTS.md` | 角色手册加载入口 |
  |---|---|---|
  | Cline | 是 | `.clinerules/pm-role.md`（首屏加载令） |
  | Qoder | 是（系统每轮以 `<loaded_context>` 注入） | `AGENTS.md` → `agents/architect.md` |
  | opencode | 是（`.opencode/` 与 `.opencode/agents/` 为项目级加载目录） | `.opencode/agents/coder.md` |
  | kilo | 是（`.kilo/`、`.kilo/agents/` 为项目级加载目录） | `.kilo/agents/tester.md` |
  | Reviewer | VS Code Copilot：Copilot harness 原生加载 `AGENTS.md` | `agents/reviewer.md`（VS Code Copilot 经 `.github/agents/reviewer.agent.md` 加载） |

- opencode / kilo 的 agent 定义文件本身**不含规则正文**，仅含「强制读取本目录对应手册」的加载令与要点摘要，以避免出现两份真相（见 §3 指针优先原则）。
- `.opencode/` 与 `.kilo/` 内可再生成的工具状态（`index/`、`node_modules/`、锁文件等）由根 `.gitignore` 排除；agent 定义文件纳入版本控制（见 `docs/management/15-version-control-convention.md` §3.1）。
- `.github/agents/` 同理：`.github/agents/*.agent.md` 为 VS Code Copilot 的 agent 定义（治理资产，纳入版本控制），根 `.gitignore` 不排除 `.github/`。
- Reviewer 的 `.github/agents/reviewer.agent.md` 工具面含 `git` / `terminal`，用于对审计报告与任务台账执行「落盘即提交」`git add` / `git commit` / `git push`（依 `14` §6.0）。

## 5. 说明

- 本目录为**项目治理文档**（纳入版本控制；见 `docs/management/15-version-control-convention.md` §3.1）。
- 本目录不代表任何状态已生效；规则的生效状态见 `docs/management/00-governance-index.md`。
