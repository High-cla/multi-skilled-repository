# DSH 配置与运行维护参考

> 本文承载 customize-dsh 的详细配置操作说明。先确认目标 DSH 版本、实际安装路径和活动 profile；不要把当前上游快照当成用户环境事实。由 `SKILL.md` 在相关任务中按需加载。

## 目录

- [配置生效与文件布局](#使配置生效热重载-vs-重启)
- [Settings 与迁移](#settings-与旧版-settingsyaml-迁移)
- [Profiles 与 patch 层](#profiles-与-patch-层)
- [MCP servers 与 Plugin Market](#mcp-servers)
- [文件修改策略](#文件修改工具的默认策略022-版本线)
- [权限与沙箱](#权限与沙箱)
- [命令、系统提示与恢复](#命令与系统提示)

## 使配置生效（热重载 vs 重启）

不要把“保存文件”一概等同于 HMR：是否热重载由当前 profile 的组合配置决定。上游 `app-boot` 文档明确说明，随附 `web` profile 启用 live reload；`headless`、`sdk`、`sdk-minimal`、`acp` 等模板在启动时应用 patch，修改后需要重启。

- **cordis.patch.yml / `!!js`**：只有组合树挂载了 `@deepseek-ai/dsh-hmr`（或相应 HMR provider）时，文件变更才会触发按 entry `id` 的卸载、重载或重新配置；`!!js` 也只有在实际 Loader 求值时才生效。先用 `dsh --profile <name> --dump-config` 查看最终组合，再确认 HMR entry 是否存在。
- **settings / volatile Config**：不是所有 `settings.yaml` 字段都会热更新。插件必须把字段声明为 `volatile` 并按其 API 读取；`.get()` 取得当前值，消费者通过 `loader/volatile-update` 等机制响应变化。`ctx.settings.update/replace/mutate` 是配置表单编辑 API，按 profile entry id 操作，并带可选 revision 冲突检查；不能据此推断任意文件编辑都实时生效。
- **技能**：本地 filesystem provider 默认 watch roots。新增、重命名、删除技能或修改 frontmatter 会使下一次 catalog lookup 更新；技能正文在每次 `get()` 时重新读取，因此正文修改无需 catalog cache invalidation。`references/`、`scripts/`、`assets/` 等资源文件变更本身不会触发技能目录 catalog refresh。
- **agent preset**：默认 preset 选择影响后续新建会话；已运行会话不会因修改默认值自动切换。切换 preset 有空白会话等限制，需按当前 preset subsystem 文档核验。
- **bundle 列表**：修改 profile manifest 的 `dsh.profile.bundles` 会改变安装/组合结构，使用 `dsh plugin --profile <name> add/remove` 管理依赖，并按 CLI 输出完成安装与重启。
- **运行时注入**：`cordis_define` / `cordis_run` 等动态 Cordis 工具、`dsh-super-injector` 的 `dev_*` 工具仅在相应插件、工具和权限实际挂载时可用；不可把开发注入通道当作每个 DSH profile 的内置能力。

## 文件存放位置

| 范围 | 路径 |
|------|------|
| Harness home | `$DSH_HOME`，缺省 `~/.dsh` |
| 旧版设置导入文件 | `$DSH_HOME/settings.yaml`（兼容导入入口；首次写入前重命名为 `settings.yaml.imported`，重命名不代表所有 section 均已导入） |
| home 级 patch（所有 profile 共享，优先于 profile 层） | `$DSH_HOME/cordis.patch.yml` |
| 用户凭据 | `$DSH_HOME/.credentials.yaml` |
| 用户环境层 | `$DSH_HOME/.env`（优先级低于继承环境与调用目录 .env） |
| profile 目录 | `$DSH_HOME/profiles/<name>/`（package.json、cordis.patch.yml、node_modules/、pnpm-workspace.yaml） |
| 安装后备扁平目录 | `$DSH_HOME/profiles/node_modules/`（符号链接，每次启动修复） |
| 项目技能 | `<projectRoot>/.dsh/skills`（rank 100） |
| 项目 agents 技能 | `<projectRoot>/.agents/skills`（rank 200） |
| 自定义技能目录 | `Config.customSkillDirs`（rank 300） |
| 用户技能 | `$DSH_HOME/skills`（rank 400） |
| 用户 agents 技能 | `<agentsHome>/skills`（rank 500） |
| 随包技能 | `Config.bundledSkillDir`（rank 600） |
| Agent preset | 当前通过 profile composition 中的 `@deepseek-ai/dsh-agent-preset` entry 声明；旧式 `$DSH_HOME/.agent-presets/<id>/` 目录不再读取 |

项目根目录 = 最近的含 `.git` 的祖先目录；找不到时用 cwd。技能本地提供方跳过 `$DSH_HOME` 的 `.system` 子目录。

## Settings 与旧版 settings.yaml 迁移

**不要把 `$DSH_HOME/settings.yaml` 当作当前通用配置数据库或实时配置文件。** 当前上游 Settings package 文档说明：早期版本遗留的 `settings.yaml` 会在 Settings 启动、Loader 完成所有条目加载后尝试导入一次；每个 section 按其 id 写入当前组合中对应的 profile entry（例如 `ui-developer-tools` → `ui-settings`、`ui-onboarding` → `ui-settings-general`、`shell` → 当前平台的 shell 执行器 entry）。**文件会在第一次写入前先重命名为 `settings.yaml.imported`，然后才逐 section 写入**。当前组合拒绝的 section 会记录日志，并只保留在这个重命名文件中；因此，重命名不以所有 section 导入成功为前提，`settings.yaml.imported` 也不代表迁移已完整成功。被拒绝的 section 不会因为文件已重命名而自动重试。

**部分导入后的检查与恢复：**

- 检查本次启动日志中的拒绝/导入错误，并检查 `$DSH_HOME/settings.yaml.imported` 中仍保留的旧 section。先备份该文件和当前 profile 配置。
- 按当前 profile 的实际 entry id 和该版本 Config schema 逐项核对；不要假设旧 section 名始终等于当前 entry id，也不要把整份旧 section 直接覆盖到现有配置。
- 普通 Config 值按当前 profile 的 `cordis.patch.yml` 规则选择性恢复；只有 schema 明确声明为 `.volatile()` 的字段才通过 Settings 表单/API 修改。
- 不要把 `settings.yaml.imported` 直接改回 `settings.yaml` 并重启作为默认恢复方式。应先确认目标 entry、字段和现有覆盖层，再人工选择需要恢复的值；已重命名的文件不会自动重试被拒绝的 section。

当前配置编辑边界：

- 普通插件 Config 通过 profile 的 `cordis.patch.yml`、home patch 或 `--patch` overlay 配置；后应用层优先。
- `ctx.settings` 表单只投影插件 Config 中声明为 `.volatile()` 的字段，并按 profile entry id 定位插件实例。
- `ctx.settings.update(ns, patch, expectedRevision)` 合并字段；`replace` 重置该 entry 的 volatile 字段后应用新值；`mutate` 按路径编辑并可保留客户端未收到的秘密字段。revision 用于拒绝过期写入。
- 业务插件通过 Config 引用的 `.get()` 读取 volatile 值，并按 `loader/volatile-update` 等机制响应更新。普通字段不是 volatile，不能据此承诺热更新。
- Secrets 应使用凭据服务/credential reference 或环境变量引用；不要把明文密钥写入技能示例、patch、日志或聊天回复。0.2.2-rc.1 的凭据解析行为按运行形态区分：Web/Desktop 的用户保存凭据优先；Headless 默认从环境变量与 `.env` 读取，不使用已保存的用户密钥。不要把一种 profile 的优先级套用到另一种部署。

需要确认字段时，查当前版本的生成 config catalog 和 [Settings 子系统文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/settings.zh.md)，不要根据旧的本机示例猜测 namespace 或字段默认值。

## Profiles 与 patch 层

`$DSH_HOME/profiles/<name>/` 是 profile 根。配置树层叠（**后应用者胜**）：

```
空根节点
→ [package.json 的 dsh.profile.bundles 顺序] 每个 bundle 的 patch
→ profiles/<name>/cordis.patch.yml（profile 层）
→ $DSH_HOME/cordis.patch.yml（home 层，各 profile 共享）
→ 按 argv 顺序的 --patch <path> overlay
```

- profile 根文件 `cordis.yml` 默认是空数组 `[]`——**编辑 cordis.patch.yml，不要直接改 cordis.yml**
- `package.json` 的 profile manifest：`"dsh": { "profile": { "bundles": [...] } }`（有序 bundle 层列表，如 `@deepseek-ai/dsh-base`、`@deepseek-ai/dsh-web-app`）；bundle 包自身用 `"dsh": { "bundle": { "patch": "./cordis.patch.yml" } }` 声明其 patch 层
- 随附模板包括 `web`、`headless`、`acp`、`sdk`、`sdk-minimal`；具体组合以目标版本的 `app-boot` 与 CLI reference 为准。`dsh --profile <custom> --from-default-profile <template>` 可从指定随附模板创建/替换自定义 profile。**这是破坏性重置**：它删除目标目录中已有依赖与用户 patch，再用模板副本替换；先备份整个 profile。进程在替换中途异常时，还需检查 CLI 文档说明的 staging/previous 恢复目录。
- `dsh plugin --profile <name> <pnpm-args...>` 在 profile 不存在时会先初始化：有同名随附模板则使用模板，否则创建仅含 `@deepseek-ai/dsh-base` 的 profile，再把参数透传给 pnpm。不要再笼统声称未知 profile 一律启动失败。
- `dsh plugin` 成功运行后会根据已安装依赖的 `dsh.bundle.patch` 声明自动更新 `dsh.profile.bundles`；不声明 bundle 的依赖仍保留为普通依赖。添加、移除或更新 bundle 后需要重启 profile；普通 patch 文件编辑是否热生效仍取决于当前组合是否启用 HMR。

`cordis.patch.yml` 是**顶层 YAML 数组**，每个元素是 patch 条目。三种语义：

```yaml
# 1) insert：追加 entry
- insert:
    - id: mcp-fastctx            # 行 id；同一组合树中应保持稳定且唯一
      name: '@deepseek-ai/dsh-mcp-client'   # 插件包名/相对路径
      config:                    # 插件配置（随插件 schema 而异）
        serverName: fastctx
        transport: stdio
        command: C:/path/to/binary
        args: ['serve']
        env: { KEY: '1' }
        cwd: !!js process.cwd()  # !!js 表达式在挂载时求值
        # toolCallTimeoutMs 默认 60000 ms；需要时再显式覆盖
# 2) id-targeted：命中 id 即【替换该 entry 的整份 config】——无深度合并，
#    必须重述要保留的所有字段
- id: some-plugin-id
  name: '@deepseek-ai/dsh-xxx'
  config: { ... }
# 3) disabled：保留 entry，但不挂载
- id: some-plugin-id
  disabled: true
```

**校验与失败规则**：

- patch 命中组合树中不存在的 entry id → 仅 stderr 警告
- 空文件或仅注释文件 → **throws**（解析成 nothing 不是列表）；用 `[]` 禁用一个层
- 缺失/不可读/不可解析/非数组文件 → throws；`--patch` 指定的文件缺失也 throws
- entry **不带 `id`** → 每次读取生成新 id → 任何配置编辑都被视为"删了再加"并重新挂载
- 启动失败（fail loud）：boot/loader rejection → 一行标签 stderr + `exit(1)`

**动手前先验证**：`dsh --profile <name> --dump-config`（离线渲染，不启动；`--dump-default-config` 只 dump bundle 层）→ 确认行与覆盖无误再启动。

**Schema dump**：`dsh --profile <name> --dump-config-schema` 输出 profile entry/patch 的 JSON Schema，**不会挂载组合或运行插件 `apply`**；但会导入 profile 中的可信模块，并可能调用 Config getter/lazy builder。它不执行 transform callback，也不求值 `!!js` 配置表达式。只对可信 profile 使用；输出中的声明默认值或原始错误仍可能包含敏感内容，分享前先检查。

## MCP servers

通过 `cordis.patch.yml` 插入 `@deepseek-ai/dsh-mcp-client` 行（见"Profiles 与 patch 层"示例）。当前上游默认值以 [MCP client README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.zh.md) 和生成的 config catalog 为准。关键配置键：

- `serverName`：桥接名，工具前缀 `mcp__<serverName>__<工具原始名>`；须匹配 `[A-Za-z0-9_-]{1,32}`，在同一注册作用域内唯一；独立 agent scope 可隔离复用
- `transport`：`stdio` | `streamable-http`（官方只有这两种，没有 `remote`）
- `command` + `args`：stdio 模式的可执行与参数。生产部署优先使用可预测的可执行路径并固定包版本；`npx` 可能触发包解析/网络安装，不应在未评估可重复性时作为生产默认。
- `env`：传给服务器的环境变量；`cwd`：工作目录（常用 `!!js process.cwd()`）
- `toolCallTimeoutMs`：每次 MCP `tools/call` 或资源请求的超时，当前默认 **60000 ms**；只有确认目标服务器确实需要更长时间时才提高。
- `failOnStartupError`：初始连接或工具同步失败时是否拒绝插件激活，当前默认 **false**；默认情况下 DSH 可继续启动，但该服务器工具不会出现并会记录错误。若服务为关键依赖，再显式设为 `true`。
- 远程（streamable-http）：`url` + 可选 `headers`

## 内置 Plugin Market 与扩展来源

官方上游提供 Plugin Market/Discover 页面与只读 `plugin_market` 工具，用于读取用户配置的索引、浏览条目与版本。索引未签名，条目描述/元数据属于第三方输入，不能视为 DeepSeek 官方发布或安全审核。`plugin_market` 中的 `update-available` 仍表示市场条目版本高于已安装版本，市场工具本身不执行升级；但 0.2.2-rc.1 的 Plugin Manager 已提供独立 `updateBundle(name, version)` 流程，供符合条件的第三方 bundle 更新到一个经过兼容性检查的精确版本。有 HMR 时先停旧插件并安装新包，失败时尝试重新安装旧版本；恢复也可能失败。无 HMR 时可能覆盖磁盘包并返回 `restart-required`。因此不要再把“必须卸载后重装”当成所有插件更新的通用规则，也不要把该能力说成市场工具自动升级。安装或更新前仍需审查仓库、manifest、`engines.dsh`、发布产物和 Git `prepare`/安装脚本；市场列表不是安全背书。

官方参考：[Plugin Market README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/boot/plugin-market/README.zh.md)、[Plugin Market tool catalog](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/tool-catalog.zh.md)。

## 文件修改工具的默认策略（0.2.2 版本线）

- `dsh-base` 中 `fs-observation-policy` 以 `disabled: true` 交付；未显式开启时，`write` 覆盖、`edit` 做字面量替换，文件修改不受 read-before-write / stale-file 检查门禁约束。需要恢复策略时，在有效组合中把对应 entry 的 `disabled` 设为 `false`。
- `tool-fs.applyPatch` 的 schema 默认值是 `false`，但具体组合可覆盖。当前同一上游 HEAD 的 base patch 文件把该值写为 `false`，tool catalog 与实现说明则称 `dsh-base`/Web `standard` 启用它；这是官方资料之间的未解决不一致。应以用户当前 profile 的 `dsh --profile <name> --dump-config` 和实际工具目录为准，不要仅凭 catalog 或 bundle 文件一处断言。
- 沙箱围栏与 Review 变更查看仍然独立存在；不要把 Review 记录误当作修改前阻止覆盖的门禁。

## 权限与沙箱

权限预设把两个 knob 捆绑成具名预设：

| 预设 | sandbox/mode | approval/policy |
|---|---|---|
| `workspace-write` | `workspace-write` | `ask` |
| `danger-full-access` | `danger-full-access` | `never` |

- `custom` 是保留名（派生的"非预设"状态，不可切换）
- `SandboxMode`：`read-only`（拒绝写入）| `workspace-write`（工作区根+后端临时区）| `danger-full-access`（绕过隔离，直接 spawn 原始 argv）
- `ApprovalPolicy`：`ask`（委托应答者链，无应答 fail-closed 为 unavailable）| `never`（确定性 `rejected`，不分发应答者）
- **用户修改未来新会话的默认预设**：在 Web GUI 的「通用设置」中修改 Permission 默认项。它读写 `permission` Settings namespace 的 `defaultPreset`，并持久化到当前 profile；只影响之后创建的新会话，不改写现有或恢复中的会话。
- **部署者配置预设表与配置默认值**：在当前 profile 的 `cordis.patch.yml` 中修改 `id: permission`、`name: '@deepseek-ai/dsh-permission-presets'` entry 的 `config.presets` / `config.defaultPreset`。`defaultPreset` 必须指向 `presets` 中实际配置的 key；未显式设置时，上游从组合后的 sandbox/approval 默认值推断（随附 base 组合通常为 `workspace-write`，`DSH_PERMISSION_MODE` 会影响底层组合默认值）。

  ```yaml
  # 示例是该 entry 的完整 config；id-targeted patch 会整体替换 config，
  # 修改时必须保留目标 profile 已有的全部 presets 和其他字段。
  - id: permission
    name: '@deepseek-ai/dsh-permission-presets'
    config:
      presets:
        read-only:
          sandbox: read-only
          approval: ask
        workspace-write:
          sandbox: workspace-write
          approval: ask
        danger-full-access:
          sandbox: danger-full-access
          approval: never
      defaultPreset: workspace-write
  ```
- **旧版文件边界**：`$DSH_HOME/settings.yaml` 中的 `permission.defaultPreset` 仅在旧文件首次迁移导入时读取；文件会先重命名为 `settings.yaml.imported`，之后再导入。迁移完成后再编辑旧 `settings.yaml` 不会改变当前默认权限，也不会触发重新导入。
- 会话被拒操作报告 `[sandbox: ...]` 标记——属策略拒绝而非命令失败，不要绕道重试；如本会话允许且真实被拒，可用 `sandbox_permissions` 一次性升级精确命令

## 命令与系统提示

- **slash 命令是插件级 API**（非文件）：插件用 `ctx.commands.register(CommandDefinition)` 注册（`name` 小写无斜杠/`description`/`input?.hint`/`handler`），执行结果直接呈现给 UI 不经模型；生命周期事件 `command/run`、`command/done`，注册变更 `commands/change`
- **系统提示词是插件级 API**：`ctx.systemPrompt.section({ name, order, text|complete })` 注册提示词段落（惯例：`-100` 宿主身份、`0` 部署 persona、工具指引 100–199；`complete: true` 段落独占整份提示词，多于一个失败）；`context()`/`variable()` 注册动态上下文与插值变量
- **用户级 persona 定制**：`@deepseek-ai/dsh-persona` 插件（patch 挂一行即可），config 含 `text`/`complete`/`includeRuntimeContext`，渲染为 `deployment:persona` 段，支持 `{{variable}}` 插值；系统提示词包 `@deepseek-ai/dsh-system-prompt` 另有 `persona`/`toolOrder`/`includeHarnessIdentity`/`includeRuntimeContext` 配置键（改 compose 内置配置前先用 `--dump-config` 查确切条目 id）
- 想在 UI/提示词层面定制 persona，优先走 `@deepseek-ai/dsh-persona` 插件或 agent preset，而非改文件

## 逃生舱 / 自愈

- **先验证不启动**：`dsh --profile <name> --dump-config`（离线渲染 patch 层）；`[]` 可禁用一个 patch 层；`disabled: true` 卸载 entry 不删
- **patch 重复崩溃**：`dev_fix_patch` 修复 `~/.dsh/profiles/*/cordis.patch.yml` 重复 loader entry id（备份原文件）
- **link 依赖悬空**：`dev_heal_links` 重建缺失的 node_modules junction
- **路由残留**：`dev_clear_routes` 清理 webserver 路由表残留（插件热重载残留）
- **卸载即净**：`dev_uninject_plugin` 卸载注入插件并写 disabled 条目防 include.refresh 加回
- 全部自检：`dev_self_test` 一键回归注入器全链路

## 编辑建议

- 写入前对照 config-catalog / 子系统文档验证；不确定就抓原文
- profile 定制改 `cordis.patch.yml`，**不要**改 `cordis.yml`；**id-targeted patch 替换整份 config**，必须重述要保留的所有字段
- 技能/插件/preset 定义优先用文件；保留用户未要求修改的已有字段与注释
- 改动后按"使配置生效"一节告知用户：patch/settings/技能多可热生效，bundle 列表改动需 `dsh plugin` 重调后重启
