# 上游项目、官方手册与工程依据

本索引集中记录 CLI-First Decision 所涉及工具、运行时和工程原则的一手资料。它不是“安装清单”：**是否可用、实际参数和真实行为，以当前机器/会话的版本、二进制帮助、MCP schema 和项目锁定版本为准**。

## 1. 资料使用规则

1. **先确定实际版本**：检查 `command -v <tool>`、`<tool> --version`、项目 lockfile/package manifest、MCP server version 和部署 commit。
2. **使用版本匹配的资料**：优先当前已安装版本对应的 release/tag/manual。主分支文档可能描述未发布行为；不能直接套用。
3. **规范和官方手册优先**：语言/协议规范、项目官方仓库、官方 API 手册和 release notes 优先于博客、搜索摘要和第三方教程。
4. **schema 优先于记忆**：MCP 工具以当前宿主实际注册的 input schema 为准；PTC 以当前注入的 `tools:sdk` 和 DSH 对应版本为准。
5. **帮助文本优先于旧命令示例**：参数存在版本差异时，执行本机 `--help` 或 `man`，并做最小无副作用验证。
6. **记录不确定性**：项目仓库 main、release tag、已安装构建不一致时，记录各自 commit/version；不把未经验证的参数写成稳定契约。
7. **没有权威资料就明说**：不能把名称相似的其他工具文档当作来源，也不能推断本机 PATH alias 的实现来源。

## 2. DSH / DeepSeek Harness：PTC、工具 SDK 与执行管线

### 官方项目与源码入口

