---
name: cli-first-decision
description: "多步骤任务的工具选择、CLI 与 MCP 编排、官方文档检索、Agent Skill 发现/验证、批量处理、代码搜索、调用链分析、API 调试、并行执行和安全写入。触发词：CLI 优先、gh、GitHub、Context7、ctx7、官方文档、skills、SKILL.md、工具选型、并行、批量操作、代码搜索、影响面、任务委派。"
metadata:
  author: High-cla
  version: "3.10"
---

# CLI-First Decision 3.10

## 1. 目标与原则

目标：以最少的工具往返、最短的关键路径和最低的上下文/资源成本，可靠地完成用户目标；从零开始时先确定有证据支撑的最优适配架构，具体实现默认以运行速度和峰值内存优先。

- 先判断任务，再选择工具；不为使用 CLI 而使用 CLI。
- 本地文件操作优先 FastCtx；终端组合与批处理优先 CLI。
- 结构匹配优先 ast-grep；符号关系优先 codebase-memory。
- 先复用项目原生 API，再考虑额外 wrapper。
- 无依赖操作同轮并行；可管道合并的操作优先合并。
- 并行必须考虑调用成本、限流、上下文和写入冲突。
- 新项目、系统重建或重大架构重设计：先区分绿地与既有系统，明确质量属性和硬约束，调研官方资料、比较可行候选并验证高风险假设；既有系统的局部改动不触发全量重选架构。门禁、取舍和 ADR 见 [ARCHITECTURE-DESIGN.md](references/ARCHITECTURE-DESIGN.md)。
- 具体代码实现优先追求更短运行时间和更低峰值内存，先分析复杂度/理论下界，再用基准与剖析迭代逼近最优。
- DSH/PTC、FastCtx、CLI、库/API 的行为或参数不确定时，先确认当前版本、二进制 help 和工具 schema，再查匹配版本的上游手册/源码；Context7 用于定位资料，不代替官方核验。来源优先级和版本策略见 [AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md)。
- 写操作范围明确、修改最小、可验证、可恢复。
- 工具返回成功不等于业务成功；完成必须有证据。
- 动手前明确目标、非目标和关键假设；存在多种实质解释时说明差异，不要默默替用户做重大取舍。若不确定性会改变范围、数据语义、接口或安全边界，先澄清再执行。
- 若方案明显超出需求，主动指出更简单的替代方案；不自行增加未要求的功能、抽象、配置项或防御性复杂度。

## 2. 触发、技能优先与例外

多步骤任务、工具选型、并行/委派决策、批量操作或跨模块工作时，执行本技能的快速路由。

技能触发优先于本技能的通用建议。命中具体领域时，先加载对应技能，再按本技能选工具：

| 意图 | 先加载的技能 |
|---|---|
| 结构搜索、规则、pattern、批量代码改写 | ast-grep |
| 符号、调用链、依赖、影响面、架构 | codebase-memory |
| 工具选择、并行、调用合并、是否委派 | cli-first-decision |
| 写或改代码 | clean-code、coding-standards；非简单新功能且方案未定时先用 brainstorming；可测试行为变更用 test-driven-development；先读现有实现并明确契约/验收条件，边界、错误、资源、并发和性能规则见 [PROGRAMMING-RULES.md](references/PROGRAMMING-RULES.md) |
| Bug、复现、报错定位 | systematic-debugging |
| 写计划或执行计划 | writing-plans、executing-plans |
| 代码审查 | requesting-code-review、receiving-code-review、code-review |
| 长任务或跨会话续跑 | long-task-continuation |
| 多子智能体并行 | dispatching-parallel-agents、subagent-driven-development |
| JSON/YAML 解析 | jq-query |
| HTTP/API 调试 | git-curl |
| 文件查找/全文搜索/模糊过滤 | fd-find、rg-search、fzf-filter |
| Windows CMD/PowerShell 脚本 | cmd-powershell-pitfalls |
| DSH Agent Team 模式、preset 或 subagent 工具组合配置 | customize-dsh |

例外：一句话可直接回答、纯读取状态、已知路径的简单读取、单文件小改，不必为了形式加载本技能或额外技能。

同一会话同一技能只加载一次。跨领域任务只加载主轴必需技能，不堆叠无关技能。若运行环境没有技能加载机制，不要伪造加载成功；直接采用已知规则。

## 3. 六步决策流程

### Step 1：分类任务

| 类型 | 默认路径 |
|---|---|
| 单个已知文件读取 | FastCtx inspect_local_file |
| 多个已知文件读取 | 一次 inspect_local_file 批量传 files |
| 文件名查找 | FastCtx glob；CLI fd |
| 普通文本搜索 | FastCtx grep；CLI rg |
| 语法/代码结构搜索 | ast-grep（sg CLI） |
| 符号、引用、调用链、影响面 | codebase-memory |
| 机械式跨文件替换 | FastCtx replace；或经验证的 sd |
| 语义重写/少量局部编辑 | 内置 edit/write |
| JSON/YAML 处理 | jq / yq |
| HTTP 调试 | curl / git-curl |
| 长时间命令 | FastCtx run_background |
| 独立复杂调研/审查 | 评估收益后并行委派 |

