---
name: customize-dsh
description: 仅当用户要编辑或创建 DeepSeek Harness（DSH）自身配置或扩展时使用：旧版 settings.yaml 迁移（默认模型/权限预设/主题）、profiles/*/cordis.patch.yml 与 package.json（dsh.profile.bundles）、技能创作与修复（~/.dsh/skills、~/.agents/skills、项目 .dsh/skills，含技能不生效/嵌套目录问题）、Agent preset（@deepseek-ai/dsh-agent-preset；旧式 ~/.dsh/.agent-presets 迁移）、MCP server（dsh-mcp-client）、cordis 插件包、自定义工具、slash 命令、DSH 启动失败或 patch 解析报错诊断。纯解释/查看类提问不需要；非 DSH 的插件、技能、MCP（如 opencode、codewhale、通用 MCP server 开发）不触发。用户说"改 DSH 配置""加技能""配 MCP""改默认模型""改权限预设""改某条目配置""改 profile""装/卸 DSH 插件""DSH 启动失败""patch 报错"时使用。
---

# 定制 DeepSeek Harness — customize-dsh

DSH 是"万物皆可插件"的宿主：配置严格校验，格式错误会导致启动失败（fail loud）。以下是常用定制面，但这是**摘要，非权威来源**。

## 当前版本边界：0.2.2-rc.1（预发布）

截至 2026-11-08，核验的官方 `master` HEAD 为 [fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159](https://github.com/deepseek-ai/deepseek-harness/commit/fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159)，源码版本为 `0.2.2-rc.1`；这是 RC 预发布快照，不代表用户安装的 stable 版本。该快照要求 Node.js `>=24.9.0`；npm/source CLI 和显式 Node runtime SDK 需要核对运行时，打包 Desktop 与自带可执行文件的 SDK 使用随包运行时。升级前按 [Node 24 迁移说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/upgrade-guide/v0.2.1-rc.2/node-24/guide.zh.md)核对。

0.2.2-rc.1 及后续上游快照的关键边界：

- 工具执行器不再支持 `both` 混合呈现模式；只按当前 Agent scope 选择 native 或 PTC executor。旧 `dsh-agent-tool-presentation` 仍兼容但已弃用。
- `dsh-base` 组合关闭 `fs-observation-policy`；先读后写/编辑及外部修改检测不是默认强制门禁。`apply_patch` 的 `tool-fs.applyPatch` schema 默认值为 `false`，由具体 profile/preset 覆盖。当前上游 `packages/bundle/base/cordis.patch.yml` 的该行与生成 tool catalog 对 base 是否启用 `apply_patch` 的说明存在冲突；不能推断用户有效工具集，需查看 `dsh --profile <name> --dump-config`。沙箱和 Review 变更查看仍是独立机制。
- Plugin Market 的 `plugin_market` 是索引发现/只读工具；`update-available` 是索引状态，不等于该工具能升级。0.2.2-rc.1 的 Plugin Manager 已为符合条件的第三方 bundle 增加显式更新流程，并在部分失败路径尝试恢复旧版本；无 HMR 时可能要求重启，恢复也可能失败。
- Agent Team 通过标准 subagent `send_message` 向目标 inbox 发消息；成功表示目标 inbox 接受，不代表已回复。任务板变化本身不会唤醒空闲 Agent，也不会结束 `wait_agent`。
- 工具可按步骤条件启用。扩展工具注册/执行器的插件迁移时，必须对照 `when`、`ctx.tools.resolve()`、`toolSet` 与条件集合传递规则，不能只在 prompt 中过滤工具。

发布说明：[DSH 0.2.2-rc.1](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.2-rc.1)。

## 权威参考

定制前先查权威资料，不要凭记忆猜字段：

- **配置目录（所有包的可配字段与默认值）**：<https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/config-catalog.md>（按 `@deepseek-ai/dsh-*` 包分节）
- **权威来源与决策索引（建议先读对应摘要）**：[`references/AUTHORITATIVE-SOURCES.md`](references/AUTHORITATIVE-SOURCES.md)，先按“决策摘要”将任务映射到首选资料，再按证据优先级核实目标版本、有效 profile 和运行时行为；下方按主题列出官方文档、源码与版本差异。
- **插件开发/打包/发布专项参考**：[`references/PLUGIN-DEVELOPMENT.md`](references/PLUGIN-DEVELOPMENT.md)。先看开头“快速决策摘要”选择 Skill、MCP、纯 Cordis、Bundle、Web 双端或 Profile，再按任务路线阅读对应章节；涉及 Git/npm 安装、发布与兼容性验证时仍须回查用户实际安装版本。
- **profile / patch / bundle 分层**：`packages/boot/app-boot/README.md#Profiles`、`apps/cli/reference/README.zh.md`
- **CLI 当前行为**：[`apps/cli/reference/README.zh.md`](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/reference/README.zh.md)；重点核对 `--from-default-profile`、`--dump-config-schema` 和 `dsh plugin` 的 profile 初始化/依赖管理语义。注意 `--from-default-profile` 会用模板全新副本替换目标 profile，连同已安装依赖与用户 patch 一起删除；执行前先备份整个 `$DSH_HOME/profiles/<name>/`。
- **工具执行器迁移**：[`tool-executor-plugins` 升级指南](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/upgrade-guide/v0.2.1-rc.2/tool-executor-plugins/guide.zh.md)，用于确认 `dsh-tools` 的旧执行配置如何迁移到 native/PTC executor；0.2.2-rc.1 还移除了 `both` 混合呈现模式。
- **条件工具迁移**：[`conditional-tools` 升级指南](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/upgrade-guide/v0.2.1-rc.2/conditional-tools/guide.zh.md)，涉及 `register(..., { when })`、`ctx.tools.resolve()`、`toolSet` 和自定义执行器时必须阅读。
- **Plugin Manager 更新**：[`plugin-manager` README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/boot/plugin-manager/README.zh.md)，核对 `updateBundle()` 的资格、精确版本、HMR 与恢复语义；不要与只读 `plugin_market` 混淆。
- **文件修改默认策略**：[`文件策略默认关闭迁移说明`](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/upgrade-guide/v0.2.2-alpha.2/fs-observation-policy-default-off/guide.zh.md) 与 [`tool-fs README`](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/fs/tool-fs/README.zh.md)；按用户的实际 profile/preset 核验是否启用观察策略与 `apply_patch`。
- **插件显示元数据**：[`Host plugin metadata reference`](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/preset/agent-preset/skills/cordis-plugin-development/references/host-plugin.md)，包含 locale、icon、subpath 插件导出边界。
- **Agent Teams**：[`agent-team` 子系统](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/agent-team.zh.md)、[`dsh-agent-team`](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/team/agent-team/README.zh.md)、[`dsh-tool-agent-team`](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/team/tool-agent-team/README.zh.md)。
- **Plugin Market**：[`plugin-market` README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/boot/plugin-market/README.zh.md) 与 [`tool-catalog.zh.md`](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/tool-catalog.zh.md)；市场索引是可配置的第三方内容，不等同于已签名/审核的官方插件目录。
- **子系统文档（中文）**：<https://github.com/deepseek-ai/deepseek-harness/tree/master/docs/subsystems>（settings、skills、tools、permission-presets、system-prompt、approval、sandbox、agent-lifecycle）
- **组合与 HMR**：`docs/cordis-tutorial/06-composition-and-hmr.zh.md`
- **用户开发指南**：`docs/user/develop/basic/`（config、tool、publish）
- **cookbook**：`docs/cookbook/`（adding-a-tool、adding-a-package、extension-cookbook）
- **agent preset**：`packages/preset/agent-preset/README.zh.md`

若字段未在此 skill 说明或需确认精确形状，**抓取上述文档阅读原文**，不要猜测。Context7 当前可用时，先 resolve `/deepseek-ai/deepseek-harness`，再针对单一配置主题查询；仍需回到对应版本官方原始文档、生成 config catalog 和源码核对。

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

## Skills（技能创作）

本地 filesystem skill provider 扫描技能根目录的**直接**条目：目录包 `<name>/SKILL.md` 或扁平文件 `<name>.md`（不会递归发现任意深度的 `**/SKILL.md`）。注意 `ctx.skills` 本身是 provider registry，也可由远程或内嵌 provider 提供技能；以下路径与发现规则仅描述随附的本地 filesystem provider。

```markdown
---
name: my-skill
description: 一句话说明功能与触发条件。前置用户可能说的关键词或文件名。
disable-model-invocation: false   # 可选，true 则模型目录不显示
user-invocable: true              # 可选，默认 true
whenToUse: "可选：补充模型判断何时应选择此技能的提示"
metadata: {}                      # 可选：技能元数据
---

