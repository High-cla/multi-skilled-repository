# customize-dsh — 权威资料与版本核验

> 本索引记录本技能所依据的 DSH 上游资料。DSH 快速迭代，链接指向上游 `master` 仅用于发现入口；涉及实际操作时，必须先确认用户安装的 DSH 版本，再对照该版本 tag/commit 的文档、生成配置目录和源码。不要把当前 master 的默认值直接套用到旧版安装。

## 检索顺序

1. 确认实际可执行文件、版本、profile、`DSH_HOME`、安装路径与包管理器来源。
2. 先查官方用户文档和 package README；配置字段以该版本生成的 `docs/config-catalog.md` / `docs/config-catalog.zh.md` 为准。
3. 涉及运行时行为、生命周期、默认值或错误语义时，回查该版本实现、类型声明与测试；不要仅凭 README 示例推断。
4. 当前 Context7 可用时，先 resolve `DeepSeek Harness` 为 `/deepseek-ai/deepseek-harness`，再按单一主题 query 文档；对字段名、默认值和安全边界仍须回到官方原始文档/源码核验。Context7 不可用或索引落后时直接查上游仓库。
5. 不存在于当前安装版本的命令、工具、插件、路径或配置键，不要建议用户照抄；先确认该能力是否在其版本发布。

## DSH 官方资料

### 配置与启动

- [配置目录（英文，生成文件）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/config-catalog.md) · [配置目录（中文，生成文件）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/config-catalog.zh.md) — 每个 package 可配置字段、类型、默认值、注入服务和声明源码。生成文件应由仓库脚本维护，不要手工修改。
- [CLI 行为参考（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/reference/README.zh.md) — profile 初始化、bundle 层、参数边界、dump-config、配置 schema dump。
- [app-boot package README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/boot/app-boot/README.md) — profile/bundle composition、HMR 模板差异、启动失败与兼容性门禁。
- [架构说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md) — profile、bundle、patch 层的总体模型。
- [组合与 HMR 教程（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cordis-tutorial/06-composition-and-hmr.zh.md) — Cordis entry id、disabled、插件重载与配置文件 watcher。

### Settings / volatile 配置

- [Settings 子系统（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/settings.zh.md) — `ctx.settings` 的 describe/update/replace/mutate、profile entry id、revision 冲突。
- [Settings package README（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/settings/settings/README.zh.md) — 表单只投影插件 Config 中 `.volatile()` 字段；并明确旧 `settings.yaml` 在首次写入前改名为 `settings.yaml.imported`，之后逐 section 导入，当前组合拒绝的 section 只留在重命名文件中。
- [Settings legacy import 回归测试](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/settings/settings/tests/configuration.spec.ts) — 覆盖一个 section 成功写入、普通字段/缺失 entry section 被拒绝并保留在 `settings.yaml.imported` 的部分导入场景。
- [Volatile Config cookbook](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/adding-a-settings-card.md) — `.volatile()`、`.get()` 与 `loader/volatile-update`。
- [Permission presets package README（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/interaction/permission-presets/README.zh.md) — `presets` 表、`config.defaultPreset` 的组合默认值，以及 `permission` Settings namespace 对未来新会话默认值的持有方式。
- [Permission presets 子系统（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/permission-presets.zh.md) — 当前权限选择、默认值与 `ctx.permissionPresets` 服务边界。
- [Web Permission settings row](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-permission-presets/README.md) — Web「通用设置」中的默认权限行只改变未来会话；当前会话通过 picker 或 `/permission` 切换。
- [Base profile 权限组合](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/bundle/base/cordis.patch.yml) — 当前 profile entry id 为 `permission`，插件为 `@deepseek-ai/dsh-permission-presets`；配置预设表及可选 `config.defaultPreset` 的位置。
- [Permission preset Config source](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/interaction/permission-presets/src/index.ts) — `defaultPreset` 是 volatile Config 字段；缺省时按组合后的 sandbox/approval 默认值推断。

### Skills

- [Skills 子系统（英文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md) — provider registry、scope layer、rank、重复名称裁决、discovery cache 和 invalidation。
- [Filesystem skill provider README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md) — 直接子项扫描、frontmatter、roots、watch 配置、正文按需重读。
- [Skill registry README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill/README.md) — provider contract、scope-aware lookup 与完整定义加载。
- 注意：`ctx.skills` 是 provider registry；目录扫描路径仅适用于 local filesystem provider，不能据此排除 remote/embedded providers。