### Step 2：检查工具真实可用性

调用前检查当前运行环境实际注册的工具名称、参数 schema、权限和返回格式。

- 只使用当前工具列表或已验证环境中存在的工具。
- 不臆造 MCP 名称、CLI 参数、agent 类型或 PTC SDK API。
- 不把其他 harness 的工具当成当前环境可用工具。
- 工具不可用时，转向已存在的等价路径；无法替代时明确报告阻塞。
- 不因工具名称熟悉就跳过 schema 检查。

### Step 3：建立依赖图

将任务表示为 DAG：

- 节点：一次工具调用或一个执行步骤。
- 边：数据依赖、状态依赖、接口依赖或写入冲突。
- 无依赖节点：可放入同一并行批次。
- 有依赖节点：按拓扑层级执行。
- 同一文件或共享状态的写入：串行化。

优先完成能够解锁最多后续步骤、且成本最低的操作。

### Step 4：选择最短工具路径

先按本节六步流程选择最短路径；只有任务分类不清、首选工具不可用或需要降级路线时，再查 [REFERENCE.md](references/REFERENCE.md) 的工具路由与 fallback。它是决策辅助索引，不是每次任务都要额外读取的步骤。

依次判断：

1. 项目是否已有原生 API/脚本可直接完成？
2. FastCtx 是否已有对应的文件或终端能力？
3. 是否可以通过一条 CLI 管道完成？
4. 问题是否要求 AST 或符号关系？
5. 是否存在真实独立且值得委派的子任务？
6. 是否能由一个内置工具调用直接完成？

路由优先级是任务相关的，不是全局固定排名。不得为了“CLI-first”增加不必要的 CLI 往返。

### Step 5：执行

- 同源、同类型批量请求优先一次调用。
- 无依赖调用同轮并行。
- 可管道组合的步骤合并为一条命令。
- 有依赖的步骤分层执行。
- 写入前明确文件集合、修改范围和冲突策略。

### Step 6：验证并结束

检查工具状态、输出完整性、实际副作用和验收条件。只报告真实执行并验证过的结果。

## 4. FastCtx 优先：本地文件与命令

本地文件读取、搜索、替换优先用 FastCtx 专用能力；需要组合过滤、转换、批处理或 stdin/stdout 管道时再用 CLI，并先确认命令真实可用且不改变数据语义。模板、PATH/别名和跨平台边界见 [CLI-TOOLS.md](references/CLI-TOOLS.md)。

| 场景 | 首选工具 | 使用规则 |
|---|---|---|
| 读取文件 | inspect_local_file | 已知路径直接读取 |
| 批量读取 | inspect_local_file | 一次传 files=[{path:...}, ...] |
| 全文搜索 | grep | 限定目录、文件类型和上下文 |
| 文件查找 | glob | 优先 glob 模式而非递归列目录 |
| 跨文件机械替换 | replace | 先 dry-run；保留编码和行尾；检测并发修改 |
| 终端命令 | run | POSIX Bash、非交互、无 TTY |
| 长任务启动 | run_background | 预计超过 run 四分钟上限时使用 |
| 后台任务状态 | job_list / job_output | 以 job_id 查询 |
| 停止后台任务 | job_kill | 先确认目标 job_id |

### 文件读取规则

- 只读任务只读取回答问题必需的文件。
- 多个文件一次 inspect_local_file 调用，除非文件依赖关系要求分阶段。
- 工具结果最后一行若为 Complete，停止续读。
- 结果为 Partial 时，只按其附带的参数原样续读，不自行推导参数。
- 文件引用即使是 URI 形状，也传等价的普通绝对路径。
- 不要把大文件全文读入上下文；先 grep 定位，再读取相关范围。

### 批量修改规则

- 机械替换用 FastCtx replace，先预览。
- 语义重写或少量局部修改使用 edit/write。
- 不逐个 Edit 完全同构的机械修改。
- 写入前检查文件是否被其他进程更改；工具支持并发保护时必须使用。
- 修改后检查 diff、命中数量和残留项。

### Shell 规则

FastCtx run 执行 POSIX Bash；Windows 上也写 Git Bash 兼容语法：

- 不写 PowerShell 语法。
- 命令必须非交互；使用 --yes、--no-edit 等等价选项。
- 编辑器和分页器默认禁用。
- 不依赖 TTY。
- 输出保持必要且有限。
- 非零退出码是需要分析的结果，不等于工具崩溃。
- 同时检查 stdout、stderr、退出码和 Complete/Partial 状态。
- 超过四分钟的命令用 run_background，之后通过 job_output/job_list 查看；不等待一个长命令占满前台调用。

推荐的安全管道：

```bash
fd -0 -e ts src | xargs -0 -r rg 'AuthService'
```

带空格或特殊字符的路径使用 NUL 分隔；避免未经转义的命令字符串拼接。

## 5. CLI 选择矩阵

