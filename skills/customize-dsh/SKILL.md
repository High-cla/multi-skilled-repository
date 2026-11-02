---
name: customize-dsh
description: 仅当用户要编辑或创建 DeepSeek Harness（DSH）自身配置或扩展时使用：settings.yaml（默认模型/权限预设/主题）、profiles/*/cordis.patch.yml 与 package.json（dsh.profile.bundles）、技能创作与修复（~/.dsh/skills、~/.agents/skills、项目 .dsh/skills，含技能不生效/嵌套目录问题）、agent preset（~/.dsh/.agent-presets）、MCP server（dsh-mcp-client）、cordis 插件包、自定义工具、slash 命令、DSH 启动失败或 patch 解析报错诊断。纯解释/查看类提问不需要；非 DSH 的插件、技能、MCP（如 opencode、codewhale、通用 MCP server 开发）不触发。用户说"改 DSH 配置""加技能""配 MCP""改默认模型""改权限预设""改某条目配置""改 profile""装/卸 DSH 插件""DSH 启动失败""patch 报错"时使用。
---

# 定制 DeepSeek Harness — customize-dsh

DSH 是"万物皆可插件"的宿主：配置严格校验，格式错误会导致启动失败（fail loud）。以下是常用定制面，但这是**摘要，非权威来源**。

## 权威参考

定制前先查权威资料，不要凭记忆猜字段：

- **配置目录（所有包的可配字段与默认值）**：<https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/config-catalog.md>（按 `@deepseek-ai/dsh-*` 包分节）
- **profile / patch / bundle 分层**：`packages/boot/app-boot/README.md#Profiles`、`apps/cli/reference/README.zh.md`
- **子系统文档（中文）**：<https://github.com/deepseek-ai/deepseek-harness/tree/master/docs/subsystems>（settings、skills、tools、permission-presets、system-prompt、approval、sandbox、agent-lifecycle）
- **组合与 HMR**：`docs/cordis-tutorial/06-composition-and-hmr.zh.md`
- **用户开发指南**：`docs/user/develop/basic/`（config、tool、publish）
- **cookbook**：`docs/cookbook/`（adding-a-tool、adding-a-package、extension-cookbook）
- **agent preset**：`packages/preset/agent-presets/README.zh.md`

若字段未在此 skill 说明或需确认精确形状，**抓取上述文档阅读原文**，不要猜测。

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
| 用户设置 | `$DSH_HOME/settings.yaml`（也可 .yml/.json） |
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
| agent preset | `$DSH_HOME/.agent-presets/<id>/`（agent.cordis.yml + 可选 preset.yml + plugins/） |

项目根目录 = 最近的含 `.git` 的祖先目录；找不到时用 cwd。技能本地提供方跳过 `$DSH_HOME` 的 `.system` 子目录。

## settings.yaml

顶级键 = 已注册 namespace 名。每个 namespace 解析为 `schema 默认值 → 注册方组合 base → 用户分节`。本机实例的真实形状：

```yaml
agent-presets:
  default: mcp-opt          # 默认 agent preset 名（影响此后创建的会话）
permission:
  defaultPreset: danger-full-access   # 权限预设：workspace-write | danger-full-access
ui-theme:
  preference: dark
ui-conversation:
  busyEnter: steer
agent-default-model:
  provider: opencode-go
  model: deepseek-v4-flash
  reasoningEffort: max
llm-pi-ai:
  providers:
    <provider-id>:
      models: [{ id, name, contextWindow, maxTokens }]
      apiKeyEnv: <环境变量名>
      # 自定义 provider 可加：displayName / api: openai-completions / baseURL
```

- 外部编辑经 `ctx.settings` 热发布；更新在写锁下先重读再原子写回，保留注释与未加载插件拥有的分节
- 启动时存在但**非法**的文档使插件加载失败；运行中不可读/不可解析的编辑只告警并保留最后可用分节
- provider 的 `apiKeyEnv` 指向环境变量而非明文密钥；凭据解析顺序：继承环境 → `.credentials.yaml` → 调用目录 .env → `$DSH_HOME/.env`

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
- 内置模板：`web`（base + web-app）、`headless`（base + headless）首次使用自动初始化；**其他 profile 名缺省会 fail loud**，需 `dsh plugin --profile <name> add <package>`
- 改 bundle 列表用 `dsh plugin --profile <name> add/remove <pkg>`（自动重调 `dsh.profile.bundles` 并安装），不要手改依赖后重启

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

**动手前先验证**：`dsh --profile <name> --dump-config`（离线渲染，不启动；`--dump-default-config` 只 dump 组合包各层）→ 确认行与覆盖无误再启动。

## Skills（技能创作）

本地 filesystem skill provider 扫描技能根目录的**直接**条目：目录包 `<name>/SKILL.md` 或扁平文件 `<name>.md`（不会递归发现任意深度的 `**/SKILL.md`）。注意 `ctx.skills` 本身是 provider registry，也可由远程或内嵌 provider 提供技能；以下路径与发现规则仅描述随附的本地 filesystem provider。

```markdown
---
name: my-skill
description: 一句话说明功能与触发条件。前置用户可能说的关键词或文件名。
disable-model-invocation: false   # 可选，true 则模型目录不显示
user-invocable: true              # 可选，默认 true
---

