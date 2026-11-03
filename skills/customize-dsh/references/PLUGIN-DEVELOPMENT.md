# DSH 插件开发与发布参考

> 本文面向 **在 DeepSeek Harness（DSH）中开发、安装、验证和发布扩展的外部作者**。它是工作指南，不替代 DSH 某个具体版本的官方配置目录、类型定义或实现。DSH 仍处于快速演进阶段；每次开发都要先确认目标 DSH 版本，并按本文“权威资料”回查当前版本。

> **上游核验快照（2026-11-03）**：本次核对的 `deepseek-ai/deepseek-harness` `master` HEAD 为 [`ce7073d51254c26cd63b22a60835b8f948deb447`](https://github.com/deepseek-ai/deepseek-harness/commit/ce7073d51254c26cd63b22a60835b8f948deb447)（提交时间 2026-10-29 16:13:15 UTC）。这是文档检索时的源码快照，不是 DSH 发布版本号，也不代表所有已安装版本；实际开发仍须以用户安装版本的 tag/commit、config catalog 和运行时测试为准。

## 1. 先分清五种装配单位

DSH 中几个名字相似的对象不是同一层：

| 名称 | 责任 | 典型位置 / 声明 |
|---|---|---|
| Cordis plugin | 一个功能单元：注册服务、工具、事件监听器、命令、提示词或生命周期副作用 | 一个可被 Loader 加载的模块，导出 `name` / `inject` / `apply`，或受支持的对象/类插件 |
| Bundle（组合包） | 插件的**分发与配置层**：随包提供一组可复用的 Loader patch rows | npm 包 `package.json` 的 `dsh.bundle.patch` |
| Profile | 一套可启动的宿主组合：按顺序安装/组合 bundles，并叠加用户 patch | `$DSH_HOME/profiles/<name>/`；`dsh.profile.bundles` |
| Agent preset | 某个 Agent 会话内可见的工具、人设、指令与技能组合 | 当前 `@deepseek-ai/dsh-agent-preset` Cordis entry；不要与旧目录 preset 混淆 |
| Skill | 按需加载的说明、工作流与辅助资源，不是运行时代码插件 | 文件系统技能根目录中的 `<name>/SKILL.md` 或 `<name>.md` |

**插件（plugin）是功能单位；bundle 是分发配置层；profile 是启动组合。** 不能把安装一个 npm 依赖、把它加入 bundle 层、把一条 Cordis entry 挂载成功当作同一个状态。

### 插件形态选择

| 用户实际需求 | 应采用的 DSH 机制 | 是否需要 bundle |
|---|---|---|
| 只增加一个 Node 服务、工具、命令或事件监听器 | 纯 Cordis 包；安装为 profile 依赖，再在 profile 的 `cordis.patch.yml` 插入一条 entry | 否 |
| 一个包需要随包分发多条 entry、默认配置或 disabled rows | Bundle 包；声明 `dsh.bundle.patch` | 是 |
| 除 Node 逻辑外还要给 DSH Web UI 添加设置页、槽位或工具结果视图 | Node 插件 + 浏览器 client half；声明 `dsh.client` 并导出 `./client`；是否另需 bundle 取决于是否要分发组合层 | 可选 |
| 只提供提示词、操作规范和文件资源 | Skill 文件系统发现机制 | 否 |
| 接入外部 MCP 服务 | 通过上游 `@deepseek-ai/dsh-mcp-client` 在 patch 层配置服务器 | 否；MCP server 本身不是 DSH 插件清单 |
| 提供独立可启动应用/profile | Profile 是消费方组合；通常配合一个或多个 bundle | Profile 不等于 bundle |

不要仅因一个仓库名包含 plugin 就假设它属于官方插件机制。当前核心开发契约以官方 Cordis 插件、bundle 与 client module 文档为准；第三方市场/索引格式、仓库专属清单（例如历史上出现过的 `.dsh-plugin`）不是 DSH 核心 package manifest 的替代品。Claude Code 的 `.claude-plugin/plugin.json` 也不是 DSH 清单。

## 2. 最小 Cordis 插件模块

官方“第一个插件”教程定义的最小函数式插件形态如下：

~~~ts
import type { Context } from '@deepseek-ai/cordis'

export const name = 'hello-plugin'

export function apply(ctx: Context) {
  console.log('[hello-plugin] loaded')
}
~~~

当插件需要其他服务时，通过 `inject` 声明依赖。Cordis 会在依赖服务就绪后执行 `apply`；不要仅凭一个服务名猜测其 API，须从对应 package README、subsystem 文档或当前版本类型定义确认。

~~~ts
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'hello-tool'
export const inject = ['tools']

export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'hello',
    description: 'Return a greeting for a person.',
    parameters: {
      name: {
        type: 'string',
        required: true,
        description: 'Person to greet',
      },
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args) {
      return `Hello, ${args.name}!`
    },
  }))
}
~~~