CLI 在 FastCtx 的 run 中执行，不能假设所有命令已安装；必要时先做一次低成本可用性检查。

| 任务 | 首选 | 说明 |
|---|---|---|
| 文件查找 | fd | 优于递归 find |
| 文本搜索 | rg | 优于逐文件读取或普通 grep |
| 结构搜索/改写 | sg（ast-grep） | 语法结构匹配，不用正则冒充 AST |
| 批量文本替换 | sd | 仅适用于纯文本且不依赖语法结构 |
| 批量文件操作 | FastCtx replace | 保留编码/行尾并支持 dry-run/并发保护 |
| JSON | jq | 查询、过滤、聚合 |
| YAML/XML | yq | 使用已安装版本的正确输入格式参数 |
| HTTP | curl | 先检查状态码和错误体 |
| 模糊过滤 | fzf | 大结果集交互筛选；非交互时优先 --filter |
| 代码统计 | tokei；简单计数用 wc | 只在统计有助于决策时执行 |
| 结构化 diff | difft | 重构审查 |
| Git diff 展示 | delta | 仅改善可读性，不改变 diff 事实 |
| 压缩文件搜索 | rg -z / zstd -d -c | 先确认实际格式 |
| JSONL 聚合 | duckdb | 必要时先流式解压 |
| 任务编排 | just | 先读项目 justfile 或 --list |
| MCP CLI 退路 | mcp2cli @<name> | 仅限已 bake 且当前可用的 MCP；先查 help/schema |
| GitHub 仓库/Issue/PR | GitHub connector 或 gh | 当前 connector schema 优先；CLI 显式指定 --repo 并使用结构化输出 |
| GitHub Agent Skills | gh skill | 检查版本与 help；search/preview/install/publish 当前为 Preview 功能 |
| 当前库/框架文档 | Context7 connector 或 ctx7 | search 单步检索；library → docs 两步精确检索 |
| Context7 Skills | ctx7 skills | search/suggest/list；安装或移除前检查来源并取得授权 |

不要为一次简单操作引入新依赖。CLI 不存在时，选择已注册的 FastCtx 或内置工具；不要静默安装工具。

## 6. ast-grep：结构搜索与规则开发

当查询涉及代码形状、语法节点、函数调用结构、API 调用模式或批量代码重构时，优先加载并使用 ast-grep 技能，执行 sg CLI。

规则开发流程：

1. 将用户查询拆分为更小的代码匹配目标。
2. 确认语言、文件范围和目标语法节点。
3. 识别可独立测试的子规则。
4. 使用关系规则或组合规则组织子规则。
5. 用最小示例测试规则。
6. 不匹配时逐个移除子规则，定位不匹配的约束。
7. 必要时转储 AST 或模式查询，检查实际语法结构。
8. 测试正例、反例和边界情况。
9. 预览 rewrite 结果，核对命中数量和差异。
10. 验收后才执行批量修改。

规则：

- 结构问题不用正则硬改代码。
- 普通文本、日志和 Markdown 搜索使用 rg/grep，不滥用 AST。
- Windows DSH 环境运行 sg 时，按本机工具契约使用 C:/... 形式的路径。
- 搜索命中不自动代表重写安全；必须检查变更结果。

## 7. codebase-memory：符号与依赖分析

当任务涉及符号、调用链、依赖、架构或影响面时，优先加载并使用 codebase-memory 对应工具。

建议流程：

1. 定位符号及其定义。
2. 查找调用者和被调用者。
3. 查询模块依赖和关键边界。
4. 将结果转成待检查文件/符号清单。
5. 用 FastCtx、rg 或 sg 交叉验证相关源码。
6. 根据源码和测试确定真实影响面。

图谱是辅助索引，不是源码事实来源。索引可能过期或不完整；发现缺失、冲突或疑似陈旧时，以当前源码、构建配置和测试为准，并报告索引限制。

## 8. 远程仓库、官方文档与 Agent Skills

GitHub / Context7 connector 与 gh / ctx7 CLI 都是可选通道，不是所有运行环境的硬依赖。先检查当前注册工具、二进制版本、帮助文本和权限；使用已存在的最短路径，不为使用 CLI 而增加往返。

### GitHub 仓库与 CLI

- 当前会话已注册 GitHub connector 时，按实际工具 schema 读取仓库、文件、PR 和权限；本地终端存在 gh 时，标准仓库/Issue/PR 操作可用 gh。
- 使用 gh 前检查 gh --version、gh help 和 gh auth status；仓库上下文不明确时显式指定 --repo OWNER/REPO，避免依赖当前目录 remote 推断。
- 优先使用 gh 命令的 --json / --jq 获取结构化结果；列表命令显式设置 --limit，原始 API 分页使用 gh api --paginate。需要字段未暴露时再用 gh api；不要解析人类表格输出。
- 认证只检查状态和所需权限，不打印、不回显、不缓存 token；区分 token scopes、仓库角色和 GitHub App 安装权限。只请求完成任务所需的最小权限。
- 写入前确认仓库、分支、路径、当前 blob SHA、目标内容和可恢复方式。遇到权限拒绝、审批拒绝或安全校验拒绝时停止，不关闭安全校验、不换 curl/token 通道绕过；提供 diff/补丁供用户在 GitHub 网页编辑器粘贴。

