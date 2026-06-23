---
name: cli-first-decision
description: Use before any task() dispatch to check whether a CLI tool can solve the problem faster than a sub-agent. Triggers include: batch text replacements, file name searches, content searches with regex, fuzzy filtering of text output, or any mechanical/repetitive operation across many files. Do NOT use when the task requires semantic understanding, cross-module integration, or architectural decisions.
---

# CLI-First Decision

## Core Rule

**每次 task() 前，先问：有没有现成的 CLI 工具能更快解决？**

Simple mechanical work -> CLI tools (sub-second). Complex reasoning -> agents (tens of seconds + thousands of tokens). Always check CLI first.

## Decision Matrix

| 场景 | 首选工具 | 耗时代价 |
|------|---------|---------|
| 批量文本替换（正则） | `git-sed` | <1s |
| 文件查找（按名称/类型/时间） | `fd-find` | <1s |
| 内容搜索+统计 | `rg-search` (ripgrep) | <1s |
| AST 代码搜索/替换（25 语言） | `ast-grep` | <1s |
| JSON 查询/转换 | `jq-query` | <1s |
| HTTP API 测试 | `git-curl` | <1s |
| 模糊过滤/缩小列表 | `fzf-filter` | <1s |
| 打包/解压 | `git-tar` | <1s |
| 换行符转换（CRLF/LF） | `git-dos2unix` | <1s |
| 基础内容搜索 | `grep`（内置） | <1s |
| 文件模式匹配 | `glob`（内置） | <1s |
| 文本查找替换（更简单语法） | `sd` | <1s |
| 代码统计（语言分布） | `tokei` | <1s |
| XML/YAML/JSON 查询 | `yq` / `xq` | <1s |
| ✅ 需要理解语义/做决策 | 代理 | 数十秒+ |

## Quick Tool Reference

| 工具 | 典型命令 | 用途 |
|------|---------|------|
| `git-sed` | `git-sed expression:"s/old/new/g" files:["src/**/*.ts"] inPlace:""` | 批量正则替换，跨文件编辑 |
| `fd-find` | `fd-find pattern:"*.xml" extension:"xml" path:"./Characters"` | 按名称/类型/大小/时间查找文件 |
| `rg-search` | `rg-search pattern:"somePattern" glob:"*.xml" context:2` | 文件内容搜索，PCRE2 正则，上下文行 |
| `ast-grep` | `ast_grep_search pattern:"if($$$) { $$$ }" lang:"ts"` / `ast_grep_replace pattern:"console.log($MSG)" rewrite:"logger.info($MSG)" lang:"ts"` | AST 结构搜索/替换，理解代码语法树 |
| `jq-query` | `jq-query filter:".name" file:"data.json"` | JSON 数据查询、过滤、转换 |
| `git-curl` | `git-curl url:"https://api.example.com" method:"POST" data:'{"key":"val"}'` | HTTP API 请求，支持各种方法和自定义头 |
| `fzf-filter` | `fzf-filter pattern:"keyword" input:$lines` | 模糊过滤文本行，缩小列表 |
| `git-tar` | `git-tar action:"create" archive:"out.tar.gz" files:["src/"] compression:"gzip"` | 创建/解压 tar/zip 归档 |
| `git-dos2unix` | `git-dos2unix file:"script.sh" mode:"dos2unix"` | 转换 CRLF ↔ LF 换行符 |
| `grep` | `grep pattern:"somePattern" include:"*.xml" output_mode:"files_with_matches"` | 基础内容搜索（内置） |
| `glob` | `glob pattern:"**/*.xml"` | 文件模式匹配（内置） |
| `sd` | `sd find:"old" replace:"new" files:["file.txt"]` | 更简单的 find-replace，默认原地编辑，支持正则和字面量模式 |
| `tokei` | `tokei path:"./"` | 按语言统计代码行数、注释、空白行。秒级出结果 |
| `yq` | `yq expression:".Missions.NestMission[]" file:"Missions.xml" xml:true` | YAML/XML/JSON 结构化数据查询。XML 模式可直查 XML 文件（如列出所有任务 ID） |

## When NOT to Use CLI

CLI tools excel at mechanical operations but fail at:

- **语义理解**: 判断代码逻辑是否正确、功能是否完整
- **跨模块集成**: 多个模块的协调变更、接口对齐
- **架构决策**: 设计方案选择、权衡分析
- **验证与审查**: 理解代码意图、做质量判断

遇到这些场景 -> 使用代理（sub-agent）或自行推理。

## Common Mistakes

1. **跳过 CLI 检查直接 task()**：习惯性派子代理做批量替换，浪费数万 token。30s 的代理工作可能 <1s 的 CLI 命令就能完成。

2. **用 ripgrep 找到文件后手动修改**：先 rg 搜索定位，再用 CLI 批量编辑要两步合一步。用 `git-sed` 一条命令完成搜索+替换。

3. **在单个文件上调用代理**：修改一个文件中的已知内容直接编辑即可，不需要启动完整的子代理会话。

4. **sd 默认原地编辑，先 `--preview` 再执行**：sd 和 sed 表现不同——sd 默认直接修改文件。实测 `sd '<?xml' '<?XML' filelist.xml` 直接改写了所有 `<?xml` 标签（63处），只能 `git checkout` 恢复。**安全步骤**: 先用 `sd --preview 'find' 'replace' file` 查看影响范围，确认无误后再执行（不加 `--preview`）。

5. **yq XML 模式 yq v3 用 `--xml`，v4 换成 `-p xml`**：yq v4 移除了 `--xml` 短参数，改用 `-p xml`。默认输出格式警告可通过 `-o yaml` 抑制。
