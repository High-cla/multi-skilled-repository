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
| [`cmd-powershell-pitfalls`](./skills/cmd-powershell-pitfalls/SKILL.md) | CMD + PowerShell 混合脚本避坑指南 — 35 条规则与代码示例，涵盖编码、引号逃逸、延迟展开、管道编码、权限提权等场景。Use when writing or debugging `.cmd`/`.bat` scripts with embedded PowerShell. |
| [`cli-first-decision`](./skills/cli-first-decision/SKILL.md) | CLI-First 决策矩阵 — 每次 `task()` 前判断是否可用 CLI 工具更快解决。包含 git-sed, fd-find, rg-search, ast-grep, jq-query 等工具速查表。Use before any agent dispatch to check CLI alternatives. |

---

## 🚀 快速入口 | Quick Entry

### cmd-powershell-pitfalls

编写 Windows 批处理（`.cmd` / `.bat`）并内嵌 PowerShell 命令时，常见的陷阱与解决方案。

**17 条核心规则预览**:

| # | 类别 | 问题 | 严重性 |
|---|------|------|--------|
| 1 | 🔤 编码 | `chcp 65001` 破坏 `%VAR%` 展开 | 🔴 High |
| 2 | 🔄 循环 | `for` 循环体内 `)` 被当作结束符吞掉 | 🔴 High |
| 3 | ❝ 引号 | `\"` 在 CMD 字符串中无效 | 🔴 High |
| 4 | 🧩 对象类型 | `Get-Location` 返回 `PathInfo` 而非字符串 | 🔴 High |
| 5 | ⏳ 延迟展开 | 循环内改变量必须用 `!var!` | 🔴 High |
| 6 | 📦 重定向 | 括号 `()` 与输出重定向 `>` 的优先级问题 | 🟡 Medium |
| 7 | ➖ 续行 | `^` 在双引号内不起作用 | 🟡 Medium |
| 8 | 💲 变量传递 | `$` / `%` 在 CMD → PowerShell 的传递规则 | 🟡 Medium |
| 9 | 📝 文件编码 | `Set-Content` 在各 PowerShell 版本的默认编码差异 | 🟡 Medium |
| 10 | ❌ 错误处理 | `%ERRORLEVEL%` 与 `$LASTEXITCODE` 的正确使用 | 🟡 Medium |
| 11 | 🚪 退出码 | PowerShell 退出码需显式传递回 CMD | 🟡 Medium |
| 12 | 📁 路径 | `%~dp0` 的正确使用与拼接方式 | 🟢 Low |
| 13 | 🔍 过滤 | `findstr` 正则语法有限 | 🟢 Low |
| 14 | 🔗 管道 | `\|` 在 CMD 字符串中不会触发管道解析 | 🟢 Low |
| 15 | ⚡ 性能 | `.NET` 直调 vs Cmdlet 的性能差距 | 🟢 Low |
| 16 | 📄 追加 vs 重定向 | 循环内 `>>` 逐个打开文件 vs 一次性 `>` | 🟢 Low |
| 17 | ✅ 检查清单 | 写完脚本后逐项自查 | — |

➡️ 完整内容: [`skills/cmd-powershell-pitfalls/SKILL.md`](./skills/cmd-powershell-pitfalls/SKILL.md)

### cli-first-decision

**核心规则**: 每次 `task()` 前，先问有没有现成的 CLI 工具能更快解决。

| 场景 | 首选工具 | 耗时 |
|------|---------|------|
| 批量文本替换 | `git-sed` | <1s |
| 文件查找 | `fd-find` | <1s |
| 内容搜索 | `rg-search` | <1s |
| AST 搜索替换 | `ast-grep` | <1s |
| JSON 查询 | `jq-query` | <1s |
| HTTP API 测试 | `git-curl` | <1s |
| 模糊过滤 | `fzf-filter` | <1s |
| 打包解压 | `git-tar` | <1s |
| 换行符转换 | `git-dos2unix` | <1s |
| ✅ 语义/决策 | 派代理 | 数十秒+ |

➡️ 完整内容: [`skills/cli-first-decision/SKILL.md`](./skills/cli-first-decision/SKILL.md)

---

## 🏗 目录结构 | Directory Structure

```
.
├── .gitignore
├── README.md                          # 本文件
└── skills/
    ├── cmd-powershell-pitfalls/
    │   └── SKILL.md                   # CMD + PowerShell 混合脚本避坑指南
    └── cli-first-decision/
        └── SKILL.md                   # CLI-First 决策矩阵
```

---

## 🤝 贡献 | Contributing

有新技能想加入合集？欢迎提 Issue 或 PR！

Want to add a new skill? Feel free to open an Issue or PR.

---

## 📄 许可 | License

MIT