### Context7 文档检索

- 当前会话提供 Context7 connector 时，先解析 library ID 再查询；只有在终端真实存在 ctx7 时才使用 CLI。connector 已经能直接完成时，不必另起 CLI。
- 单步跨库检索用 ctx7 search；针对确定的库/框架，先用 `ctx7 library <name> "<one topic>"`，再将返回的精确 `/org/project[/version]` ID 传给 `ctx7 docs`。
- 查询前从 lockfile、manifest 或用户给出的版本确定目标版本；查询主题一次聚焦一个 API/配置/行为。不要把密钥、私有代码、用户数据放进检索词。
- Context7 用于定位和提取资料，不代替上游官方文档；涉及 API 签名、默认值、安全、兼容性和弃用行为时，打开原始官方文档/源码/release note 核验。

### Agent Skills 发现与验证

- 发现技能时可使用 gh skill search / preview，或 ctx7 skills search / suggest / list；先检查 CLI 版本与 --help。gh skill 当前为 Preview，不能假定每个安装版本都支持。
- 官方技能优先从工具供应商/项目维护者的仓库读取；核对来源组织、维护状态、许可证、更新时间、SKILL.md、引用文件和脚本。搜索排名不是可信度证明。
- 安装或运行第三方技能前先 preview 并审阅全部脚本与外部调用；没有用户明确要求时不自动安装、不执行未知脚本、不授予额外权限。
- 需要查当前库/API/CLI 文档、GitHub 资源或发现第三方 Agent Skill 时，先选当前可用的 connector/CLI，再核对版本和官方来源；第三方技能先 preview 并审阅脚本、权限与外部调用，不盲目安装或执行。检索步骤和安全门见 [ONLINE-RESEARCH-AND-SKILLS.md](references/ONLINE-RESEARCH-AND-SKILLS.md)。

没有网络或权威来源不可达时，明确报告未完成在线核验；不得将模型记忆包装成当前官方文档。

## 9. 并行、管道与调用合并

### 决策表

| 依赖/冲突 | 策略 |
|---|---|
| 无依赖的只读调用 | 同轮并行 |
| 同源数据且 API 支持批量 | 一次批量调用优先于 N 次并发 |
| 能通过 stdin/stdout 串联 | 一条 CLI 管道 |
| 有数据依赖 | 分层；层内并行、层间串行 |
| 写入不同文件且无共享依赖 | 可并行 |
| 写入同一文件 | 必须串行 |
| 消费另一个任务尚未确定的接口/输出 | 先确定生产者结果，再执行消费者 |
| 多维独立审查 | 并行审查，统一汇总 |
| 共享状态或不可逆外部副作用 | 串行并加强检查 |

并行前计算实际收益：节省的关键路径时间必须大于启动、协调、限流、上下文和结果合并成本。并发数量服从工具服务限制，不设虚构的固定并发数。

### DSH 执行快捷路径

- PTC 子调用只有在当前参数被调度策略明确判定为 concurrency-safe 时才可重叠；未声明、未知或判断失败均按 exclusive 处理。`Promise.all` 只表达并发意图，不保证实际并行。
- 按当前 runtime 的 `maxParallelSubCalls` 和工具服务限额控制扇出；文档中的默认值有版本属性，执行时核对当前配置，不硬编码为通用常量。
- 需要保留部分成功结果时用 `Promise.allSettled` 或逐项 `try/catch`；聚合失败后先检查已发生的副作用，再决定恢复方式。
- FastCtx 前台命令预计超过四分钟时使用 `run_background`；通过 `job_list` / `job_output` 跟踪，确认终态和退出结果后再验收；仅对核实过的 job id 使用 `job_kill`。
- 同源 API 支持批量时优先批量；可通过 stdin/stdout 合并时优先管道。不要为了并发拆散本可一次完成的请求。
- PTC 程序内筛选、裁剪和聚合中间结果，只返回决策需要的字段；把图像和 `additionalContexts` 等可能单独转发的内容也计入上下文预算。

多阶段任务需要决定批量、并行、后台运行、委派或失败恢复时，先画依赖 DAG 和读写集合；批量优先于拆分并发，仅在独立、安全且节省的关键路径时间大于协调成本时并行。长任务管理、上下文裁剪和部分失败恢复见 [EXECUTION-EFFICIENCY.md](references/EXECUTION-EFFICIENCY.md)。

### 写入边界

派发前记录每个执行者的 Read、Write 和共享接口范围。写入集合有交集时拆开或串行化；只读任务即使读取相同文件也可并行，但应限制重复输出。

禁止：

- 两个执行者同时编辑同一文件。
- 消费尚未稳定的接口。
- 把独立的批量文本替换委派给代理。
- 为单文件小改启动子智能体。
- 为形式上的“全并行”制造额外调用。

