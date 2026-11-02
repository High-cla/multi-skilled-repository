# CLI-First Decision 3.5 — Reference

本参考表以 DSH 环境提供的信息为基准。工具调用前仍需确认当前注册状态和参数 schema；未注册的可选工具不得假设存在。

## 0. 扩展参考

- [CLI 工具链、命令模板和 FastCtx Shell 约定](CLI-TOOLS.md)
- [从零开始的架构选择、官方文档调研与 ADR/C4](ARCHITECTURE-DESIGN.md)
- [编程规则、速度与内存优先优化](PROGRAMMING-RULES.md)
- [工程原则、定律与设计取舍](ENGINEERING-PRINCIPLES.md)
- [DSH/FastCtx 上游、CLI 官方手册和工程依据](AUTHORITATIVE-SOURCES.md)

## 1. 任务类型路由

| 任务 | 先读 |
|---|---|
| 从零开始、系统重建、重大架构选择、技术栈调研 | [ARCHITECTURE-DESIGN.md](ARCHITECTURE-DESIGN.md) |
| 具体功能实现、代码优化 | [PROGRAMMING-RULES.md](PROGRAMMING-RULES.md) |

## 2. 工具路由速查

| 场景 | 首选 | 备选/降级 | 不要这样做 |
|---|---|---|---|
| 已知本地文件读取 | FastCtx inspect_local_file | 内置 Read | 用 shell cat / Get-Content |
| 多文件读取 | 一次 inspect_local_file(files=[...]) | 分批读取 | 一个文件一次工具调用 |
| 文件名搜索 | FastCtx glob | fd | 多层递归 ls/find |
| 全文搜索 | FastCtx grep | rg | 全文 Read 后肉眼查 |
| 结构搜索/改写 | ast-grep (sg) | 语义编辑 | 正则硬改代码 |
| 符号/调用链/依赖 | codebase-memory | grep + sg 交叉验证 | 只靠关键词猜调用链 |
| 跨文件机械替换 | FastCtx replace | sd | 逐文件 Edit |
| 语义重写 | edit/write | 专项代码技能 | 盲目批量替换 |
| JSON | jq | 项目原生脚本 | 字符串切割 JSON |
| YAML/XML | yq | 对应语言解析库 | 普通文本替换结构字段 |
| HTTP | curl | git-curl / 当前可用 API | 多层 wrapper |
| 长命令 | run_background | 拆成可恢复阶段 | 前台超过四分钟 |
| MCP 退路 | mcp2cli @<name> | 已注册等价工具 | 假设任何 MCP 都已 bake |

GitHub、Context7 插件不是本地 DSH 的必需依赖。它们只有在当前运行时实际注册时才可选择。

## 3. FastCtx 操作约定

| 工具 | 用途 | 要点 |
|---|---|---|
| inspect_local_file | 读取一个或多个文件 | 多文件用 files 数组一次提交 |
| grep | 搜索文件内容 | 收窄目录、文件类型和上下文 |
| glob | 查找路径 | 使用 glob pattern |
| replace | 跨文件文本替换 | dry-run；保留编码/行尾；拒绝并发修改 |
| run | Bash 命令 | POSIX Bash、非交互、无 TTY |
| run_background | 长任务 | 预计超过四分钟时启动 |
| job_list | 查询后台任务 | 找回已有 job_id |
| job_output | 获取任务输出 | 按 job_id 查询 |
| job_kill | 停止后台任务 | 先核对 job_id |

所有 FastCtx 结果检查最后一行：

- Complete：结果完整，停止续读。
- Partial：仅使用返回的续读参数原样继续。

非零退出码也需要读取 stdout、stderr 和退出状态后再判断。不得把非零退出码误判为工具崩溃，也不得因命令启动成功就报告业务成功。

## 4. CLI 命令模板

### 搜索

```bash
rg -n -C 2 'pattern' src --glob '*.ts'
fd -0 -e ts src | xargs -0 -r rg -n 'pattern'
```

### JSON / YAML

```bash
curl -fsS "$URL" | jq '.items[] | {id, name}'
yq '.services.api.port' config.yaml
```

### 压缩文件

```bash
rg -z 'pattern' archive.tar.gz
zstd -d -c data.jsonl.zst | jq -c 'select(.level == "error")'
```