- [DeepSeek Harness 源码仓库](https://github.com/deepseek-ai/deepseek-harness) — DSH 项目本体；检查实际安装构建对应的 tag/commit。
- [包目录总览](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/README.md) — 包职责和目录导航。
- [工具注册/执行管线：`@deepseek-ai/dsh-tools` 中文 README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/tools/README.zh.md) · [English](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/tools/README.md) — native/PTC presentation、工具 schema、策略、调用生命周期、取消和并发安全约定。
- [官方工具目录（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/tool-catalog.zh.md) — 当前工具名称、参数 schema、说明和源码归属；包含 `run_code` 的真实输入定义。
- [PTC executor package 文档（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/tool-executor-ptc/README.zh.md) · [English](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/tool-executor-ptc/README.md) — PTC schema、SDK 呈现、子调用调度、并发上限、输出与已知限制。
- [PTC SDK 生成入口](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/tools/src/ptc.ts) · [TypeScript 类型 renderer](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/tools/src/ts-types.ts) · [Python 类型 renderer](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/core/tools/src/py-types.ts) — 从源码核实生成语言和类型投影。
- [PTC runtime 抽象契约（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/ptc-runtime/ptc-runtime/README.zh.md) · [English](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/ptc-runtime/ptc-runtime/README.md) — runtime language、request/result、sandbox descriptor 和 provider 边界。
- [官方 Node PTC runtime 文档（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/ptc-runtime/ptc-runtime-node/README.zh.md) · [English](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/ptc-runtime/ptc-runtime-node/README.md) — 当前 Node provider 的执行模式、沙箱后端、超时、输出和 V8 heap 限制。
- [实验性 Python PTC runtime](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/experimental/ptc-runtime-python) · [中文 README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/experimental/ptc-runtime-python/README.zh.md) — Python provider；当前为显式组合的实验包，没有已发布 profile 默认启用，且文件隔离能力不同于已发布 Node provider。
- [模块依赖图](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/module-graph.md) — 核验当前 PTC runtime、Node provider、sandbox 和 executor 的真实包边界。
- [并行工具调用实现说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/feature/2026-07-10-parallel-tool-call-execution.md) — 并发调度的实现背景；以当前代码/schema 为最终准据。
- [PTC Runtime 开发者文档](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/ptc-runtime) — runtime request/result、provider、sandbox facts 和错误分类。
- [工具目录在线文档](https://deepseek-harness.github.io/deepseek-harness/en/reference/tool-catalog) — 发布文档入口；版本敏感细节应回到已安装 commit 的仓库源码。

### 已从当前官方工具文档核实的 PTC 契约

- PTC 模式对模型公开 `run_code` 入口和由当前运行时语言生成的 SDK；其它工具通过程序内的 `tools.<name>(args)` 绑定访问。**不要绕开 PTC 调用模式，直接假设每个 MCP 工具都能作为模型顶层工具调用。**
- 当前工具目录中 TypeScript `run_code` schema 的必填字段是 `code` 与 `description`；程序体是异步 TypeScript 函数体，支持顶层 `await` / `return`，只允许可擦除类型语法。运行时/schema 变更时以注入说明为准。
- SDK 语言取决于加载的 `ctx.ptcRuntime.language` 和已注册 renderer。`dsh-tools` 当前包含 TypeScript 与 Python SDK renderer；已发布 Node provider 执行 TypeScript，Python provider 位于实验性 package，需显式组合。PTC presentation 按 Agent 统一，不能在同一 Agent 内假设不同工具分别使用 Native/PTC；不能把某次会话的 TS 声明当成所有 PTC preset 的永久约定。
- 当前 `@deepseek-ai/dsh-tool-executor-ptc` 文档给出的 `maxParallelSubCalls` 默认值为 10；设为 1 可串行执行，必须为正整数。根 `run_code` 调用本身是 exclusive；该值限制每个程序内部并行安全的嵌套调用数。它是该 DSH 版本的配置默认值，不应硬编码成所有运行时的固定上限。
- `Promise.all` 只表达程序端的并发意图。工具定义的参数敏感 parallel/exclusive 分类和执行 scheduler 决定是否真正重叠；未知工具 fail-closed 为 exclusive。连续 parallel calls 可组成有界 pool，exclusive 调用形成单独屏障；不支持按兄弟调用之间资源冲突作关系型判断，因此可能冲突的写入应串行化。工具主体必须遵守 `exec.signal` 合作式取消；中止后等待已启动工作清理，但不会撤销已经完成的副作用。
- PTC 中间绑定结果只存在于执行局部，不进入 Session 历史/回放；官方 PTC executor 文档明确指出这些值没有字节数上限，可能耗尽进程/worker 内存。外层 `run_code` 的返回值/log 才受 provider 输出预算约束。`maxMessageBytes` 是 Node provider 控制消息、未完成 binding 参数字节与排队控制写入的限制，不能误读为中间工具返回对象图的总内存上限。只取需要字段、分块/流式处理并及时释放大结果。
- 当前 Node runtime 的 `timeoutMs` 默认 120,000 ms、上限 600,000 ms，并纳入嵌套工具与审批等待；它是经过时间 deadline，不是 CPU 时间计量。
- 当前 Node provider README 还列出 `executionMode: per-call`（默认，每次新 Node 进程）、可选 `persistent-in-memory`（每个 Agent 保留受限 REPL）、`maxOldGenerationSizeMb: 512`、`maxOutputBytes: 64 MiB`、`maxMessageBytes: 128 MiB` 等配置默认值。这些都是该 provider 版本的配置，不能当作 PTC SDK 的通用内存上限；尤其中间对象仍应主动限量。
- 请求更宽的 `sandbox_permissions` 时需要 `justification` 和审批。要检查 provider 实际报告的 sandbox enforcement/facts；不能把 `isolation` 一词当成 OS 级安全保证，也不能把 sandbox policy 扩权理解为永久授权。
- 子调用失败按真实错误对象处理（例如 `ToolCallError` 的 `toolName`）；外层程序异常与工具调用异常需要区分。执行失败不自动回滚此前副作用，不自动重放非幂等调用；重试前核对实际状态。

**运行原则**：当前会话注入的 `tools:sdk` / tool schema > 安装版本对应的 DSH 官方文档与源码 > 本文摘要 > 模型记忆。开发预览版本可能存在 breaking changes；更新 DSH 后重新核验。

## 3. FastCtx：本地仓库 MCP 与 Bash 工具

### 官方项目与版本

- [FastCtx 官方仓库](https://github.com/yc-duan/fastctx)
- [FastCtx v0.2.6 中文 README](https://github.com/yc-duan/fastctx/blob/v0.2.6/README.zh-CN.md) — 与该 release tag 配套的 MCP 工具文档。
- [FastCtx README（main）](https://github.com/yc-duan/fastctx/blob/main/README.md) — 当前重构分支说明；截至 2026-11-03，main 指向尚未稳定发布的 v1.0.1 beta 重构，不是 v0.2.6 MCP server 的兼容说明。
- [FastCtx Releases](https://github.com/yc-duan/fastctx/releases) — 区分正式 release 与 pre-release。
- [FastCtx v0.2.6 Release](https://github.com/yc-duan/fastctx/releases/tag/v0.2.6) — 截至 2026-11-03 最新稳定正式发布版（2026-08-23）。
- [FastCtx v1.0.1-beta.13 Release](https://github.com/yc-duan/fastctx/releases/tag/v1.0.1-beta.13) — 2026-10-31 发布的预览版；release 标记为 pre-release，README 明确说明新重构尚未正式发布。只有本机确实运行该 beta 时才按 beta 源码/帮助文档判断。
- [v0.2.6 工具 schema 源码](https://github.com/yc-duan/fastctx/blob/v0.2.6/src/tool_schema.rs) · [glob](https://github.com/yc-duan/fastctx/blob/v0.2.6/src/glob_tool.rs) · [grep](https://github.com/yc-duan/fastctx/blob/v0.2.6/src/grep_tool.rs) · [replace](https://github.com/yc-duan/fastctx/blob/v0.2.6/src/edit/replace.rs)
- [v0.2.6 批量读取](https://github.com/yc-duan/fastctx/blob/v0.2.6/src/read_tool/batch.rs) · [MCP server](https://github.com/yc-duan/fastctx/blob/v0.2.6/src/server.rs) · [Bash server](https://github.com/yc-duan/fastctx/blob/v0.2.6/src/shell_server.rs) · [完整源码树](https://github.com/yc-duan/fastctx/tree/v0.2.6)

版本边界：截至 2026-11-03，正式稳定发布仍是 `v0.2.6`；GitHub 最新预览 `v1.0.1-beta.13` 是全新重构且标记为 pre-release。新 beta README 明确声明重构分支尚未正式发布，不能把 v1 beta 的 World/Hands 架构文档套作 v0.2.6 的 MCP 工具契约。当前已安装版本由 `fastctx --version` 和实际二进制来源决定。

当前文档核验时，v0.2.6 README 明确改变了 `glob` 的 ignore 行为：`glob` 默认只尊重普通 `.ignore`，不自动套用 `.gitignore`、`.git/info/exclude` 或 global Git ignore，也不自动隐藏 `.git`；需要排除的目录应显式传负 pattern。**不要把 main 分支文档无条件当作所有已安装版本的契约。**

### MCP 工具和安全边界

FastCtx 官方 README 当前列出九个同级 MCP 工具：

| 工具 | 官方定义的职责 |
|---|---|
| `inspect_local_file` | 读取受支持文件；支持批量文本读取与分页 |
| `grep` | 搜索单文件或目录树的内容 |
| `glob` | 按路径模式发现文件 |
| `replace` | 机械批量替换；支持 dry-run、候选集冻结和并发变更保护 |
| `run` | 前台执行 Bash |
| `run_background` | 启动后台 Bash 任务 |
| `job_output` | 查看后台任务状态/新增输出 |
| `job_kill` | 终止后台任务进程树 |
| `job_list` | 找回运行中或已保留的任务 |

适用边界：

- `inspect_local_file` 批量文本读取支持 1–32 个文件；`grep`/`glob` 自动并行默认按 OS 可用并行度工作、最高 16；这是 FastCtx v0.2.6 搜索请求的有效并行度，不是 CPU affinity 或整机 governor。
- v0.2.6 `replace` 默认最大输入/替换结果文件大小 256 MiB，可配置为 64 MiB–4 GiB；提高上限会增加内存耗尽风险。
- `run` 使用有界内存缓冲，超出输出预算会截断；大日志应重定向到文件再分页读取。
- `run_background` 没有运行超时，由独立监督进程管理；任务输出/状态保存在用户私有目录，server/session 退出后仍可用 job id 查询。需要自行设置停止和存储配额策略。
- 文件工具默认发布；Bash/job 工具是否可见取决于 FastCtx 的 Bash terminal 设置及宿主配置，不能假设每台机器都已启用。
- 官方 README 说明 FastCtx server 继承宿主进程本地权限。MCP server 的文件权限边界不应被误认为宿主应用自身 sandbox 的边界。
- `replace` 的 dry-run、候选集冻结、原子替换、CAS 校验、编码/BOM/行尾保留等语义，以已安装版本的 schema/实现为准。
- `run` 在 Windows 使用 Git Bash；POSIX shell 写法仍要考虑 Git Bash/MSYS 路径参数转换。
- 后台任务可跨 FastCtx server/session 留存；使用返回的 job id 查询状态，不能假设前台调用结束就终止后台进程。

## 4. Context7 文档检索

Context7 是库/框架文档检索索引，不是 CLI 运行依赖，也不能替代官方原始文档。

### 使用流程

Context7 是可选的文档检索工具，**不是 DSH 本地运行时依赖，也不需要为运行 FastCtx 而安装**。当前会话若确实提供 Context7 工具，检索第三方库/框架时优先使用它。

1. 仅当当前会话工具列表实际提供 Context7 时才调用；先用 `resolve_library_id` 搜索准确项目名和查询主题。
2. 根据名称匹配、来源声誉、文档覆盖、相关性选择 library ID；用户指定版本或项目锁定版本时，优先选择对应版本 ID。
3. 再用 `query_docs` 检索一个明确主题；跨主题分开查询。不得跳过 resolve 步骤，也不得猜 ID。
4. 阅读返回的来源 URL 和适用版本，打开官方手册/仓库原文核验关键 API、默认值、限制和弃用状态；如果 Context7 结果与锁定版本不符，以锁定版本的一手资料为准。
5. 将 Context7 用于快速发现相关段落、用法和可能遗漏的选项；性能/安全/兼容性关键结论至少回到项目官方文档、规范或源码验证。
6. Context7 不可用、未索引项目或缺少目标版本时，直接搜索并打开官方文档/仓库。不要因此假装 Context7 已查询，也不要要求用户安装插件才能继续。

本次已实际检索的示例 ID（仅供识别，不作为永久 ID 保证）：

- jq：`/jqlang/jq` — 官方 jq 手册/项目索引。
- ripgrep：`/burntsushi/ripgrep` — 上游源码与指南。
- GNU Bash：`/websites/gnu_software_bash_manual_html_node` — GNU Bash 手册索引。

本次 Context7 交叉核实的具体行为：jq `--slurp` 会把所有输入读入内存；jq 1.5+ 可使用 `inputs` 逐实体处理，`--stream` 可处理超大 JSON 但 filter 更复杂且可能较慢；ripgrep 默认忽略 `.gitignore`/`.ignore`/`.rgignore`（优先级 `.rgignore` > `.ignore` > `.gitignore`）、隐藏/二进制文件并不跟随 symlink；Bash pipeline 默认退出码是最后一个命令的退出码，启用 `set -o pipefail` 后才会传播最右侧失败状态。实际行为仍应按本机版本复核。

## 5. Shell、POSIX 与 Windows Git Bash

- [GNU Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html) — Bash 自身语法、扩展、参数展开、重定向和执行语义；Bash 不等于纯 POSIX `sh`。
- [POSIX.1-2024 / The Open Group Base Specifications Issue 8](https://pubs.opengroup.org/onlinepubs/9799919799/) — POSIX Shell Command Language 与标准工具的可移植基线。
- [Git for Windows Technical Overview](https://gitforwindows.org/technical-overview.html) — Git for Windows 使用 MSYS2 子集并提供 Git Bash。
- [Git for Windows](https://gitforwindows.org/) — 官方安装、组件与环境入口。
- [MSYS2 Filesystem Paths](https://www.msys2.org/docs/filesystem-paths/) — Unix/Windows 路径转换、argv/environment 自动转换和 `cygpath`；跨原生 Windows 程序边界时必须注意。
- [MSYS2 Overview](https://www.msys2.org/wiki/MSYS2-introduction/) — MSYS POSIX 兼容层与 MinGW 原生 Windows 二进制的差别。

在 DSH/FastCtx 里写 Bash 时，需分别核对：调用端 shell、FastCtx 版本、Git Bash/MSYS 版本、目标 CLI 的原生/ MSYS 构建类型。路径转换行为不能只凭字符串外观推断。

## 6. 命令行工具的官方手册/项目仓库

| 工具 | 权威文档 / 上游项目 | 使用时特别核验 |
|---|---|---|
| `sg` / ast-grep | [CLI Reference](https://ast-grep.github.io/reference/cli) · [源码仓库](https://github.com/ast-grep/ast-grep) | `sg --help`、语言 parser、配置发现、rewrite/test 子命令；结构搜索不要退化成宽泛正则 |
| `rg` / ripgrep | [User Guide](https://ripgrep.dev/docs/guide/) · [源码仓库](https://github.com/BurntSushi/ripgrep) | ignore 规则、隐藏文件、symlink、glob、编码、`-z` 和预处理行为 |
| `fd` | [源码与手册](https://github.com/sharkdp/fd) | `fd --help`、ignore/filter 选项、NUL 输出与路径边界 |
| `sd` | [源码与用法](https://github.com/chmln/sd) | 正则语法、stdin/文件行为、in-place/预览方式；不要把它用于 AST 改写 |
| `jq` | [jq 1.8 Manual](https://jqlang.org/manual/) | 安装版本手册；注意 `--slurp` 会把全部输入收集成数组，可能显著增加内存 |
| `yq` | [Mike Farah yq 文档](https://mikefarah.gitbook.io/yq) · [源码仓库](https://github.com/mikefarah/yq) | 区分 Mike Farah yq 与 Python/kislyuk 等同名工具；版本、表达式和输入格式 |
| `curl` | [curl Documentation](https://curl.se/docs/) · [Everything curl](https://everything.curl.dev/) | HTTP status、重定向、超时、TLS、代理、退出码和响应体；`-f`/重试行为要按需求选择 |
| `zstd` | [CLI README](https://github.com/facebook/zstd/blob/dev/programs/README.md) · [zstd manual](https://facebook.github.io/zstd/zstd_manual.html) · [源码仓库](https://github.com/facebook/zstd) | 压缩格式/参数/多线程与解压内存；流式场景使用 `-d -c` |
| `duckdb` | [CLI Overview](https://duckdb.org/docs/current/clients/cli/overview) · [源码仓库](https://github.com/duckdb/duckdb) | CLI 与 SQL 引擎版本；输入读法、外部文件扫描、内存预算和临时目录 |
| `difft` / Difftastic | [Difftastic Manual](https://difftastic.wilfred.me.uk/) · [源码仓库](https://github.com/Wilfred/difftastic) | 语法 parser 支持范围和配置；结构化 diff 是审阅辅助，不替代测试 |
| `delta` | [Delta Manual](https://dandavison.github.io/delta/) · [源码仓库](https://github.com/dandavison/delta) | 它是 Git diff 的展示/pager 工具，不改变 diff 语义，也不负责证明变更正确 |
| `just` | [Just Programmer's Manual](https://just.systems/man/en/) · [源码仓库](https://github.com/casey/just) | 查当前项目 `justfile`、recipe 参数和 dotenv/shell 设置；不能假定仓库已有 recipe |
| `fzf` | [官方源码与 README](https://github.com/junegunn/fzf) | 交互式 TTY 行为；脚本无 TTY 时使用 `--filter` 或其他非交互路径 |
| `bat` | [官方源码与 README](https://github.com/sharkdp/bat) | pager/theme/config 与非 TTY 输出；程序处理优先原始文件读取，不解析彩色展示 |
| `tokei` | [官方源码与 README](https://github.com/XAMPPRocky/tokei) | 语言检测、ignore 行为和统计口径；行数不是性能/质量指标 |
| `mcp2cli` | [官方 Usage Guide](https://mcp2cli.dev/docs/usage-guide/) · [官方源码](https://github.com/mcp2cli/source-code) | 动态发现的 MCP tools/resources/prompts、schema、transport/config；只用已配置的 server，不能臆造 bake 名称 |

### 非标准 Git 辅助命令

`git-tar`、`git-dos2unix`、`git-which` 不是 Git 核心子命令的通用标准接口。它们可能是本机安装包、Git-for-Windows 附加组件、个人 wrapper 或 PATH shim 提供的可执行程序。

- 使用前先运行 `command -v <name>`，再读取其 `--help`、版本、真实路径和包管理器归属。
- 不把某台机器上的行为写成其他 DSH/FastCtx 环境的普遍事实。
- 未能追溯来源时，退回通用 POSIX/Git 工具并标注差异。

## 7. 编程规则、性能分析与工程原则的原始依据

这些原则大多是工程启发式，不是强制标准。链接用于查看原始作者/规范/工具的定义；项目仍需结合实际约束做判断。

- [The Pragmatic Programmer — 20th Anniversary Edition](https://books.pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/) — DRY、正交性、可逆性、资源管理、调试、算法速度等工程实践。
- [DRY chapter excerpt by Dave Thomas & Andy Hunt](https://media.pragprog.com/titles/tpp20/dry.pdf) — DRY 原始语义是避免重复表达同一知识，不是消灭所有相似代码。
- [Richard Gabriel — Worse Is Better](https://www.dreamsongs.com/WorseIsBetter.html) — 该设计理念的作者原文。
- [John Gall — Systemantics](https://books.google.com/books/about/Systemantics.html?id=WnJQAAAAMAAJ) — Gall's Law 的原始著作来源；法律式表述属于经验观察。
- [Gene Amdahl, 1967 paper](https://doi.org/10.1145/1465482.1465560) — 并行化总收益受到串行部分限制的原始论文。
- [Google Benchmark User Guide](https://github.com/google/benchmark/blob/main/docs/user_guide.md) — 重复测量、复杂度、统计和自定义内存测量接口。
- [Node.js Performance Measurement APIs](https://nodejs.org/api/perf_hooks.html) — Node `perf_hooks`、PerformanceObserver、mark/measure 等 API。
- [Node.js CLI profiling options](https://nodejs.org/api/cli.html) — `--cpu-prof`、`--heap-prof`、`--max-old-space-size` 等运行时诊断/资源参数；以当前 Node 版本为准。
- [Linux perf record manual](https://man7.org/linux/man-pages/man1/perf-record.1.html) — Linux 硬件/软件性能事件采样和 profile。
- [Python tracemalloc](https://docs.python.org/3/library/tracemalloc.html) — Python 分配跟踪；仅用于 Python runtime。
- [C4 Model](https://c4model.com/)、[AWS ADR process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html) — 架构图和决策记录；详见 [ARCHITECTURE-DESIGN.md](ARCHITECTURE-DESIGN.md)。

## 8. 最终核验清单

- [ ] 已确认机器/会话实际可见的工具名称和 schema。
- [ ] 已确认 CLI binary/version/path，而不是只依据 PATH alias 名称。
- [ ] 文档版本与已安装工具版本匹配。
- [ ] DSH PTC 使用当前生成 SDK；未硬编码旧工具名、语言或并发上限。
- [ ] FastCtx 版本与 README/release tag 对齐；尤其复核 glob/replace/shell 行为。
- [ ] 所有需要非交互执行的命令都在无 TTY 条件下验证。
- [ ] 对性能/内存敏感路径用 profiler/benchmark 证据，而不是宣传数字或主观感觉。