## 10. DSH PTC：运行时入口与详细参考

仅当当前会话明确启用 PTC 且提供 run_code 与 tools:sdk 时，才使用 PTC 编排。先读取当前 runtime language、SDK 绑定、参数 schema、并发安全策略和资源限制；禁止凭记忆臆造工具名、语言或默认值。

- 简单单步调用直接使用原生工具；多步依赖、批量扇出、程序内筛选/聚合且能降低往返或上下文成本时再使用 PTC。
- 只让明确标记为 concurrency-safe 的当前参数调用重叠执行；未知/异常一律按 exclusive 串行处理。写同一资源必须串行。
- 处理部分失败时保留各分支结果；检查已发生副作用后再恢复，不能假设外层失败会回滚。
- 中间结果留在程序内，筛选/流式处理后只返回决策必需字段；图像与 additionalContexts 等可能独立转发的 payload 也计入上下文预算。
- 仅在当前会话确实启用 PTC、注入 `run_code` 与 `tools:sdk`，且多步编排/批量处理能减少往返或上下文时采用；单步任务直接调用原生工具。runtime 语言、SDK、调度、取消和部分失败语义见 [PTC-EXECUTION.md](references/PTC-EXECUTION.md)，版本依据见 [AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md)。

## 11. 计划、子智能体与 Agent Team 协作

### 非简单功能：先比较方案并确认设计

存在多个合理路径、跨模块或新用户可见行为，或影响架构、数据/API、安全、性能及兼容性的非简单功能，必须先确认设计，再写执行计划或实现。先读取相关模块、调用方、测试和约束；缺少会改变方案的需求时，先澄清。
1. **比较方案**：给出 2–3 个可行选择（含简单基线），说明收益、代价、风险、兼容/迁移影响和待验证假设，不制造伪选项。
2. **提出推荐设计**：明确目标/非目标、模块与数据流/API、失败和安全边界、性能影响、验收条件及取舍理由。
3. **取得确认**：将设计交用户审阅；确认前不写详细计划、不派发实现任务、不做生产性代码修改。用户已给出足够具体且可执行的设计时，视为确认。
4. **确认后计划**：再拆依赖 DAG、任务、读写范围和验证步骤；实现中若出现改变方案、数据语义、公共接口或安全边界的新信息，暂停并重新确认。
简单拼写/格式修正、单文件且行为明确的小改、根因和修复路径已确定的窄范围修复不触发完整比较；仍须控制范围并验证。用户只要求讨论方案时，停留在设计阶段。 

### 何时写计划与委派

多阶段、多模块、依赖复杂、高风险、长时间或跨会话任务先写可验证计划；简单任务直接执行。只有任务可拆成独立交付、上下文可交接、Read/Write 范围可分离，且节省的关键路径时间大于启动与协调成本时才委派。优先并行只读调研、正交审查和文件边界明确的实现；不要为单文件小改或紧耦合步骤组队。

### 何时启用 DSH Agent Team

- **能力边界**：Agent Team 是叠加在标准 subagent 树上的持久化共享任务板，不是另一套 teammate 运行时。标准 subagent 负责创建、发现、消息、中断和生命周期；Team 负责共享任务、依赖与归属状态。
- **启用门槛**：先确认根 Session 已在模型/推理等级菜单开启「使用智能体团队」，且当前步骤实际注册了 `team_task_create/list/get/update`、`subagent` / `subagent_fork` 和所需 subagent control 工具。标准 base 组合中新 Session 默认关闭 Team；部署 preset 可设初始默认值，但已有根 Session 保存的选择优先。不能仅凭技能被加载就假定 Team 已启用。
- **不能启用时**：技能不能替用户切换根 Session 模式。Team 工具不可见但标准 subagent 可用时，退化为无共享任务板的普通委派；连 subagent 都不可用时，按依赖顺序串行执行并说明限制。不要臆造工具或调用旧版 `spawn_teammate`、Team 专属消息/成员 API。
- **配置边界**：仅当用户要求改变 DSH profile/preset、默认 Team 模式或插件组合时，才加载 [customize-dsh](../customize-dsh/SKILL.md)；普通任务协作不改部署配置。

### Team 协作流程