仅在确认文件格式和工具版本后使用对应参数。不要为了一条命令默认解压所有数据到磁盘。

### 结构搜索

```bash
sg --pattern 'console.log($A)' --lang ts src
```

具体参数以安装版本的 `sg --help` 和项目配置为准。Windows DSH 环境路径使用已约定的 `C:/...` 形式。

### 机械替换

优先 FastCtx replace 的 dry-run。使用 sd 时先检查本机版本帮助和预览能力；纯文本替换不得用于依赖语法结构的代码改写。

## 5. ast-grep 规则调试

1. 定义正例、反例和边界样例。
2. 将目标表达式拆成最小子模式。
3. 检查目标语言解析器是否支持该语法。
4. 使用最小样例验证 pattern。
5. 逐个组合子规则，定位误匹配来源。
6. 对结构关系使用关系规则，而不是扩大通配符。
7. rewrite 前先输出匹配和预览结果。
8. 检查命中数量、diff、格式和类型检查。

## 6. codebase-memory 交叉验证

适合：符号定义、引用、调用者/被调用者、依赖边、模块架构、影响面。

交叉验证路径：

```text
codebase-memory 定位符号
        |
获取 callers / callees / dependencies
        |
生成待核验的文件和符号清单
        |
FastCtx grep / rg / sg 核查当前源码
        |
检查测试、配置和动态调用
        |
确定真实影响面
```

若图谱没有结果或与源码冲突，标记索引可能不完整/过期，以当前源码和可复现测试为准。

## 7. 并行与写入冲突

| 情况 | 策略 |
|---|---|
| 独立只读检索 | 同轮并行 |
| 同一个源可批量读取 | 一次批量调用优先 |
| 独立文件写入、接口已稳定 | 可并行 |
| 同一个文件写入 | 串行 |
| 消费另一个任务的接口/输出 | 生产者完成后再消费 |
| 可通过管道合并 | 合成一条 CLI |
| 多维独立审查 | 并行审查、统一归并 |

派发前为每个执行者列出 Read、Write、共享接口。并行数量服从真实工具限制；不要设定未经验证的固定上限。

## 8. 工具不可用时的降级

| 首选不可用 | 降级顺序 |
|---|---|
| FastCtx 文件读取 | 当前已注册的内置 Read；再考虑可用 CLI |
| FastCtx grep | rg；再用已注册 grep |
| FastCtx replace | sd（先预览）；语义修改用 edit/write |
| ast-grep | 仅在确属纯文本时用 rg；结构规则不可用则说明阻塞 |
| codebase-memory | rg + sg + 源码跟踪；结论标记为人工交叉分析 |
| Context7 | 官方文档、官方仓库、锁定版本对应文档 |
| GitHub 插件 | 本地 git clone；公开只读用 Web/curl；远程写入需认证通道 |
| MCP 工具 | 仅对已 bake 工具尝试 mcp2cli；否则使用等价工具或报告阻塞 |

## 9. DSH PTC：run_code 与自动生成的 tools:sdk

PTC 的权威定义来自 DSH 当前安装版本的 `@deepseek-ai/dsh-tools`、`@deepseek-ai/dsh-tool-executor-ptc`、工具目录和当前会话注入的 `tools:sdk`。先读 [AUTHORITATIVE-SOURCES.md](AUTHORITATIVE-SOURCES.md) 的 DSH 部分。

### 9.1 调用入口与 SDK

- PTC presentation 下，模型直接调用的执行入口是 `run_code`；其它当前可见的工具由运行时按 `ctx.ptcRuntime.language` 生成程序内 SDK。
- 当前官方 `run_code` schema 要求 `code` 与 `description` 两个字段。TypeScript runtime 的 `code` 是异步函数体，支持顶层 `await` / `return`，但只支持可擦除类型语法。
- SDK 的类型渲染语言由加载的 PTC runtime 决定；`dsh-tools` 当前包含 TypeScript 与 Python renderer，Node provider 执行 TypeScript，Python runtime 位于实验性 package。**不得假设所有 DSH PTC 环境恒为 TypeScript。**
- 以本会话展示的 `tools:sdk` 声明为准，精确核验工具名称、参数、返回类型和可见范围。不要复制旧会话的 schema，不要自行创造工具名。
- PTC-only 模式中不能把 SDK 绑定误认为模型顶层工具；应通过 `run_code` 内的 `await tools.<tool_name>(args)` 进入调用流水线。
- `packages/sdk`（进程外驱动 Harness）与 PTC 自动生成的 `tools:sdk`（程序内调用当前 agent 工具）不是同一概念。