# My Skill

（正文：说明、示例、参考）
```

），与目录名一致
- `description` 必填：无效或缺失的 description 会使该 skill 被跳过。模型目录展示摘要而非完整正文；description 长度上限和解析规则以当前 skill-filesystem 配置/源码为准，不要依赖硬编码的 500 字符常量。
- `whenToUse`、`metadata` 是当前 filesystem provider 支持的可选 frontmatter 字段；`disable-model-invocation` 与 `user-invocable` 必须使用可解析的布尔值（或 provider 明确接受的布尔字符串），非法值可能使整个技能被跳过。
- 当前 provider 可识别 symlink 目录包与扁平文件；仍只在每个技能根目录的直接子项中查找 `<name>/SKILL.md` 或 `<name>.md`，不会递归遍历任意深度。
- 重名裁决：rank 低者赢，再按提供方顺序、本地顺序；最近 scope 层条目直接压过全局层
- `skill` 工具加载后返回 `<skill_content>`、`<skill_resources>`、`<skill_instructions>`；资源（scripts/references/assets）按需解析，不枚举目录
- 本环境技能库在 `~/.agents/skills/`（user-agents 层），与 `customize-opencode`、`skill-creator` 等并列

## Agent presets

先区分两种容易混淆的概念：

1. **当前 Cordis Agent preset**：由 `@deepseek-ai/dsh-agent-preset` 声明，通常作为 profile composition 中的一条插件 entry。其 `config.id` 是会话保存的 preset identity，entry 自身的 `id` 是 Loader patch 定位键；`config.plugins` 是 Agent 子插件列表。修改声明只影响之后创建的 Agent，不会自动改写已有会话。
2. **旧式目录 preset**：`$DSH_HOME/.agent-presets/<id>/` 下的 `preset.yml` + `agent.cordis.yml` 是旧格式。当前上游已不再读取这种目录；不要把旧目录当成当前 preset 的生效来源，也不要只修改旧目录来尝试修复 preset。

当前 Cordis 声明形态（字段以已安装版本的 config catalog 为准）：

```yaml
- id: agent-preset-registry
  name: '@deepseek-ai/dsh-agent-preset-registry'
  config:
    default: standard