1. **由 Lead 规划**：把目标拆成可独立验收的工作包（如官方资料调研、独立模块实现、测试或正交审查），先建立依赖 DAG，明确输入、交付物、验收证据、负责人和 Read/Write 范围；不要只分配模糊角色，把紧耦合或必须串行的步骤留在主流程。
2. **登记任务**：每个可分派工作项用 `team_task_create` 写入明确的 subject/description（含上下文和验收条件）；用 `blocked_by` 表示依赖，用 `write_scopes` 标注预期触及的工作区相对路径。依赖必须无环；阻塞任务未完成前不得 claim。任务板只记录/协调工作，不会自动启动 Agent。
3. **派生成员**：用标准 `subagent` 启动自包含的新上下文任务；仅当工作确实需要已完成对话历史时用 `subagent_fork`（它继承已完成轮次，不包含当前尚未完成的轮次）。使用工具返回的成员名称，并按当前 schema 核对提供方能力；一次性外部后端不能依赖后续消息来补充任务。Team 工具不负责创建成员。派发时明确原子目标、工作目录、上下文、允许/禁止修改范围、输出格式和验收条件。
4. **认领与更新**：成员先用 `team_task_list/get` 读取最新任务和 revision，再以 `team_task_update` 携带 `expected_revision` 执行 claim、release、complete 等状态变更。过期 revision 报冲突时重新读取并协调，不盲目重试；只有根 Lead 可 reassign。持久化结果不确定时先 get 核对，再决定是否重试。
5. **主动通信**：任务板状态变化不会唤醒 Agent、投递 inbox 消息或结束 `wait_agent`；需要成员行动时显式 `send_message`。发送成功只代表 inbox 接受，不代表已回复。根 Agent 在线时通常会收到直属子 Agent 完成通知；`list_agents` 用于必要的状态/身份核对，`inactive` 不等于任务已完成。不要用轮询替代通知和明确消息。
6. **逐任务双阶段审查**：实现成员交付任务说明、修改文件、diff、测试命令与真实输出、未解决问题后，Lead 才启动审查。先做**规格符合性审查**：逐项检查遗漏（Missing）、超出范围（Extra）和需求误解（Misunderstood）；通过后再做**代码质量审查**：检查正确性、边界条件、错误/资源处理、并发/安全、可维护性及测试质量。非代码任务则审查交付物的准确性、来源或证据、完整性与可复现性。审查者只读，不信任实现者自述，不自行派生审查 Agent；输入至少包含任务 brief、全局约束、diff/交付物及验证证据。两阶段均通过前，不得将任务标记为最终 completed，也不得解除下游依赖。任一阶段发现问题，明确列出可定位的 finding，交回修复；修复后运行受影响的验证，并针对 finding 与修复 diff 复审，直到通过或明确报告阻塞。Lead/独立 reviewer 均可执行审查；若没有可用 reviewer，Lead 自行完成两阶段检查，不因此跳过门禁。
7. **整体集成验收**：所有任务通过逐项审查后，Lead 再检查集成后的完整 diff、跨任务接口/文件冲突、端到端行为和全局验收条件。逐任务审查不替代最终整体审查；任务板状态也不替代代码/业务验收。

### 共享工作区与写入边界

Team 成员共享同一个 checkout；`write_scopes` 只是重叠提示，不是锁、权限边界或独立 worktree。并行写入前必须让文件集合互斥：优先一名成员负责一个文件/模块，多个成员可并行只读分析；同一文件或共享接口只能由一个写入者负责，其他修改串行合并。由 Lead 负责最终集成和回归验证。

DSH 行为以当前工具 schema 和目标版本官方资料为准：[Agent Team 子系统](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/agent-team.zh.md)、[Team service](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/team/agent-team/README.zh.md)、[Team task tools](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/team/tool-agent-team/README.zh.md)、[subagent runtime](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/subagent/README.zh.md) 与 [subagent control](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/tool-subagent-control/README.zh.md)。

### 子智能体任务契约与失败处理

每个子任务 prompt 必须包含：原子 TASK、工作目录、必要 CONTEXT、Read/Write 范围、MUST NOT、交付物、ACCEPTANCE 和 REPORT。新上下文 `subagent` 必须获得自包含信息；`subagent_fork` 也要补足当前轮次尚未进入历史的关键信息。子任务失败、超时或输出不完整时，保留已验证结果，读取任务与 Agent 状态后再决定 release、reassign、重试或主流程接手；不得仅凭成员的“完成”声明验收。

## 12. 写操作安全与恢复

| 风险 | 示例 | 要求 |
|---|---|---|
| 只读 | 搜索、读取、状态检查 | 直接执行 |
| 低风险写入 | 单文件局部修改 | 精确编辑并复核 diff |
| 批量写入 | 跨文件替换、生成文件 | dry-run、命中范围检查、验证残留 |
| 高风险写入 | 删除、覆盖、远程提交、生产操作 | 检查授权、目标、备份/回滚路径；超出用户授权时先询问 |

通用规则：

- 修改前检查 git status 和现有 diff，不覆盖用户未提交工作。
- 只改任务要求的最小范围；每一处改动都应能追溯到用户目标或验证所必需的修复，不顺手修改相邻代码、格式或文档。
- 只清理由本次修改导致的未使用 import、变量或函数；不要擅自清理既有死代码，除非用户要求。
- 批量改写保留编码、行尾和文件权限。
- 非幂等操作失败后先查状态，不盲目重跑。
- 不吞异常；区分工具故障、输入错误、权限错误、业务失败和部分成功。
- 远程写入必须验证最终远端状态。
- 任何未运行的测试都不能报告为通过。

## 13. 验证闭环

开始前先把用户目标转成可观察的成功条件；多阶段任务将每一步写成“执行步骤 → 验证证据”，不要只罗列动作。

### 可测试行为变更的 TDD 门禁