# My Skill

（正文：说明、示例、参考）
```

- `name` 必填，kebab-case（`^[a-z0-9]+(?:-[a-z0-9]+)*$`），与目录名一致
- `description` 必填：无效或缺失的 description 会使该 skill 被跳过。模型目录展示摘要而非完整正文；description 长度上限和解析规则以当前 skill-filesystem 配置/源码为准，不要依赖硬编码的 500 字符常量
- 重名裁决：rank 低者赢，再按提供方顺序、本地顺序；最近 scope 层条目直接压过全局层
- `skill` 工具加载后返回 `<skill_content>`、`<skill_resources>`、`<skill_instructions>`；资源（scripts/references/assets）按需解析，不枚举目录
- 本环境技能库在 `~/.agents/skills/`（user-agents 层），与 `customize-opencode`、`skill-creator` 等并列

## Agent presets

`$DSH_HOME/.agent-presets/<id>/` 下存放 preset：

```
agent.cordis.yml   # 插件行顶层列表（必填，preset 的组合）
preset.yml         # 可选展示元信息：只有 name/description；id=目录名、trust 来自根，不可写
plugins/           # preset 自带插件（相对路径从 preset 目录解析）
```

- 目录名必须是合法 preset id（`[a-z0-9][a-z0-9-]*`），否则跳过；损坏（YAML 无法解析/非具名插件行列表）以 `broken` 原因列出而非跳过
- 常驻挂载（standing mount）每个进程只一次；加入的会话共享一份工具/提示词/投影，插件按 Session/Agent 键控状态
- 视角解析顺序 `agent → preset → global`（近者遮蔽远者）
- `settings.yaml` 的 `agent-presets.default` 选择默认 preset；`roots`/`includeUserRoot` 可配置（缺省追加 `$DSH_HOME/.agent-presets` 为 user 根）
- **切换限制**：preset 只能在"尚未产生任何内容的空白会话"上切换（`recompose`）；默认值只影响此后创建的会话；preset 文件是输入而非持久化目标（loader 不写回）
- 创作是 copy-only：`ctx.agentPresets.copy()` 从现有 preset 整目录复制；`remove()` 只删 user 根下的 preset
- preset 的权限 = 它引用的插件的权限（trust 只用于展示 system/user 差异，不强制隔离）

## 插件（cordis package）与自定义工具

- **最小插件形态**（cookbook adding-a-tool）：

```ts
import { defineTool } from '@deepseek-ai/dsh-tools'
import type { Context } from '@deepseek-ai/cordis'

export const name = 'my-tool'
export const inject = ['tools']

