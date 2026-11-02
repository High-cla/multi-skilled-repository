<p align="center">
  <img src="https://img.shields.io/badge/Type-Agent%20Skills-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Language-ZH%20%7C%20EN-green?style=flat-square" />
  <img src="https://img.shields.io/github/license/High-cla/cmd-powershell-pitfalls?style=flat-square" />
</p>

<h1 align="center">AI Agent Skills</h1>
<p align="center"><i>Curated skill collection for AI agents — reusable knowledge, proven workflows.</i></p>

---

> **中文**: AI 智能体技能合集仓库。每个技能是一个独立的 `SKILL.md`，封装特定领域的专家知识和最佳实践。
>
> **English**: A collection of reusable AI agent skills. Each skill is a self-contained `SKILL.md` with domain-specific knowledge and proven workflows.

---

## 📦 Skills

| Skill | Description |
|-------|-------------|
| [`cmd-powershell-pitfalls`](./skills/cmd-powershell-pitfalls/SKILL.md) | CMD + PowerShell 混合脚本避坑指南 — 35 条规则与代码示例，涵盖代码页/编码、引号与变量展开、路径、退出码、UAC 最小权限和 MSYS2 参数转换。Use when writing or debugging `.cmd`/`.bat` scripts with embedded PowerShell. |
| [`cli-first-decision`](./skills/cli-first-decision/SKILL.md) | CLI-First Decision 3.7 — DSH/FastCtx 优先路由、ast-grep、codebase-memory、DAG 并行，以及基于 run_code + 自动生成 tools:sdk 的 PTC runtime SDK 编排。GitHub/Context7 插件不是依赖。 |
| [`customize-dsh`](./skills/customize-dsh/SKILL.md) | DeepSeek Harness (DSH) 自定义修改指南 — settings.yaml、profiles/*/cordis.patch.yml 与 bundles、技能创作与修复、agent preset、MCP server (dsh-mcp-client)、cordis 插件、自定义工具、slash 命令、启动失败与 patch 报错诊断。Use when editing or creating DSH configs/extensions. |
| [`game-item-spawner`](./skills/game-item-spawner/SKILL.md) | 游戏模组"网页点击生成物品"系统 — 逆向找生成API、提取物品目录(内嵌JSON)、模组内嵌本地HTTP服务器(localhost:PORT)、网页物品浏览器(分类/搜索/点击生成)、GitHub Pages托管+全链路验证。Use when user wants in-game item spawning with a visual web UI (spawn item, item browser, cheat generator). |

---

## 🚀 快速入口 | Quick Entry

### cmd-powershell-pitfalls

编写 Windows 批处理（`.cmd` / `.bat`）并内嵌 PowerShell 命令时，常见的陷阱与解决方案。

**17 条核心规则预览**:

| # | 类别 | 问题 | 严重性 |
|---|------|------|--------|
| 1 | 🔤 编码 | 区分控制台代码页、PowerShell 管道与文件编码 | 🟡 Medium |
| 2 | 🔄 循环 | `for` 循环体内 `)` 被当作结束符吞掉 | 🔴 High |
| 3 | ❝ 引号 | `\\\"` 在 CMD 字符串中无效 | 🔴 High |
| 4 | 🧩 路径对象 | 使用 `Join-Path` 处理 `PathInfo` 和路径拼接 | 🟡 Medium |
| 5 | ⏳ 延迟展开 | 括号块读取更新值时按需使用 `!var!`，并注意字面 `!` | 🟡 Medium |
| 6 | 📦 重定向 | 括号 `()` 与输出重定向 `>` 的优先级问题 | 🟡 Medium |
| 7 | ➖ 续行 | `^` 在双引号内不起作用 | 🟡 Medium |
| 8 | 💲 变量传递 | `$` / `%` 在 CMD → PowerShell 的传递规则 | 🟡 Medium |
| 9 | 📝 文件编码 | `Set-Content` 在各 PowerShell 版本的默认编码差异 | 🟡 Medium |
| 10 | ❌ 错误处理 | `%ERRORLEVEL%` 与 `$LASTEXITCODE` 的正确使用 | 🟡 Medium |
| 11 | 🚪 退出码 | PowerShell 退出码需显式传递回 CMD | 🟡 Medium |
| 12 | 📁 路径 | `%~dp0` 的正确使用与拼接方式 | 🟢 Low |
| 13 | 🔍 过滤 | `findstr` 正则语法有限 | 🟢 Low |
| 14 | 🔗 管道 | `\\|` 在 CMD 字符串中不会触发管道解析 | 🟢 Low |
| 15 | ⚡ 性能 | `.NET` 直调 vs Cmdlet 的性能差距 | 🟢 Low |
| 16 | 📄 追加 vs 重定向 | 循环内 `>>` 逐个打开文件 vs 一次性 `>` | 🟢 Low |
| 17 | ✅ 检查清单 | 写完脚本后逐项自查 | — |

➡️ 完整内容: [`skills/cmd-powershell-pitfalls/SKILL.md`](./skills/cmd-powershell-pitfalls/SKILL.md)

### cli-first-decision

**核心规则**：本地文件优先 FastCtx；终端批处理优先 CLI；结构搜索使用 ast-grep；调用链和影响面使用 codebase-memory；多步骤工具操作使用 DSH PTC 的 run_code + tools:sdk runtime-language 组合。先确认当前 SDK 签名，再按 DAG 合并/并行，最后验证结果。

| 场景 | 首选 |
|------|------|
| 文件读取/搜索 | FastCtx inspect_local_file / grep / glob |
| 跨文件机械替换 | FastCtx replace（先 dry-run） |
| 结构搜索/改写 | sg（ast-grep） |
| 符号/调用链/影响面 | codebase-memory |
| JSON/YAML / HTTP | jq / yq / curl |
| 长任务 | run_background + job_output |
| MCP 退路 | 仅使用已 bake 的 mcp2cli |

GitHub、Context7 插件不是本技能的本地运行依赖；只有当前运行时真实注册时才可选用。从零开始先进行架构选型与网络官方文档调研，并明确速度/内存优先优化；并新增 DSH/FastCtx/CLI 上游权威文档索引与 Context7 文档检索流程；附带 [74 个评估用例](./skills/cli-first-decision/evals/evals.json)。

➡️ [技能主体](./skills/cli-first-decision/SKILL.md) · [工具总参考](./skills/cli-first-decision/references/REFERENCE.md) · [CLI 工具链](./skills/cli-first-decision/references/CLI-TOOLS.md) · [权威文档索引](./skills/cli-first-decision/references/AUTHORITATIVE-SOURCES.md) · [架构设计与官方文档调研](./skills/cli-first-decision/references/ARCHITECTURE-DESIGN.md) · [编程规则](./skills/cli-first-decision/references/PROGRAMMING-RULES.md) · [工程原则](./skills/cli-first-decision/references/ENGINEERING-PRINCIPLES.md) · [评估用例](./skills/cli-first-decision/evals/evals.json)

### customize-dsh

编辑或创建 DeepSeek Harness (DSH) 自身配置与扩展时的权威参考：

| 定制面 | 关键文件/机制 |
|--------|--------------|
| 配置 | `settings.yaml`（默认模型/权限预设/主题） |
| Profile/Patch | `profiles/*/cordis.patch.yml`、`package.json` (`dsh.profile.bundles`) |
| 技能 | `~/.dsh/skills`、`~/.agents/skills`、项目 `.dsh/skills`（6 层 rank） |
| MCP | `@deepseek-ai/dsh-mcp-client`（stdio / streamable-http） |
| 插件/工具/命令 | cordis 插件包、defineTool、`ctx.commands.register` |

涵盖配置生效时机（HMR/热重载）、Profiles 层叠与 patch 语义（insert/disabled/整体替换）、反直觉陷阱（空/仅注释 patch 文件 throws 须用 `[]`）、区分当前 Cordis Agent preset 与已废弃的旧式目录 preset，以及逃生舱（`dev_fix_patch`/`dev_heal_links`/`dev_clear_routes`/`dev_uninject_plugin`）等。附带 `references/AUTHORITATIVE-SOURCES.md` 权威来源索引、Context7 检索流程和 `evals/evals.json`（12 个回归评估用例）。

➡️ 完整内容: [`skills/customize-dsh/SKILL.md`](./skills/customize-dsh/SKILL.md)

### game-item-spawner

为游戏模组搭建"网页点击生成物品"系统——网页物品浏览器点"生成"→ 物品进游戏背包。

**核心架构**: 网页只用 HTTP，与游戏解耦；模组是本机服务。

| 环节 | 说明 |
|------|------|
| 逆向 | 找游戏生成API（`DirectoryMaster.Item` 类）+ 主背包入口 |
| 提取 | 内嵌资源 JSON → `items_data.js`（ID/名称/分类） |
| 服务器 | 模组内嵌 HttpListener (localhost:26880)，**HTTP线程只入队、主线程OnUpdate消费**（IL2CPP防跨线程崩） |
| 网页 | 分类侧栏+搜索+卡片+生成按钮+状态点+Toast，可托管 GitHub Pages |
| 验证 | mock 服务器模拟 /api/health+/api/spawn，无游戏也能全链路测 |

**换游戏复用**: 骨架 100% 通用，仅改 3 处（创建API/主背包/入包API）。附带 `evals/evals.json`（3 个评估用例）。

➡️ 完整内容: [`skills/game-item-spawner/SKILL.md`](./skills/game-item-spawner/SKILL.md)

---

## 🏗 目录结构 | Directory Structure

```
.
├── .gitignore
├── README.md
└── skills/
    ├── cmd-powershell-pitfalls/
    │   └── SKILL.md
    ├── cli-first-decision/
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── REFERENCE.md
    │   │   ├── CLI-TOOLS.md
    │   │   ├── AUTHORITATIVE-SOURCES.md
    │   │   ├── ARCHITECTURE-DESIGN.md
    │   │   ├── PROGRAMMING-RULES.md
    │   │   └── ENGINEERING-PRINCIPLES.md
    │   └── evals/
    │       └── evals.json
    ├── customize-dsh/
    │   ├── SKILL.md
    │   └── evals/evals.json
    └── game-item-spawner/
        ├── SKILL.md
        ├── scripts/
        ├── assets/
        └── evals/evals.json
```

---

## 🤝 贡献 | Contributing

有新技能想加入合集？欢迎提 Issue 或 PR！

Want to add a new skill? Feel free to open an issue or PR.

---

## 📄 许可 | License

MIT