新功能、Bug 修复及可能改变可观察行为的重构，只要存在合理的自动化测试路径，就必须先测试后实现，不得事后补测试冒充 TDD。
1. **RED**：先写独立表达预期行为的测试并运行；失败必须是目标断言未满足，而非测试语法、编译/导入、环境或无关故障，否则先修正并重跑，直到获得有效 RED。
2. **GREEN**：只做让目标测试通过的最小生产改动；重新运行同一测试并确认通过，不扩展需求或顺手重构。
3. **回归与重构**：运行受影响测试及必要的类型检查、lint/build；重构后重新验证。记录实际命令、退出码和关键输出。
4. **证据**：报告 RED 原因、GREEN 结果和回归结果；未实际观察到的结果不得宣称通过。
纯文档/格式调整、无可观察行为变化的配置整理，或确实没有可执行测试路径时，不伪造 RED；说明原因并采用最接近的可验证替代（静态检查、配置解析、最小复现或人工验收）。存在可行测试路径时仍执行上述门禁。

按风险选择验证深度：

1. 范围：修改文件与命中数量正确。
2. 内容：diff 与需求一致，无意外改动。
3. 结构：AST/格式/类型检查通过。
4. 行为：相关单元测试或集成测试通过。
5. 系统：必要时运行构建或端到端检查。

失败时：

- 保留已知成功结果。
- 缩小失败范围。
- 查明根因后再重试。
- 降级工具时重新检查输出语义。
- 验证未通过时明确报告阻塞，不得宣称任务完成。

## 14. 红旗

发现以下任一情况，停止并重新选择路径：

- 已知文件仍全文扫描整个仓库。
- 多文件读取被拆成多次单文件调用。
- FastCtx 文件工具可用却用 shell 读取本地文件。
- AST 结构改写使用宽泛正则。
- 用全文搜索代替调用链/影响面分析。
- 未检查工具 schema 就调用想象中的工具。
- 把 GitHub / Context7 插件当成默认依赖。
- 无依赖且收益明确的调用被串行执行。
- 批量请求已可合并却重复往返。
- 并行执行者写入同一文件。
- 简单机械任务被委派给子智能体。
- 非幂等操作失败后盲目重试。
- 未验证就报告成功。

## 15. CLI、编程规范与工程原则

本技能负责选择工具和执行路径；实现细节按任务按需加载，避免把所有规则重复塞入主技能：

| 触发场景 | 决策层摘要：先判断什么、默认怎么选 | 深入参考 |
|---|---|---|
| 绿地项目、系统重建或重大架构重设计 | 先明确质量属性和硬约束，再做官方调研、候选比较与高风险原型；既有系统先理解现状，不因局部任务重选架构。 | [ARCHITECTURE-DESIGN.md](references/ARCHITECTURE-DESIGN.md) |
| 工具、运行时、CLI/API 行为或参数不确定 | 先看当前版本、help 和 schema；按版本匹配上游手册/源码。Context7 用于定位，不作为最终行为证据。 | [AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md) |
| 本地文件、终端命令和批处理 | 文件读写/搜索优先 FastCtx；过滤、转换、批量组合和管道再选 CLI，并核对可用性与输入输出语义。 | [CLI-TOOLS.md](references/CLI-TOOLS.md) |
| 多阶段工具任务、并行、后台运行或委派 | 先画 DAG 和读写集合；优先批量，只有独立且收益超过协调成本时并行；长任务后台化并保留部分成功结果。 | [EXECUTION-EFFICIENCY.md](references/EXECUTION-EFFICIENCY.md) |
| 当前文档检索、GitHub 操作或 Agent Skill 发现 | 按任务选 connector/CLI 和官方来源；确认版本、权限与数据边界；第三方技能先审阅来源、脚本和外部调用。 | [ONLINE-RESEARCH-AND-SKILLS.md](references/ONLINE-RESEARCH-AND-SKILLS.md) |
| 功能实现、Bug 修复、重构和代码审查 | 先理解现有实现并明确契约/验收条件；外部边界校验、错误与资源处理明确；性能优化先定 workload、基线和热点。 | [PROGRAMMING-RULES.md](references/PROGRAMMING-RULES.md) |
| 简单性、兼容性、抽象、可靠性或性能原则冲突 | 不按原则名称机械套用；先守硬约束，再按目标、调用方可观察行为、风险和测量证据权衡总成本。 | [ENGINEERING-PRINCIPLES.md](references/ENGINEERING-PRINCIPLES.md) |
| 确认当前会话启用 PTC，且任务需要多步编排 | 多步依赖、批量扇出或程序内聚合有净收益时才用；runtime/SDK 以当前注入定义为准，单步调用不强制套 PTC。 | [PTC-EXECUTION.md](references/PTC-EXECUTION.md) |
| 任务路由仍不明确，或首选工具不可用 | 查工具映射和降级路径；它是补充索引，不替代本技能六步流程，也不要求每次都读取。 | [REFERENCE.md](references/REFERENCE.md) |