### Agent preset 与 Cordis 插件

- [Agent preset package README（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/preset/agent-preset/README.zh.md) — Cordis YAML 中定义 Agent 子插件列表；不要与其他基于目录的 preset 功能混为一谈。
- [Agent preset registry README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/preset/agent-preset-registry/README.md) — preset registry 与 session 选择的接口边界。
- 旧式 `$DSH_HOME/.agent-presets/<id>/`（`preset.yml` + `agent.cordis.yml`）已不再被当前上游读取；不要继续把它当作可生效配置目录。迁移说明见 [editing-cordis-compositions skill](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/preset/agent-preset/skills/editing-cordis-compositions/SKILL.md)。
- [Cordis primer（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cordis-primer.zh.md) — plugin、service、scope、lifecycle 基础。
- [Cordis API catalog](https://github.com/deepseek-ai/deepseek-harness/tree/master/docs/cordis-api) — API 具体签名与事件。

### MCP client

- [MCP client README（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.zh.md) — 当前 transport、配置字段、默认超时、重连、失败策略和图片/资源行为。
- [MCP client Config source](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/src/index.ts) — schema、serverName pattern、scope uniqueness、默认值。
- [MCP connection supervisor](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/src/connection.ts) — reconnect defaults、backoff、attempt budget。
- [MCP client generated config catalog](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/config-catalog.zh.md#deepseek-aidsh-mcp-client) — 当前版本字段约束。

### 自定义工具、系统提示与命令

- [Tools subsystem（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/tools.zh.md) — 工具注册、schema、执行与结果约定。
- [Adding a tool cookbook](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/adding-a-tool.md) — 最小工具插件开发流程。
- [System prompt subsystem（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/system-prompt.zh.md) — 系统提示段落 API。
- [Commands subsystem（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/commands.zh.md) — slash command 注册和生命周期。

## 当前上游核验得到的关键差异（不要视为跨版本常量）

- HMR 由 profile composition 决定。当前架构文档说明 base bundle 启用 config-only `dsh-hmr`，headless/SDK/ACP 关闭，`sdk-minimal` 不包含；profile patch 可覆盖。CLI 文档对随附模板的行为为准。
- `ctx.settings` 表单只编辑 volatile Config 字段；普通 Config 仍通过 Cordis patch 管理。不能宣称所有 `settings.yaml` 更改都会热生效。
- 权限默认值不再通过持续编辑 `$DSH_HOME/settings.yaml` 管理：该文件中的 `permission.defaultPreset` 仅在一次性 legacy import 时读取。当前 Web 用户应使用「通用设置」的 Permission 默认项；部署配置应调整 profile 中 `id: permission` 的 `@deepseek-ai/dsh-permission-presets` Config。该默认只用于新建会话。
- 旧 `settings.yaml` 在第一次写入前就重命名为 `settings.yaml.imported`，之后再逐 section 导入；不被活动 composition 接受的 section 会记录日志并只保留在该文件中。重命名不表示全部导入成功，必须检查日志和 `.imported` 文件并选择性恢复。
- local filesystem skill provider 默认 `watch: true`；frontmatter/skill entry 变化触发 catalog refresh，而正文每次 load 重新读取。资源子目录修改不等于 catalog refresh。
- MCP client 当前源码默认 `toolCallTimeoutMs = 60000`、`failOnStartupError = false`；`serverName` pattern 为 `[A-Za-z0-9_-]{1,32}`，唯一性按注册 scope 管理，agent scopes 可复用名称。以用户实际版本 config catalog 为准。
- MCP 当前支持 `stdio` 与 `streamable-http`；不能虚构 `remote` transport。
- Agent preset 存在不同概念/实现。确认用户指的是目录型 Agent preset 还是 `@deepseek-ai/dsh-agent-preset` 的 Cordis 子插件组合，再选择对应配置路径。


## Plugin development and publishing

- [First plugin tutorial（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/index.zh.md) — Cordis entry、`name` / `inject` / `apply`、对象/类形式、依赖注入与生命周期清理。
- [Plugin Config tutorial（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/config.zh.md) — Schemastery Config schema、默认值与加载期校验。
- [Tool tutorial（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/tool.zh.md) — 第一个模型可调用工具的端到端教程。
- [External plugin packaging and installation（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.zh.md) — **外部插件作者首要依据**；定义 bundle 的 `dsh.bundle.patch`、profile 的 `dsh.profile.bundles`、安装、patch 叠加、engines.dsh 兼容范围、Git `prepare` 和构建授权。
- [Tool authoring contract（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/adding-a-tool.zh.md) — 参数 schema、规范 JSON 输出、render、执行与错误语义。
- [Extension plugin shapes cookbook（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/extension-cookbook.zh.md) — tool、hook、UI 与 protocol driver 扩展方式。
- [Client Modules README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/modules/README.zh.md) / [Client Modules subsystem](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/client-modules.md) — 浏览器端 `dsh.client`、`./client` 入口、client bundle、模块加载与资产路由。
- [Client stack internal conventions](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/AGENTS.md) — DSH 上游仓库内部 client 导出、slots、store 与 inject 规则；不要把所有 monorepo 维护约束当作外部插件硬要求。
- [Adding a workspace package（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/adding-a-package.zh.md) — **只适用于修改 DSH 上游 monorepo 本身**；其中 `private`、workspace version、tsconfig references 等不是外部插件 package 的统一模板。
- [Generated Config Catalog（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/config-catalog.zh.md) — 以目标版本核验真实配置字段、类型和默认值。
- [DeepSeek Harness Terms of Use](https://www.deepseek.com/en/harness/terms-of-use/) — 官方安全使用和隔离边界。

## Community skills and implementation examples (non-authoritative)

这些仓库有参考价值，但**不是 DeepSeek 官方仓库或规范**；API、版本和实践应逐项回到上方上游资料核验。

- [vlln/dsh-skills — make-dsh-plugin](https://github.com/vlln/dsh-skills/tree/main/skills/make-dsh-plugin) — 社区开发技能，涵盖插件形态选择、开发步骤、项目化、验证、发布和生态索引；适合作为工作流/检查表补充，不是字段契约。
- [brzvsk/dsh-plugins — Visualize](https://github.com/brzvsk/dsh-plugins/tree/main/visualize) — bundle + client half、工具 + slash command + keyed tool view，以及使用 sandboxed iframe 隔离不可信 HTML 的实例。
- [PerryLink/dsh-mcp-panel](https://github.com/PerryLink/dsh-mcp-panel) — 较完整的 Host/client 双端项目，示范状态快照、审批门、备份/验证、脱敏、真实运行时测试和兼容性 gate；版本验证声明仅代表其记录的测试时间点。
- [vlln/plugin-registry](https://github.com/vlln/plugin-registry) — 社区插件索引实现，适合研究 registry data 与生成流程；不是官方市场审核结论。

社区 Awesome 列表与 GitHub `dsh-plugin` topic 只用于发现仓库。开始使用前检查源码、许可证、维护状态、发布包内容、依赖范围、安装脚本与真实 smoke tests；下载数、市场排名和徽章不是安全证明。

## 验证命令

先确认本机命令解析到哪个安装：

```sh
command -v dsh
dsh --version
dsh --help
```

Windows PowerShell 可用：

```powershell
Get-Command dsh -All | Format-Table CommandType, Source, Version
dsh --version
dsh --help
```

在改动前查看实际 profile composition：

```sh
dsh --profile <name> --dump-config
dsh --profile <name> --dump-config-schema
```

`--dump-config-schema` 会导入组合中的插件以读取 schema；只对可信 profile 使用。dump 输出也不代表命令行 app args 已解析，CLI 文档明确 dump 模式拒绝 app args。

## 安全与操作约束

- 不输出或回显 API key、token、credential 文件内容；检查时只验证环境变量是否存在、字段是否引用正确。
- 改动前备份目标文件；保留未知字段、注释和用户未要求修改的配置。
- Cordis patch 的 id-targeted 修改会替换目标 entry 的整份 `config`，不是深度合并；先读完整原配置再编辑。
- `disabled: true` 是保留 entry 但不挂载；不要发明 `disable: { id }` 这种未被当前 patch dialect 支持的操作。
- 修改后先 dump/validate，再按 profile 是否启用 HMR 决定是否需要重启；不要盲目重启生产会话。



### 上游版本核验记录

- 本次资料核验日期：2026-11-03。
- 核验时 `deepseek-ai/deepseek-harness` `master` HEAD：[`ce7073d51254c26cd63b22a60835b8f948deb447`](https://github.com/deepseek-ai/deepseek-harness/commit/ce7073d51254c26cd63b22a60835b8f948deb447)，提交时间 2026-10-29 16:13:15 UTC。该 SHA 仅用于复核本次文档快照，不等于用户安装版本；后续更新需重新读取官方 HEAD / tag。