### 9.2 PTC 示例

以下只是结构示例；`read_file` 不是 DSH 固定工具名，必须换成当前 SDK 实际生成的绑定：

~~~~ts
const paths = ["/project/a.ts", "/project/b.ts"];
const contents = await Promise.all(
  paths.map((path) => tools.read_file({ path }))
);
return contents.map((content, index) => ({
  path: paths[index],
  chars: content.length,
  preview: content.slice(0, 800),
}));
~~~~

工具参数的序列化、返回值和类型限制以当前生成 SDK 与 DSH 工具 schema 为准。SDK 中的类型提示不是运行时验证的替代品。

### 9.3 并发调度

- DSH 当前 `@deepseek-ai/dsh-tools` 文档将 `maxParallelSubCalls` 的默认值列为 10；配置为 1 时恢复严格串行。该默认值具有版本属性，不要假设未来或定制 runtime 固定不变。
- `Promise.all` 只代表程序发起并发意图，不保证子调用一定同时执行。
- 只有工具当前参数被调度策略判定为 concurrency-safe 时才允许重叠；exclusive/未知调用必须遵从串行屏障。
- 共享文件写入、远程副作用、提交/发布/删除等操作不得仅为加速而并行。先拆分只读预检和副作用阶段。
- 调用结果的外层顺序/关联由 DSH 管线维护；不要通过程序端 Promise 完成顺序推断安全顺序。

### 9.4 结果、内存与输出

- PTC 子调用中间结果在程序执行本地保留；当前 DSH 工具包文档明确指出中间绑定值不按字节数限制，可能耗尽进程或 worker 内存。
- 大文件/大响应应在程序内筛选、流式或分块处理、汇总必要字段；及时解除不再使用的引用，避免把所有完整结果保存在数组中。
- 只有外层 `run_code` 的返回值/log 输出进入模型上下文（图片等附加上下文按 DSH 当前契约处理）。外层输出仍受大小限制；只返回模型决策所需信息。
- 控制输出体积不等于控制程序内存。程序内部仍需显式设定数据规模和缓存上限。

### 9.5 超时、安全与副作用

- 当前工具目录对 Node provider 给出的 `timeoutMs` 默认值为 120,000 ms、最大值为 600,000 ms；Node provider README 还列出 `maxOldGenerationSizeMb` 默认 512 MiB、`maxOutputBytes` 默认 64 MiB、`maxMessageBytes` 默认 128 MiB 等参数。它们均为 provider 版本配置，不等于所有 PTC 中间值都有相同 byte cap；必须以本会话 runtime/schema 为准。
- 更宽的 `sandbox_permissions` 需要解释理由并经审批；权限只适用于该次执行。嵌套工具仍遵守自身策略与审批。
- Runtime 的 isolation/substrate 描述不能单独证明 OS 级安全隔离。检查当前 PTC provider、实际 sandbox mode 和执行结果报告的 enforcement facts；按 DSH sandbox policy 操作，不通过 Node API 或子进程绕过宿主权限。
- 对于取消和失败，区分外层代码异常、超时/取消、SDK 子工具错误和 sandbox 拒绝。工具定义若要求协作式取消，应观察传入的 signal。
- SDK 子调用失败可通过 `ToolCallError` 与 `toolName` 识别具体失败工具；外层程序失败按当前 runtime 的错误分类处理。
- 普通文件/网络/提交等副作用不会因为 PTC 程序失败而自动回滚。失败后先核对实际状态，不盲目重试，不假设事务或 exactly-once。

## 10. 验收记录

一次任务至少记录：

- 实际使用的工具和降级路径。
- 读取/修改的文件集合。
- 修改前后范围或 diff。
- 命令退出码及关键输出。
- 测试/检查是否真实运行。
- 未解决的问题和限制。
