---
name: customize-dsh
description: "仅当用户要求修改或扩展 DeepSeek Harness（DSH）本身时使用：profile/settings/cordis.patch.yml、bundles、技能注册与修复、Agent preset/Agent Team、MCP server、Cordis 插件/自定义工具、命令与系统提示，以及 DSH 启动或配置错误诊断。纯解释或只读状态查询、非 DSH 的插件/技能/MCP 工作不触发。"
license: MIT
compatibility: "Requires DeepSeek Harness (DSH); verify commands, configuration fields, and tool schemas against the installed version and active profile."
metadata:
  author: High-cla
---

# 定制 DeepSeek Harness — customize-dsh

DSH 配置和扩展操作指南。**所有命令、字段、默认值和 API 均有版本边界**；先识别用户实际环境，再根据任务加载对应参考，不要凭当前上游快照直接修改用户配置。

## 当前版本边界：0.2.2-rc.2（预发布）

截至 2026-11-13，核验的官方 `master` HEAD 为 [e8f7b93a344964de3dca1ace9e72b6e4d6de87cb](https://github.com/deepseek-ai/deepseek-harness/commit/e8f7b93a344964de3dca1ace9e72b6e4d6de87cb)，CLI 源码版本为 `0.2.2-rc.2`；官方 [v0.2.2-rc.2 release](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.2-rc.2) 标记为 Pre-release，不是 stable，也不代表用户安装版本。该快照要求 Node.js `>=24.9.0`；npm/source CLI 和显式 Node runtime SDK 需要核对运行时，打包 Desktop 与自带可执行文件的 SDK 使用随包运行时。升级前按 [Node 24 迁移说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/upgrade-guide/v0.2.1-rc.2/node-24/guide.zh.md)核对。

0.2.2-rc.1 及后续上游快照的关键边界：

- 工具执行器不再支持 `both` 混合呈现模式；只按当前 Agent scope 选择 native 或 PTC executor。旧 `dsh-agent-tool-presentation` 仍兼容但已弃用。
- `dsh-base` 组合关闭 `fs-observation-policy`；先读后写/编辑及外部修改检测不是默认强制门禁。`apply_patch` 的 `tool-fs.applyPatch` schema 默认值为 `false`，由具体 profile/preset 覆盖。当前上游 `packages/bundle/base/cordis.patch.yml` 的该行与生成 tool catalog 对 base 是否启用 `apply_patch` 的说明存在冲突；不能推断用户有效工具集，需查看 `dsh --profile <name> --dump-config`。沙箱和 Review 变更查看仍是独立机制。
- Plugin Market 的 `plugin_market` 是索引发现/只读工具；`update-available` 是索引状态，不等于该工具能升级。0.2.2-rc.1 的 Plugin Manager 已为符合条件的第三方 bundle 增加显式更新流程，并在部分失败路径尝试恢复旧版本；无 HMR 时可能要求重启，恢复也可能失败。
- Agent Team 通过标准 subagent `send_message` 向目标 inbox 发消息；成功表示目标 inbox 接受，不代表已回复。任务板变化本身不会唤醒空闲 Agent，也不会结束 `wait_agent`。
- 工具可按步骤条件启用。扩展工具注册/执行器的插件迁移时，必须对照 `when`、`ctx.tools.resolve()`、`toolSet` 与条件集合传递规则，不能只在 prompt 中过滤工具。

发布说明：[DSH 0.2.2-rc.2](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.2-rc.2)（Pre-release）。

## 开始前：确认实际运行环境

1. 确认实际 `dsh` 可执行文件、版本、安装来源、`DSH_HOME` 和活动 profile；多份安装并存时不要推断 PATH 指向。
2. 以安装版本匹配的 config catalog、package README、类型声明和源码为准。Context7 只用于定位资料；关键配置/行为回到官方原文核验。
3. 先读取目标文件与完整 entry 当前值。id-targeted patch 会整体替换该 entry 的 config，不是深度合并；编辑前保留所有需要继续生效的字段。
4. 先离线渲染/验证配置，再执行有副作用的写入；变更后确认实际 profile、工具目录和行为，不以写入成功或无报错代替验收。

## 按任务加载参考

| 任务 | 加载资料 |
|---|---|
| Settings、profile、patch、目录、热重载、权限、沙箱、MCP server、Plugin Market、文件策略和自愈 | [CONFIGURATION-REFERENCE.md](references/CONFIGURATION-REFERENCE.md) |
| 来源优先级、版本核验、官方字段/默认值和配置冲突 | [AUTHORITATIVE-SOURCES.md](references/AUTHORITATIVE-SOURCES.md) |
| Cordis 插件、bundle、双端插件、自定义工具、发布、安装与验证 | [PLUGIN-DEVELOPMENT.md](references/PLUGIN-DEVELOPMENT.md) |

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

## 插件与自定义工具

先区分 Skill（文件系统发现资源）、MCP server（外部服务）、纯 Cordis package、bundle（配置层）和 Web 双端插件。不要混用其他 harness 的插件格式。开始插件开发/发布时，加载 [PLUGIN-DEVELOPMENT.md](references/PLUGIN-DEVELOPMENT.md)；配置挂载与更新则同时核对 [CONFIGURATION-REFERENCE.md](references/CONFIGURATION-REFERENCE.md)。

## 完成前核对

- 目标版本、安装路径、profile 和文件位置均已确认。
- patch 语义、完整 config 替换、插件依赖和配置字段已按目标版本核验。
- 没有编辑 shipped package、错误的 legacy 文件或非活动 profile。
- 配置渲染/解析通过；需要重启时已明确说明；最终工具、会话和行为已实测。
- 权限拒绝、沙箱拒绝或审批拒绝没有被绕过；未确认的行为明确标为未验证。