export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'read_file',
    description: 'Read a file from disk.',
    parameters: {
      path: { type: 'string', required: true, description: 'Absolute path' },
      limit: { type: 'number' },
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args, exec) {
      return readFile(args.path, { encoding: 'utf8', signal: exec.signal })
    },
  }))
}
```

- `defineTool` 在 execute 前按 `ParameterSchemaSpec` 校验参数（类型/必填/字面量/oneOf）；`output.schema` 声明规范 JSON 值；抛异常即 `isError`；必须遵守 `exec.signal`；dispose 插件 fiber 即注销工具
- **Code Mode**：`tools` 插件 config 的 `mode: 'native' | 'code' | 'both'`（`both` 下模型可写 TS/Python 程序经 `run_code` 触达全部工具；`run_code` 是保留名）；工具错误类型 `ToolArgsError`/`ToolOutputError`/`ToolNotFoundError`
- 插件可配 Config 用 `@deepseek-ai/schemastery` 的 `Schema.object(...)` 导出 `Config`（不要导出普通对象）；**无效配置在加载时失败并给出明确错误**；约定：不同部署可能需要不同值的参数都必须定义为配置字段
- **挂载通道**：① `dsh.profile.bundles`（随 profile 启动）② `cordis.patch.yml` 的 insert（HMR 热生效）③ 运行时注入（super-injector dev_* 工具，免重启）④ 动态 cordis（`cordis_define`/`cordis_run`，会话级）
- 工具注册表按 scope 分层；MCP 工具名为 `mcp__<serverName>__<tool>`，实际可见范围取决于 MCP client 所挂载的注册作用域，不应一概描述为 GLOBAL

## MCP servers

通过 `cordis.patch.yml` 插入 `@deepseek-ai/dsh-mcp-client` 行（见"Profiles 与 patch 层"示例）。当前上游默认值以 [MCP client README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.zh.md) 和生成的 config catalog 为准。关键配置键：

- `serverName`：桥接名，工具前缀 `mcp__<serverName>__<工具原始名>`；须匹配 `[A-Za-z0-9_-]{1,32}`，在同一注册作用域内唯一；独立 agent scope 可隔离复用
- `transport`：`stdio` | `streamable-http`（官方只有这两种，没有 `remote`）
- `command` + `args`：stdio 模式的可执行与参数。生产部署优先使用可预测的可执行路径并固定包版本；`npx` 可能触发包解析/网络安装，不应在未评估可重复性时作为生产默认。
- `env`：传给服务器的环境变量；`cwd`：工作目录（常用 `!!js process.cwd()`）
- `toolCallTimeoutMs`：每次 MCP `tools/call` 或资源请求的超时，当前默认 **60000 ms**；只有确认目标服务器确实需要更长时间时才提高。
- `failOnStartupError`：初始连接或工具同步失败时是否拒绝插件激活，当前默认 **false**；默认情况下 DSH 可继续启动，但该服务器工具不会出现并会记录错误。若服务为关键依赖，再显式设为 `true`。
- 远程（streamable-http）：`url` + 可选 `headers`

## 权限与沙箱

权限预设把两个 knob 捆绑成具名预设：

| 预设 | sandbox/mode | approval/policy |
|---|---|---|
| `workspace-write` | `workspace-write` | `ask` |
| `danger-full-access` | `danger-full-access` | `never` |

- `custom` 是保留名（派生的"非预设"状态，不可切换）
- `SandboxMode`：`read-only`（拒绝写入）| `workspace-write`（工作区根+后端临时区）| `danger-full-access`（绕过隔离，直接 spawn 原始 argv）
- `ApprovalPolicy`：`ask`（委托应答者链，无应答 fail-closed 为 unavailable）| `never`（确定性 `rejected`，不分发应答者）
- `settings.yaml` 的 `permission.defaultPreset` 设置默认；新会话进程后备默认 `workspace-write`（`DSH_PERMISSION_MODE` 可改）
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