执行底线：正确性、安全、数据完整性和已有 API 契约是硬约束；先理解 workload、复杂度和理论下界，再用真实基准、profile、分配与峰值内存数据优化。大数据优先流式、分块和有界队列。绿地项目先调研当前官方文档、比较至少两个可行架构并记录 ADR；既有项目先检查现状和基线。工程原则是决策启发式，不是机械打勾项；细则只在当前任务需要时读取。

按任务选择原则，不逐条背诵或机械套用：

- **绿地设计与功能扩展**：用 Gall 定律、KISS/YAGNI 和第二系统效应约束范围；先交付最小但正确、可运行的方案，再根据已验证需求演进。Worse is Better 不意味着牺牲正确性、安全或必要契约。
- **公共 API、协议和数据契约**：结合海勒姆定律、最小惊讶、健壮性、约定优于配置和单一事实来源；变更前识别调用方依赖的可观察行为及迁移影响。仅对协议允许的边界差异保持宽容，内部契约违例应尽早暴露。
- **模块与抽象边界**：用复杂性守恒、抽象漏洞、高内聚低耦合、接口隔离和最少知识原则判断复杂度由哪一层承担。只在稳定变化点、真实替换需求或测试隔离收益明确时引入抽象；DRY 复用稳定知识，不把偶然相似的实现强行合并。CQRS 仅在读写模型确有独立扩展需求时采用。
- **性能与资源优化**：用 Pareto 和阿姆达尔定律指导优先级；基于端到端测量定位主要瓶颈，优先优化对总耗时、吞吐或峰值内存贡献最大的部分，不以局部指标改善冒充整体收益。
- **错误处理与可靠性**：按信任边界区分防御性检查和 Fail Fast；验证外部输入及系统边界，不在可信内部层重复堆叠校验。保留错误上下文、确定性释放资源，并显式处理幂等性、并发和部分成功。

遇到原则冲突时，不按口号机械裁决：先守住正确性、安全、数据完整性和已有契约，再按用户目标、当前 workload、风险与可测证据选择总成本更低的方案。定律适用边界和常见冲突见 [ENGINEERING-PRINCIPLES.md](references/ENGINEERING-PRINCIPLES.md)；代码实现规则见 [PROGRAMMING-RULES.md](references/PROGRAMMING-RULES.md)。

## 16. 快速检查清单

```text
[ ] 任务类型和必要技能已判断
[ ] 关键假设、多义解释和重大取舍已显式说明；必要时已先澄清
[ ] 方案没有引入未要求的功能、抽象、配置项或防御性复杂度
[ ] 工具名称、schema、权限和副作用已确认
[ ] 绿地项目已完成架构先行、官方网络文档调研和候选方案比较
[ ] 已选择并遵循对应 CLI / 编程 / 工程参考规范
[ ] DSH/FastCtx/CLI 的关键行为已按上游仓库、匹配版本文档和当前 schema 核验
[ ] 本地文件优先 FastCtx
[ ] 结构搜索使用 ast-grep
[ ] 符号/调用链使用 codebase-memory
[ ] GitHub / Context7 不作为默认依赖；先检查 connector / CLI 的真实可用性
[ ] 当前 API/CLI 文档已按 lockfile 版本经 Context7 定位，并回到官方原文核验关键事实
[ ] Agent Skill 来源、脚本、许可证和 SKILL.md 已审阅；验证前未盲目安装或执行
[ ] GitHub 写入使用最小权限；安全校验或审批拒绝后不尝试绕过
[ ] 同源请求已批量化
[ ] 无依赖操作已合理并行
[ ] 依赖操作按 DAG 分层
[ ] 写入范围互斥
[ ] 每一处修改都可追溯到用户目标；未顺手清理既有死代码
[ ] 非简单功能已先比较方案并获设计确认；Team/subagent 任务已通过规格符合性与质量双阶段审查，发现问题已修复复审
[ ] 适用行为变更已观察目标测试因预期原因 RED，再以最小实现 GREEN；不适用时已说明原因和替代验证
[ ] 多阶段计划中的每个步骤都有对应的验证证据
[ ] 长任务使用后台任务机制，且已核验 job 终态/退出结果
[ ] PTC 并发仅用于明确 concurrency-safe 的当前参数，且遵守运行时上限
[ ] PTC 中间结果已裁剪，未把无关大 payload 带回上下文
[ ] 异常、Partial 和退出码已处理
[ ] 绿地项目已记录架构 ADR，必要时提供 C4 Context/Container 图
[ ] 性能敏感代码已分析时间/空间复杂度与理论下界
[ ] 基准、剖析和峰值内存数据已验证优化收益
[ ] diff 和必要测试已验证
[ ] 汇报只包含有证据的结果
```

最终原则：**少读取、少往返、少修改、少委派；每次调用都有目的，每次写入都有边界，每段代码都有契约，每个工程取舍都有理由，每个结论都有证据。** 流程参考：[Superpowers Brainstorming](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md)、[Subagent-Driven Development](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md) 与 [Test-Driven Development](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md)。