### Config schema

如需用户可配置字段，导出 Schemastery schema（不要把普通对象冒充运行时 schema）。TypeScript 类型与运行时 schema 应保持一致：

~~~ts
import type { Context } from '@deepseek-ai/cordis'
import Schema from '@deepseek-ai/schemastery'

export const name = 'configurable-greeting'

export interface Config {
  greeting: string
  maxRetries: number
}

export const Config: Schema<Config> = Schema.object({
  greeting: Schema.string().default('Hello'),
  maxRetries: Schema.number().default(3),
})

export function apply(ctx: Context, config: Config) {
  // Consume the validated config. Inject only services confirmed by this DSH version.
  void ctx
  console.log(config.greeting, config.maxRetries)
}
~~~

schema 约束在加载时校验，缺少必填项或类型错误可能导致插件激活失败，因此要提供有意义的默认值、边界和错误信息。

### 生命周期与清理

- 通过 Cordis context 注册的监听器、工具等资源，随其所属插件 fiber dispose 自动清理。
- 创建了框架未托管的资源（子进程、socket、文件 watcher、定时器等）时，使用当前版本支持的 `ctx.effect` 注册清理回调；清理必须可重复执行且不会泄漏。
- 对耗时任务传递并监听 `AbortSignal`；停止/卸载时停止新工作、取消在途工作，再释放资源。
- 插件不要在模块 import 时就启动不可撤销的后台工作；将副作用放在 `apply` / 明确的生命周期回调中。
- 不要绕过 DSH 的审批、沙箱、工具注册表或 scope 体系，直接建立一个能力更大的旁路。

## 3. 工具插件的模型可见契约

以官方 [工具编写参考](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/adding-a-tool.zh.md) 为准：

1. `defineTool` 的 parameters 描述参数；框架会在执行前校验可表达的类型、必填项、literal/union 与嵌套结构。无法由 schema 表达的跨字段约束仍需在 execute 中检查。
2. `output.schema` 描述工具返回的规范 JSON 值；`execute` 返回这个值，不要直接返回 MCP 内容块、UI React 节点或要求调用方从自然语言解析的文本协议。
3. `output.render` 再把规范值转换成模型可读的内容块。渲染与执行返回值是两层职责。
4. 处理文件、网络或子进程时，遵循 `exec.signal`；尊重取消，不要吞掉取消或在调用结束后继续后台执行。
5. 运行时异常或无效输出会以工具错误路径处理。成功返回值即使表示业务失败，也应采用稳定的结构化结果，而不是伪装成执行异常。
6. 原始 JSON Schema 注册与 `defineTool` 类型 DSL 不同；直接注册原始定义时，插件作者自己承担对应的输入验证责任。

不要自行假设工具在全局可见。工具注册表有 scope；宿主工具、Agent 子树工具与 MCP 工具的可见范围由当前 composition 决定。

