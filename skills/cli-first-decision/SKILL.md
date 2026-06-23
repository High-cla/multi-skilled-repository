---
name: cli-first-decision
description: Use before any tool call or task() dispatch to decide the right approach — built-in tool, CLI tool, skill, MCP, or sub-agent. Triggers include: any operation where you need to pick between direct tools, CLI utilities, skills, MCP servers, or delegating to a sub-agent. Use whenever the approach is not immediately obvious.
---

# CLI-First Decision

## Core Rule

**需要工具调用时，按优先级决策：触发 → 推理 → 内置工具 → CLI 工具 → 技能 → MCP → 子智能体 → 自行推理**

1. **触发**: 接收任务请求，识别类型（修复/实现/调研/评估/开放式），明确用户意图。
2. **推理优先**: 先思考问题本质——明确需求、拆解步骤、判断范围。不要急着摸工具。
2. **内置工具次之**: 简单读/写/搜索一步直达 → 直接用 Read/Edit/Grep/Glob 等（零额外成本）
3. **CLI 工具再次**: 批量/机械性操作 → 用对应的 CLI 工具（<1s，参考下方矩阵）
4. **技能辅助**: 需要领域专知的操作 → 先加载对应 skill 获取指导（参考可用技能列表）
5. **MCP 工具**: 知识图谱查询、顺序推理、网页抓取等 → 用 MCP server 提供的工具
6. **子智能体**: 需要多步推理、语义理解、跨模块分析 → 派子智能体（sub-agent）
7. **自行推理兜底**: 架构决策、设计权衡、审查验证 → 亲自推理或咨询 Oracle

## Decision Tree

```
收到请求（触发）
  └─ 识别类型：修复/实现/调研/评估/开放式？
       └─ 推理：先明确需求、拆解步骤、判断范围
       ├─ 简单读/写/改一个文件已知内容？───→ 内置工具 (Read/Edit/Write)
       ├─ 机械性批量操作？
       │   ├─ 批量文本替换？───────────→ git-sed / sd
       │   ├─ 文件查找？───────────────→ fd-find / glob
       │   ├─ 内容搜索？───────────────→ rg-search / grep
       │   ├─ AST 结构化操作？──────────→ ast-grep
       │   ├─ JSON/YAML/XML 查询？──────→ jq-query / yq
       │   └─ 其他机械操作？────────────→ 查下方矩阵
       ├─ 有对应领域 skill 可用？────────→ 先加载 skill 获取指导
       ├─ 有 MCP 工具可用？
       │   ├─ 知识图谱/代码关系查询？────→ codebase-memory-mcp
       │   ├─ 顺序推理/复杂分析？───────→ sequential-thinking
       │   └─ 网页内容获取？───────────→ fetch
       ├─ 需要语义理解/多步推理/跨模块？──→ 子智能体 (task/sub-agent)
       └─ 架构决策/设计权衡/审查？──────→ 自行推理或咨询 Oracle
```

## Tool Decision Matrix

| 层级 | 场景 | 首选工具 | 耗时代价 |
|------|------|---------|---------|
| **触发** | 接收请求、识别类型、明确意图 | Intent Gate 分类 | 即时 |
| **推理** | 任务分析、需求拆解、步骤规划 | 先思考，后选工具 | 即时 |
| **内置** | 简单文件读/写/编辑 | Read / Edit / Write | 即时 |
| **内置** | 基础内容搜索 | `grep` | <1s |
| **内置** | 文件模式匹配 | `glob` | <1s |
| CLI | 批量文本替换（正则） | `git-sed` | <1s |
| CLI | 文件查找（按名称/类型/时间） | `fd-find` | <1s |
| CLI | 内容搜索+统计 | `rg-search` (ripgrep) | <1s |
| CLI | AST 代码搜索/替换（25 语言） | `ast-grep` | <1s |
| CLI | JSON 查询/转换 | `jq-query` | <1s |
| CLI | HTTP API 测试 | `git-curl` | <1s |
| CLI | 模糊过滤/缩小列表 | `fzf-filter` | <1s |
| CLI | 打包/解压 | `git-tar` | <1s |
| CLI | 换行符转换（CRLF/LF） | `git-dos2unix` | <1s |
| CLI | 文本查找替换（更简单语法） | `sd` | <1s |
| CLI | 代码统计（语言分布） | `tokei` | <1s |
| CLI | XML/YAML/JSON 查询 | `yq` / `xq` | <1s |
| **技能** | 领域专知操作（量化/前端/云等） | 加载对应 skill 获取指导 | 见 skill 文档 |
| **MCP** | 知识图谱/代码关系查询 | `codebase-memory-mcp` | <5s |
| **MCP** | 顺序推理/多步分析 | `sequential-thinking` | 视步骤 |
| **MCP** | 网页内容获取 | `fetch` | <10s |
| **子智能体** | 多步推理、语义理解、跨模块分析 | `task()` 派子智能体 | 数十秒+ |
| **自行推理** | 架构决策、设计权衡、审查验证 | 亲自处理或 Oracle | 视复杂度 |

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

## When to Use Sub-Agents (Sub-Agent Trigger Guide)

Sub-agents excel where CLI tools and built-in tools fall short:

| 场景 | 说明 | 推荐方式 |
|------|------|---------|
| **语义理解** | 判断代码逻辑是否正确、功能是否完整 | `task()` 派子智能体 |
| **跨模块集成** | 多个模块的协调变更、接口对齐 | `task()` 派子智能体 |
| **多步操作** | 需要先搜索→分析→再修改的连锁操作 | `task()` 派子智能体 |
| **代码生成/重构** | 需要理解现有代码结构后生成新代码 | 子智能体或自行推理 |
| **架构决策** | 设计方案选择、权衡分析 | 自行推理或 Oracle |
| **验证与审查** | 理解代码意图、做质量判断 | 自行推理或 review-work |

> **注意**: 即使最终决定用子智能体，在 task() prompt 中也可以引用 CLI 工具——子智能体内部同样可以调用这些工具完成任务。

## Common Mistakes

1. **跳过 CLI 检查直接 task()**：习惯性派子代理做批量替换，浪费数万 token。30s 的代理工作可能 <1s 的 CLI 命令就能完成。

2. **用 ripgrep 找到文件后手动修改**：先 rg 搜索定位，再用 CLI 批量编辑要两步合一步。用 `git-sed` 一条命令完成搜索+替换。

3. **在单个文件上调用代理**：修改一个文件中的已知内容直接编辑即可，不需要启动完整的子代理会话。

4. **该用子智能体时却用 CLI 工具硬扛**：CLI 工具不懂语义。涉及跨模块分析、多步推理、理解代码意图的场景，用 CLI 组合拳不如一个子智能体高效。示例：需要"找到所有调用了 X 函数的文件，分析其参数模式，然后统一重构"——这是子智能体的领域，不是 sed 能搞定的。

5. **sd 默认原地编辑，先 `--preview` 再执行**：sd 和 sed 表现不同——sd 默认直接修改文件。实测 `sd '<?xml' '<?XML' filelist.xml` 直接改写了所有 `<?xml` 标签（63处），只能 `git checkout` 恢复。**安全步骤**: 先用 `sd --preview 'find' 'replace' file` 查看影响范围，确认无误后再执行（不加 `--preview`）。

6. **yq XML 模式 yq v3 用 `--xml`，v4 换成 `-p xml`**：yq v4 移除了 `--xml` 短参数，改用 `-p xml`。默认输出格式警告可通过 `-o yaml` 抑制。
