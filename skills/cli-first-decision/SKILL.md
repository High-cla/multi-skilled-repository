---
name: cli-first-decision
description: "当任务需要多步骤工具选型或编排、CLI/MCP 批量操作、官方文档或 Agent Skill 检索验证、代码结构/调用链/影响面分析、API 调试、并行委派或安全写入时使用。适合需要建立依赖 DAG、跨模块执行或验证工具副作用的任务；单步回答、纯状态查询、已知路径简单读取和单文件小改通常不触发。"
license: MIT
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

- 本地已知文件读取优先 FastCtx；多文件一次批量读取。全文搜索用 grep，文件名查找用 glob；不要为简单文件操作启动 shell。
- 批量替换先 dry-run；写入前核对路径集合，写后检查命中数、编码、行尾和 diff。
- FastCtx Bash 采用非交互 POSIX/Git Bash 语法；路径可能含空格或换行时使用 NUL-safe 管道。
- 前台命令预计超过四分钟时用 `run_background`；用 job 工具核对终态与退出结果后再验收。
- 具体工具参数、跨平台差异与 fallback：按需读取 [CLI-TOOLS.md](references/CLI-TOOLS.md)；长任务与恢复见 [EXECUTION-EFFICIENCY.md](references/EXECUTION-EFFICIENCY.md)。

## 5. CLI 选择矩阵

| 任务 | 首选 |
|---|---|
| 文件名 / 文本 | fd / rg |
| 语法结构搜索与改写 | sg（ast-grep） |
| JSON / YAML | jq / yq |
| HTTP/API | curl |
| GitHub | 当前可用的 GitHub connector 或 gh |
| 当前库/API 文档 | Context7 connector 或已安装的 ctx7 |
| 模糊筛选 / 结构化 diff | fzf / difft |

调用前检查二进制版本、help、schema、权限和副作用；不为一次简单任务引入依赖。详细选型与跨平台边界见 [CLI-TOOLS.md](references/CLI-TOOLS.md)。

## 6. ast-grep：结构搜索与规则开发

代码形状、语法节点和批量结构重构使用 ast-grep；普通文本仍用 rg。先明确语言与节点，再以正例、反例和边界样例验证规则，预览 rewrite 并复核 diff；不要用宽泛正则代替 AST。

## 7. codebase-memory：符号与依赖分析

涉及符号定义、调用者/被调用者、模块依赖和影响面时优先使用 codebase-memory，再用当前源码、测试和构建配置交叉验证；索引不是源码事实来源。

## 8. 远程仓库、官方文档与 Agent Skills

- 当前 GitHub/Context7 connector 或 CLI 可用时才使用；先核对实际工具 schema、版本、权限和仓库/项目范围。
- Context7 先 resolve 精确 library ID，再按目标版本查询单一主题；重要 API、默认值、弃用和安全结论回到官方原文/源码核验。
- 第三方 Agent Skill 先检查维护方、来源、许可证、引用文件、脚本和外部调用；先 preview/审阅，不自动安装或执行未知脚本。
- 详细来源优先级、检索步骤和远程写入边界见 [ONLINE-RESEARCH-AND-SKILLS.md](references/ONLINE-RESEARCH-AND-SKILLS.md) 与 [AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md)。

## 9. 并行、管道与调用合并

先建立依赖 DAG 和 Read/Write 集合；同源可批量时优先批量，无依赖且 concurrency-safe 的调用才并行，有依赖则分层执行，共享资源写入串行。并行收益必须大于启动、限流、上下文与集成成本。

- PTC 子调用只有在当前参数明确标记 concurrency-safe 时才可重叠；未知/异常按 exclusive 串行处理，并遵守当前运行时上限。
- 保留部分成功结果；失败后先核对已发生的副作用，不假设外层失败会回滚。
- 中间结果在程序内裁剪/聚合，只返回决策所需字段；图像和 additionalContexts 也计入上下文预算。
- 子智能体只承接足够独立、上下文可自包含且读写范围可分离的工作；同一文件/接口单写入者。
- 细节见 [EXECUTION-EFFICIENCY.md](references/EXECUTION-EFFICIENCY.md)。

## 10. DSH PTC：运行时入口与详细参考

仅当当前 Session 明确启用 PTC 且提供 `run_code` 与 `tools:sdk` 时使用；先读取注入的语言、SDK、schema、并发策略和资源限制。单步调用直接用原生工具。部分失败、取消、结果裁剪和 runtime 语义见 [PTC-EXECUTION.md](references/PTC-EXECUTION.md)。

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
- **配置边界**：仅当用户要求改变 DSH profile/preset、默认 Team 模式或插件组合时，才加载 同仓库的 `customize-dsh` 技能；普通任务协作不改部署配置。

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
1. **RED**：先按目标 API 写测试并运行。若仅因本次要新增的导出符号/类型尚不存在而无法编译或导入，接受为**编译期 RED**并记录准确诊断；这不等同于目标行为 RED。随后只补足让测试可编译的最小导出声明、类型或签名（必要时用明确失败的 stub），不实现目标行为；重跑后，行为断言应因目标行为缺失而失败，纯类型/API 契约则可由编译期断言验证。
2. **GREEN**：只做让目标测试通过的最小生产改动；重新运行同一测试并确认通过，不扩展需求或顺手重构。
3. **回归与重构**：运行受影响测试及必要的类型检查、lint/build；重构后重新验证。记录实际命令、退出码和关键输出。
4. **证据**：报告编译期 RED（如适用）、行为 RED、GREEN 结果及回归结果；与目标符号无关的编译/导入错误仍是无效 RED，不得作为 test-first 证据。未实际观察到的结果不得宣称通过。
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

本技能只决定工具路径；实现规则按需加载，不在主文件重复展开：
- 绿地/重大重构：[ARCHITECTURE-DESIGN.md](references/ARCHITECTURE-DESIGN.md)
- 工具版本、上游来源与行为核验：[AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md)
- CLI / FastCtx：[CLI-TOOLS.md](references/CLI-TOOLS.md)
- 并行、后台任务与恢复：[EXECUTION-EFFICIENCY.md](references/EXECUTION-EFFICIENCY.md)
- 代码实现与测试：[PROGRAMMING-RULES.md](references/PROGRAMMING-RULES.md)
- 工程原则权衡：[ENGINEERING-PRINCIPLES.md](references/ENGINEERING-PRINCIPLES.md)
- PTC：[PTC-EXECUTION.md](references/PTC-EXECUTION.md)

## 16. 快速检查清单

```text
[ ] 任务类型、必要技能、目标/非目标和成功条件已明确
[ ] 工具 schema、权限、版本、数据范围与副作用已确认
[ ] FastCtx/CLI/AST/符号工具按实际问题选择，无不必要往返
[ ] 同源请求批量化；依赖按 DAG 分层；并行读写范围互斥
[ ] 非简单功能已比较方案并获设计确认，再制定计划和实现
[ ] Team/subagent 任务已通过规格符合性与质量双阶段审查，问题已修复复审
[ ] 适用行为变更已观察目标测试因预期原因 RED，再以最小实现 GREEN
[ ] 写入仅覆盖授权范围，非幂等失败后已先查状态
[ ] 长任务已核对终态、退出码和输出完整性
[ ] diff、必要测试与外部副作用已验证
[ ] 未执行/未通过的检查没有被报告为通过
```

最终原则：**少读取、少往返、少修改、少委派；每次调用有目的，每次写入有边界，每个结论有证据。**