## 4. 纯 Cordis 包：安装依赖 + profile 显式插入

纯 Cordis 包适用于一个可加载功能模块，但不需要把多条配置层随包发布的情况。它可以是本地目录、Git 包或 npm 包。安装依赖本身不保证插件 entry 已经加载；还需要 profile 的 patch row：

~~~yaml
- insert:
    - id: hello-plugin
      name: dsh-hello-plugin
~~~

模块路径必须能从 profile 的 Node 解析上下文解析到。用当前 profile 的命令进行安装，不要把全局 npm 安装误当成 profile 安装：

~~~sh
dsh plugin --profile <profile> add ./hello-plugin
dsh --profile <profile> --dump-config
~~~

对纯 Cordis 包，profile 自己维护这条 entry；对 bundle 包，bundle 的 patch 提供这些 rows。不要为相同能力重复挂载两份 entry，也不要改写 DSH 随包提供的安装目录。

## 5. Bundle 包：用 dsh.bundle.patch 发布配置层

官方外部发布教程规定：bundle 是附带配置层的 npm 包，profile 是消费这个 bundle 的可启动组合。最小 bundle 示例：

~~~text
hello-plugin/
├── package.json
├── cordis.patch.yml
└── index.js
~~~

~~~json
{
  "name": "dsh-hello-plugin",
  "version": "0.1.0",
  "type": "module",
  "main": "index.js",
  "files": ["index.js", "cordis.patch.yml"],
  "engines": {
    "dsh": ">=0.2.0 <0.3.0"
  },
  "dsh": {
    "bundle": {
      "patch": "./cordis.patch.yml"
    }
  }
}
~~~

~~~js
export const name = 'hello-plugin'

export function apply() {
  console.log('[hello-plugin] loaded')
}
~~~

~~~yaml
- insert:
    - id: hello
      name: dsh-hello-plugin
~~~

注意：

- `dsh.bundle.patch` 可声明单个相对文件路径，也可声明一个有序文件路径数组；多个 patch 文件按声明顺序应用。
- `cordis.patch.yml` 是 patch 条目数组。bundle 中的 plugin row 用已安装包名引用代码，不是 bundle 根目录下的随意相对路径。
- `dsh.profile.bundles` 属于消费方 profile manifest；不要把它放进 bundle manifest。通过 `dsh plugin --profile <name> add <package>` 安装 bundle，CLI 会按官方流程维护 profile 的依赖与 bundle 列表。
- 未声明 `dsh.bundle` 的包可以作为普通依赖安装，但不会因此自动贡献 bundle layer。
- 发布前使用 `dsh --profile <name> --dump-config` 验证最终层栈；确认出现预期的 bundle 层、插件 entry id 和有效配置，再启动应用。
- bundle patch 仍遵守普通 Cordis patch 方言：按 id 命中时 config 是整体替换，不是深度合并；需要覆盖 entry 时保留所有必需配置字段。

## 6. Web 双端插件：Node half + dsh.client

只有在确实要扩展 DSH Web UI 时才增加 client half。官方 Client Modules 契约的要点：

- Node half 是普通 Cordis plugin，由 Host Loader 加载。
- 浏览器 half 通过 `package.json` 的 `exports["./client"]` 暴露构建产物，并声明 `dsh.client.platform` 为 `web`。
- `dsh.client.inject` 声明它依赖的 client module package edges；需要非 baseline 外部模块时，再按当前 client module manifest schema 使用 `dsh.client.external`。
- Web host 扫描已启用的 Loader entries，按声明把构建好的 client bundle 暴露给模块加载器；缺少 bundle、错误的 exports 或无效 manifest 可能在激活时失败。
- 浏览器代码不要导入 Node-only API、秘密凭据或 Host 内部实现。Host 与 client 的跨边界数据应使用稳定、可验证的 wire schema / Remote API，而不是直接共享运行时对象。
- Client 插件应遵循 slots、stores、inject 与 renderer 的官方扩展点，不要篡改宿主页面内部 DOM 或假设某个组件层级永久稳定。