- id: preset-standard
  name: '@deepseek-ai/dsh-agent-preset'
  config:
    id: standard
    plugins:
      - id: child-tool
        name: '@deepseek-ai/example-plugin'
        config: {}
```

- entry 的 `id` 与 `config.id` 不是同一个标识；不要互换。
- `plugins` 是 Cordis 子 entry 列表，子插件仍受 Loader dependency、schema、scope 和 lifecycle 规则约束。
- 随包的 `@deepseek-ai/dsh-agent-preset` README 说明声明会提前加载，变更影响随后创建的 Agent；已有 Agent composition 保持稳定。
- `@deepseek-ai/dsh-agent-preset-registry` 的 `config.default` 是部署默认 preset；其 volatile 字段 `selectedDefault` 保存用户默认值，新会话在未显式指定 preset 时优先使用用户默认值。不要沿用已废弃的 `modeSelectionEnabled` 配置，也不要把默认值变更解释为现有会话自动切换。
- 如需新增或复制 preset，优先使用当前 Web UI/Agent Preset 管理能力；若通过运行时 API 或工具操作，先从当前环境的 API/工具 schema 确认可用方法（例如 `agentPresets` service），不要假设旧版 `copy/remove` 或文件系统布局仍可用。
- preset plugin row 的配置 patch 遵循普通 Cordis patch 语义：按 entry id 定位，整份替换 config 时重述完整 `plugins` 列表；不要直接编辑随包安装目录中的 shipped composition。

## Agent Teams（共享任务板；0.2.2-rc.2 行为）

Agent Teams 是叠加在 subagent 树上的持久化共享任务板，不是独立的成员/消息运行时，也不是 worktree/进程隔离机制。0.2.2-rc.2 的核心边界是：**subagent 负责创建、发现、通信和中断；Team 只负责根 Session 的模式选择与共享任务板。**

- **包分工**：@deepseek-ai/dsh-agent-team 提供 Team 服务与任务状态持久化；@deepseek-ai/dsh-tool-agent-team 提供 team_task_create/list/get/update 四个模型工具。完整组合还需标准 subagent 服务、spawn backend、@deepseek-ai/dsh-tool-subagent 与 @deepseek-ai/dsh-tool-subagent-control；不要把 Team 包当成创建/通信/中断工具的提供者。
- **按 Session 启用**：新 Session（包括普通 fork）默认关闭 Team；根 Session 可在模型与推理等级菜单中切换「使用智能体团队」，选择控制整棵子代理树。关闭 Team 只隐藏后续步骤中的任务工具和 Team 指导，不删除任务或子代理。选择持久化并在重启后保留；没有保存选择的历史任务板仍按历史兼容规则视为开启。
- **默认值**：defaultEnabled: true 只为尚无已保存选择的新根 Session 初始化开启状态；已有选择优先，恢复 Session 不应用默认值。maxTasks 默认 256。标准 base 组合默认 defaultEnabled: false。
- **Team 专属成员运行时已移除**：不要再使用 spawn_teammate、Team 专属 send_message/list_agents/interrupt_agent、ctx.agentTeams 的创建/消息/中断/成员关系 API。使用标准 subagent（新上下文）或 subagent_fork（继承已完成历史）创建成员；标准 subagent control 工具负责 list_agents、send_message、interrupt_agent 与 wait_agent。历史 Team roster/mailbox 记录仍可解码，但不再授予成员权限，也不会重新投递旧待处理消息。
- **配置迁移**：agent-team 不再接受 maxMembers、maxMessageBytes、disposalTimeoutMs；tool-agent-team 不再接受 interrupt、freshProvider、forkProvider。将 interrupt: false 移到 tool-subagent-control；删除其他已移除键及仅为 Team 禁用标准 subagent 工具的 patch。字段仍须按目标版本 config catalog 核实。
- **共享工作区限制**：Team 成员共享同一 checkout；writeScopes 只是规范化路径前缀提示，用于提示 in-progress 任务的重叠，不是锁、写权限边界或隔离。不会自动释放任务 owner，也不会为 teammate 创建独立 worktree。
- **通信与等待**：任务 owner 以 Session id 为授权身份，展示层可附带不可变 agent 名称。任务变化不会结束 wait_agent、不会给 inbox 投递消息，也不会启动空闲 Agent。send_message 成功只表示 inbox 接受（返回 message id），不代表收到回复；需要成员继续行动时显式发消息。
- **Web projection**：agentTeam Session projection 为 Web 发布持久 roster/task 视图；实时运行状态由 Session 状态叠加。projection 持久记录失败时会暴露 failure 并保留最后有效视图。不要把旧版 Web roster/mailbox 投影或历史成员字段当作当前权限来源。

**版本迁移注意**：从 Team 专属 API 迁移时，先读 [Agent Team subagent migration guide](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/upgrade-guide/v0.2.1-rc.2/agent-team-subagents/guide.zh.md) 和 [Session Team mode guide](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/upgrade-guide/v0.2.1-rc.2/session-team-mode/guide.zh.md)。两份指南描述不同迁移切面；工具参数以目标版本当前 tool-subagent-control README / 生成工具目录为准。旧指南中的参数名称与当前 README 若不一致，必须查目标版本 schema，不要猜。

详见 [Agent Teams 子系统](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/agent-team.zh.md)、[Team service README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/team/agent-team/README.zh.md)、[Team tools README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/team/tool-agent-team/README.zh.md) 与 [subagent control README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/tool-subagent-control/README.zh.md)。

## 插件（cordis package）与自定义工具

插件开发与打包不止一种形态：**纯 Cordis 包**是单个功能模块；**bundle**通过 `dsh.bundle.patch` 分发一组配置层；需要 Web UI 时还可增加 `dsh.client` 浏览器端。Skill 是文件系统发现资源，MCP server 是通过官方 MCP client 配置的外部服务，二者都不是 npm bundle。不要把 Claude Code 的 `.claude-plugin/plugin.json` 或社区市场自定义清单当成 DSH 核心规范。

**开发前先读** [`references/PLUGIN-DEVELOPMENT.md`](references/PLUGIN-DEVELOPMENT.md)：它包含官方外部插件 manifest、Cordis entry、tool schema、双端模块、Git prepare 信任边界、发布和真实运行验证流程。不要把 DSH monorepo 内部 package checklist 当成外部插件模板。

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
- **工具执行器（0.2.1-rc.2 及后续版本）**：`@deepseek-ai/dsh-tools` 负责工具注册，不再接受旧的 `mode` 或 `maxParallelSubCalls` Config 字段。原生执行挂载 `@deepseek-ai/dsh-tool-executor-native`；PTC 执行挂载 `@deepseek-ai/dsh-tool-executor-ptc`。随附 profile 从 base 继承原生执行器；自定义组合必须在目标 scope 挂载一个执行器，同一 scope 不应并挂两个执行器。
- **PTC 执行**：需要可用的 `ctx.ptcRuntime` 及对应语言 SDK renderer；TypeScript runtime 可由 `@deepseek-ai/dsh-ptc-runtime-node` 提供。`maxParallelSubCalls` 移至 PTC executor 配置（当前 README 默认 `10`），`maxSubCallsPerMinute` 默认 `1024`；`agent-loop.maxParallelToolCalls` 是另一项批次并发设置，默认 `10`。PTC 的模型调用入口是保留工具 `run_code`。
- **迁移边界**：`@deepseek-ai/dsh-agent-tool-presentation` 旧选择器仍兼容但已弃用，新配置直接挂载 native/PTC executor；Web、headless、SDK 不再读取 `DSH_TOOLS_MODE`。旧 `dsh-tools` 的 `mode`/`maxParallelSubCalls` 配置在新版本会加载失败，必须按[官方迁移指南](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/upgrade-guide/v0.2.1-rc.2/tool-executor-plugins/guide.zh.md)调整。
- 插件可配 Config 用 `@deepseek-ai/schemastery` 的 `Schema.object(...)` 导出 `Config`（不要导出普通对象）；**无效配置在加载时失败并给出明确错误**；约定：不同部署可能需要不同值的参数都必须定义为配置字段
- **挂载通道**：① `dsh.profile.bundles`（bundle 配置层，是否重载取决于 profile/HMR）② `cordis.patch.yml` 的 insert（是否热生效取决于组合树是否启用 HMR；不能一概承诺热更新）③ 运行时注入（仅在相应 super-injector 工具真实存在且权限允许时）④ 动态 Cordis（仅在相应工具/服务真实注册时）。不要把开发注入器当作默认 DSH 能力。
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
