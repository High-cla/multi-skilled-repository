---
name: cli-first-decision
description: "多步骤任务的工具选择、CLI 与 MCP 编排、官方文档检索、Agent Skill 发现/验证、批量处理、代码搜索、调用链分析、API 调试、并行执行和安全写入。触发词：CLI 优先、gh、GitHub、Context7、ctx7、官方文档、skills、SKILL.md、工具选型、并行、批量操作、代码搜索、影响面、任务委派。"
metadata:
  author: High-cla
  version: "3.9"
---

# CLI-First Decision 3.9

## 1. 目标与原则

目标：以最少的工具往返、最短的关键路径和最低的上下文/资源成本，可靠地完成用户目标；从零开始时先确定有证据支撑的最优适配架构，具体实现默认以运行速度和峰值内存优先。

- 先判断任务，再选择工具；不为使用 CLI 而使用 CLI。
- 本地文件操作优先 FastCtx；终端组合与批处理优先 CLI。
- 结构匹配优先 ast-grep；符号关系优先 codebase-memory。
- 先复用项目原生 API，再考虑额外 wrapper。
- 无依赖操作同轮并行；可管道合并的操作优先合并。
- 并行必须考虑调用成本、限流、上下文和写入冲突。
- 从零开始先进行需求/质量属性分析、网络官方文档调研、候选架构比较和风险原型，再确定架构并开始主体实现。
- 具体代码实现优先追求更短运行时间和更低峰值内存，先分析复杂度/理论下界，再用基准与剖析迭代逼近最优。
- 对 DSH/PTC、FastCtx、CLI 和性能工具，优先查阅 [AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md) 中的项目仓库、版本匹配手册和规范；Context7 可用时先解析库 ID、查询目标版本文档，再回到官方原文核验；最后按本机版本/schema 校验。
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
| 写或改代码 | clean-code、coding-standards |
| Bug、复现、报错定位 | systematic-debugging |
| 写计划或执行计划 | writing-plans、executing-plans |
| 代码审查 | requesting-code-review、receiving-code-review、code-review |
| 长任务或跨会话续跑 | long-task-continuation |
| 多子智能体并行 | dispatching-parallel-agents、subagent-driven-development |
| JSON/YAML 解析 | jq-query |
| HTTP/API 调试 | git-curl |
| 文件查找/全文搜索/模糊过滤 | fd-find、rg-search、fzf-filter |
| Windows CMD/PowerShell 脚本 | cmd-powershell-pitfalls |

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

本地文件和终端操作优先 FastCtx。不要使用 shell 等价物替代 FastCtx 的专用文件工具。

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
- SKILL.md 按 Agent Skills 规范校验；详细检索流程、命令、源清单和安全门见 [ONLINE-RESEARCH-AND-SKILLS.md](references/ONLINE-RESEARCH-AND-SKILLS.md)。

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

详细的端到端执行顺序、后台任务生命周期、渐进式上下文读取、缓存失效和失败恢复见 [EXECUTION-EFFICIENCY.md](references/EXECUTION-EFFICIENCY.md)。

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
- 详细的 TypeScript/Python runtime 差异、调度、取消、输出限制和 Session 记录见 [PTC-EXECUTION.md](references/PTC-EXECUTION.md)；版本依据见 [AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md)。


## 11. 计划与子智能体

### 何时写计划

多阶段、多模块、依赖关系复杂、风险较高、需要长时间执行或跨会话续跑时，先写可验证计划。简单任务直接执行，不为形式写计划。

计划至少包含：

- 目标和不做什么。
- 相关文件/模块。
- 依赖顺序。
- 每步执行工具。
- 写入边界。
- 验收命令和成功条件。
- 失败时的回滚/降级路径。

### 何时委派

只在独立工作能抵消代理启动和协调成本时委派。优先委派只读调研、正交审查和文件边界明确的独立实现；不按“跨两个模块”机械触发。

每个子智能体 prompt 必须自包含：

```text
TASK:
一个原子目标。

WORKING_DIR:
绝对工作目录。

EXPECTED OUTCOME:
具体交付物和验收标准。

REQUIRED TOOLS:
当前环境确实可用的工具。

MUST DO:
必要检查和分析。

MUST NOT DO:
禁止操作、禁止修改范围。

CONTEXT:
文件路径、项目现有模式、已知约束。

ACCEPTANCE:
明确的测试/检查命令及通过标准。

REPORT:
修改文件、关键结论、实际验证、未解决问题。
```

子代理无声失败是可能情况。回收结果后，主代理检查任务状态、文件 diff 和验证证据；不得仅凭子代理的成功声明验收。

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

| 任务 | 参考文档 |
|---|---|
| CLI 模板、Windows Git Bash、压缩文件和 diff | [CLI-TOOLS.md](references/CLI-TOOLS.md) |
| 在线资料、Context7、GitHub CLI、Agent Skills 发现/验证 | [ONLINE-RESEARCH-AND-SKILLS.md](references/ONLINE-RESEARCH-AND-SKILLS.md) |
| 编写/修改代码、API、错误处理、测试和性能优化 | [PROGRAMMING-RULES.md](references/PROGRAMMING-RULES.md) |
| 绿地架构、官方调研、候选方案、ADR/C4 | [ARCHITECTURE-DESIGN.md](references/ARCHITECTURE-DESIGN.md) |
| 工程定律、复杂性和性能取舍 | [ENGINEERING-PRINCIPLES.md](references/ENGINEERING-PRINCIPLES.md) |
| DSH/FastCtx/ast-grep/codebase-memory 路由 | [REFERENCE.md](references/REFERENCE.md) |
| PTC 执行细节 | [PTC-EXECUTION.md](references/PTC-EXECUTION.md) |
| 上游仓库、CLI 手册与规范 | [AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md) |

执行底线：正确性、安全、数据完整性和已有 API 契约是硬约束；先理解 workload、复杂度和理论下界，再用真实基准、profile、分配与峰值内存数据优化。大数据优先流式、分块和有界队列。绿地项目先调研当前官方文档、比较至少两个可行架构并记录 ADR；既有项目先检查现状和基线。工程原则是决策启发式，不是机械打勾项；细则只在当前任务需要时读取。


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

最终原则：**少读取、少往返、少修改、少委派；每次调用都有目的，每次写入都有边界，每段代码都有契约，每个工程取舍都有理由，每个结论都有证据。**