manifest 示意（`exports` 中的根入口按包实际情况保留；下面只展示 client 必需的声明）：

~~~json
{
  "exports": {
    ".": {
      "types": "./lib/types/index.d.ts",
      "default": "./lib/index.js"
    },
    "./client": {
      "types": "./lib/types/client/index.d.ts",
      "default": "./lib/client.js"
    }
  },
  "dsh": {
    "client": {
      "platform": "web",
      "inject": ["@deepseek-ai/dsh-client-ui-settings"]
    }
  }
}
~~~

`dsh.client.inject` 的包名和 `external` 条目必须来自当前版本真实存在的模块/manifest；不要照抄一个项目的 client 依赖名到另一个版本。Client entrypoint 是公开浏览器 API 边界；官方 monorepo 的 `packages/client/AGENTS.md` 还有更严格的内部导出纪律，这些仓库内约束不应被误称为所有外部包的通用清单。

## 7. 依赖、兼容性与发布纪律

### 版本兼容

- 给外部 bundle 声明适当的 `engines.dsh` SemVer 范围；官方启动/安装流程会检查兼容性。范围应覆盖你实际验证的版本，不要写一个未经测试的宽泛范围。
- 复用 DSH 宿主中的 Cordis / DSH 运行时包时，按官方外部发布指南把需要共享单例的包声明为 `peerDependencies`，并为本地类型检查/测试按需配置 `devDependencies`。不要把需要和宿主共享身份的 Cordis 包打进自己的 bundle，否则可能出现重复 Context / service 实例。
- 独立的第三方库放在 `dependencies`。不要把 DSH monorepo 的内部包清单、内部版本号与 workspace 设置原样复制到社区插件；官方 `adding-a-package` 指南是上游仓库内部新建 package 的要求，不是外部作者模板。
- 确保 npm `files` 包含运行时入口、声明的 patch、client bundle、需要提供的资源和许可证；用 `pnpm pack` 检查实际 tarball，而不是只看本地目录。
- README 要明确功能、所需 DSH/Node 版本、安装命令、配置字段、权限影响、已知限制、卸载/回滚方式和测试证据。

### Git 安装与 prepare 风险

官方发布指南明确：Git 安装得到的是源码；不会自动替作者执行任意 `build` 脚本。TypeScript 插件需要可用的构建产物时，应提供自包含的 `prepare` 构建步骤，或直接分发预构建 npm/tarball。

pnpm 10 对 Git 依赖的构建脚本需要显式授权（通常通过 profile 内 pnpm 配置的 `allowBuilds` 项）。这不是无害开关：它允许依赖在安装阶段以当前用户权限执行代码，通常不处于 Agent 的沙箱内。处理原则：

1. 先审查仓库脚本、依赖和 lockfile，确认来源可信。
2. 优先锁定 Git commit SHA，而不是长期追踪会变化的 branch。
3. 只对确实需要且已审查的包授权 prepare/build；不要一次性开放未知依赖的构建脚本。
4. 能提供构建完成的 npm 包或 tarball 时，优先选择不需要安装时执行构建脚本的发布路径。

## 8. 开发验证：安装成功不等于功能正确

按这个顺序验证，并记录 DSH 版本、Node 版本、profile 与提交 SHA：

1. **版本与路径**：确认当前 `dsh` 可执行文件、`dsh --version`、Node 版本、目标 profile；不要在一台机器上混用多个 DSH 安装。
2. **依赖和 manifest**：干净安装依赖，验证 peer 解析；检查 `package.json` 的 exports、`dsh.bundle` / `dsh.client`、`engines.dsh` 与 `files`。
3. **静态检查**：按项目实际脚本运行 typecheck、lint、unit tests、build；不要把测试命令名当作统一的 DSH 标准。
4. **产物检查**：执行 `pnpm pack` 并检查 tarball 确实包含入口、patch、client bundle、locale/assets 和 license。
5. **隔离启动**：使用专用临时 `DSH_HOME` 和独立端口启动测试 profile，不要拿日常 `~/.dsh` 或生产会话验证不稳定代码。保留一个可重复使用的私有测试 home，避免并行测试写同一 session store。
6. **真实组合验证**：运行 `dsh --profile <name> --dump-config`；必要时对可信 profile 检查 `--dump-config-schema`（它会导入组合插件，不是无副作用的纯文本检查）。
7. **功能 Smoke test**：至少真实调用一次工具/命令/设置面板；观察真实输出、取消、错误、卸载清理和重启边界。只验证 boot 成功无法证明惰性服务、工具回调或 client bundle 正常。
8. **负向测试**：用无效 config、缺失依赖、重复 id、错误 client export、不可达 MCP endpoint 等用例确认系统会明确失败，而不是静默报告成功。
9. **兼容矩阵**：对 README 宣称支持的每个 DSH 版本做安装与 smoke test；API 发生 breaking change 时提高 peer/engines 下限并在 CHANGELOG 说明。

## 9. 安全基线

插件的代码在宿主进程内或浏览器上下文执行，Git prepare 还会在安装阶段执行；不能假设 DSH 沙箱自动覆盖插件作者代码。

- 只请求实现功能所需的最少服务、文件和网络能力；不要为方便引入 unrestricted shell、任意目录读取或全局网络访问。
- 任何 shell、文件、网络或外部服务输入都必须按威胁模型校验；拒绝路径穿越、命令注入、SSRF 和不可信 URL 跳转。
- 密钥只经 DSH credential/环境注入路径传递；不写入 patch、技能示例、截图、测试快照、错误日志或 README。
- 远程 URL、headers、stdout/stderr 与工具错误都视为可能含秘密；日志、模型可见输出和 UI 展示前做脱敏。
- UI 预览不可信 HTML 时，采用隔离 iframe / CSP；不要给不可信内容同时授予 scripts 与 same-origin 权限。
- 对删除、覆盖、发帖、付款、执行外部命令等有副作用的动作，要求清楚的用户授权、可审计结果、备份或回滚路径。
- 测试未知插件时使用专用用户、临时 profile、隔离目录或容器；不要只凭 README 或下载数判断可信度。

## 10. 值得研究的项目

### 官方上游源码（第一方实现样例）

先看官方教程，再按需求深入实际 package。源码展示的是当前 master 的实现方式，不保证每个内部 API 都是外部稳定接口。

- [§packages/shell/tool-bash§](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/shell/tool-bash) — 官方工具编写参考点名的生产级工具插件案例；适合研究工具 schema、executor/provider 分层、后台 job 与 sandbox 语义。不要只复制 tool entry 而忽略它依赖的 shell/env/job services。
- [§packages/bundle/web-app§](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/bundle/web-app) — 官方 Web bundle；§cordis.patch.yml§ 是 profile bundle 层叠、entry 覆盖、完整 config 重述和 client roster 的一手例子。
- [§packages/client/ui-settings§](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/client/ui-settings) — 官方 client-side settings domain；可研究 Web settings slot、schema/remote service 分离和 feature plugin 接入方式。它是宿主内部扩展包，不是拿来直接作为外部依赖的通用脚手架。
- [§packages/acp/acp§](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/acp/acp) — 官方 ACP protocol driver；适合研究独立协议进程、session 生命周期、语义事件和取消路径。其 [README（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/acp/acp/README.zh.md) 是行为契约入口。

### 社区实现样例（非官方）

下面样例用于学习工程实现，不取代上游文档。版本号、依赖和 API 随项目变化，开始复用前先看当前分支、release 与 DSH 兼容范围。

| 项目 | 可研究的设计 | 不应照搬的内容 |
|---|---|---|
| [brzvsk/dsh-plugins — Visualize](https://github.com/brzvsk/dsh-plugins/tree/main/visualize) | 小型 bundle + `dsh.client` 双端插件；`visualize_html` 工具、slash command、工具结果 keyed view；沙箱 iframe 将可执行预览与宿主 origin 隔离 | 它的 toolview、slot、构建链与 profile 命令需按目标 DSH 版本核对 |
| [PerryLink/dsh-mcp-panel](https://github.com/PerryLink/dsh-mcp-panel) | 规模较大的 Host + Web client 双端实现；状态快照与配置写入分离、审批门、备份/验证、敏感信息脱敏、真实 Context/Session 测试和兼容性门禁 | README 报告的验证版本是项目自身时间点记录；不能推断为所有 DSH 版本均兼容 |
| [vlln/dsh-skills — make-dsh-plugin](https://github.com/vlln/dsh-skills/tree/main/skills/make-dsh-plugin) | 社区维护的插件形态选择、开发路线、验证/发布清单与生态目录；适合作为任务分解参考 | 它是 MIT 社区技能，不是 DeepSeek 官方政策；所有字段/API 必须回核官方当前版本 |
| [vlln/plugin-registry](https://github.com/vlln/plugin-registry) | 社区插件索引结构、npm/Git 版本信息和定期索引生成思路 | 社区目录不是官方审核或安全背书 |

发现项目可参考社区 Awesome 列表或 GitHub `dsh-plugin` topic，但要自行验证：仓库是否活跃、是否有源代码、许可证、维护状态、发布包内容、`engines.dsh` / peer range、CI 与真实启动测试。社区市场排名、徽章和下载数不是安全证明。

## 11. 权威资料入口

- [官方第一个插件教程（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/index.zh.md)：Cordis entry、inject、apply、插件清理和本地加载。
- [官方插件配置教程（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/config.zh.md)：Config interface 与 Schemastery schema。
- [官方工具开发教程（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/tool.zh.md)：第一个模型可调用工具。
- [官方外部插件打包与安装教程（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.zh.md)：bundle/profile manifest、安装、patch 叠加、Git prepare 与发布路径。
- [官方工具编写参考（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/adding-a-tool.zh.md)：工具 schema、执行、规范化结果与错误语义。
- [官方扩展插件形态 Cookbook（中文）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/extension-cookbook.zh.md)：tool、hook、UI、protocol driver 的扩展点。
- [官方 Client Modules README](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/modules/README.zh.md) 与 [Client Modules subsystem](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/client-modules.md)：`dsh.client`、client bundle 与浏览器模块加载。
- [官方 client stack 维护约束](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/AGENTS.md)：上游 monorepo 内部 client 代码导出、slots、store 与 inject 纪律；属于仓库内开发规则。
- [官方添加 workspace package checklist](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cookbook/adding-a-package.zh.md)：**只用于给 DSH 上游 monorepo 本身添加新 package**，不可将其 private/version/workspace 约束套用为外部插件模板。
- [官方配置目录（生成文件）](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/config-catalog.zh.md)：目标版本实际包配置、字段、默认值与 schema 的核验入口。
- [DeepSeek Harness 使用条款](https://www.deepseek.com/en/harness/terms-of-use/)：插件安装、权限、隔离与安全使用边界。

通用 Agent Skills 的 `SKILL.md` 目录结构/frontmatter 规范与 DSH 代码插件不是一份规范；编写本仓库技能时另按 [Agent Skills specification](https://agentskills.io/specification) 核对。Claude Code 的 plugin manifest 也不适用于 DSH。

---

**维护规则：** 上游 master 可帮助发现新资料，但不能代表所有已发布版本。每次对本参考做实质更新，都应写入核验日期/DSH commit 或 tag，并将新发现的版本边界加入 evals；对不上目标安装版本时，应先停在诊断而不是生成猜测配置。
