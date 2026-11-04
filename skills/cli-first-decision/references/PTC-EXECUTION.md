# DSH PTC 执行与运行时 SDK 参考

本文承载 CLI-First Decision 中 DSH PTC 的详细执行契约。具体运行时能力必须以当前会话注入的 tools:sdk、工具 schema、安装版本和官方源码为准。


## 1 默认使用方式

当当前 DSH 会话启用 PTC，且提示上下文提供 `run_code` 与 `tools:sdk` 时，多步骤工具任务可优先用 PTC 编排。**程序语言必须服从当前加载的 `ctx.ptcRuntime.language` 及注入的 SDK 指令**：TypeScript runtime 使用 TypeScript；Python runtime 使用 Python；不要把以下 TypeScript 示例复制到 Python runtime。

- `run_code` 是 PTC 程序的模型调用入口；以当前 schema 要求传入 `code`、`description` 等字段，不猜测可选参数。程序体语法由当前 runtime 的 instructions 决定。
- `tools:sdk` 是运行时根据当前 agent 可见工具注册表、策略与 `ctx.ptcRuntime.language` 生成的程序内 SDK。
- 在程序中通过 `tools.<工具名>(args)` 调用 SDK 中实际提供的绑定。
- 工具名、参数和返回类型必须以当前会话注入的 SDK 定义为准；不得从其他项目、旧版本或记忆中猜测。
- PTC-only 模式下，不要绕过 `run_code` 直接调用具名工具；应通过 SDK 绑定进入工具执行流水线。
- `tools:sdk` 不是外部安装的 GitHub/Context7 插件，也不是进程外驱动 Harness 的 `packages/sdk`；它是 PTC 工具呈现层生成的调用 SDK。

如果当前会话不是 PTC preset，或没有注入 `tools:sdk`，就使用当前真实可用的原生工具调用路径。不要假装 SDK 存在，也不要仅为简单单步操作强行切换模式。

## 2 何时使用 PTC

适合：
- 读多个文件后在程序内筛选、提取、归纳。
- 多个工具按依赖顺序串联，且中间结果只供程序判断。
- 根据中间结果执行条件分支、循环或批量处理。
- 扇出多个独立调用，再在程序内聚合结果。
- 希望仅把最终摘要或必要结果送回模型上下文。

不必使用：
- 单个简单工具调用。
- 必须由模型观察中间结果后再作高层判断的阶段。
- 用户要求逐步确认或每一步都有外部副作用审批的任务。
- PTC SDK 未提供所需工具或权限的任务。

## 3 编排模式

先读取当前会话的 `tools:sdk`，确认每个绑定的真实名称、参数、返回类型和可见性，再写程序。

以下只是 **TypeScript runtime** 的结构示例；只有当前 `tools:sdk` 明确生成 TypeScript 声明时才使用。`read_file` 不是 DSH 固定工具名，必须换成当前 SDK 实际生成的绑定。Python runtime 应按注入的 Python instructions 写程序，不得直接照抄本例：

~~~~ts
const paths = [
  "/project/src/auth.ts",
  "/project/src/router.ts",
  "/project/package.json",
];

const outcomes = await Promise.allSettled(
  paths.map((path) => tools.read_file({ path }))
);

// 按路径保留每个成功/失败分支；按当前 SDK 的真实返回类型调整。
return outcomes.map((outcome, index) =>
  outcome.status === "fulfilled"
    ? { path: paths[index], ok: true, preview: String(outcome.value).slice(0, 1200) }
    : { path: paths[index], ok: false, error: String(outcome.reason) }
);
~~~~

若当前 SDK 中没有 `read_file` 或参数不同，必须按注入的签名替换示例；不得把示例名称当成 DSH 固定内置工具。

## 4 并发语义

`Promise.all` 表示程序发起并发意图，不代表所有子调用都会并行执行；其中一个调用 reject 会使整个聚合 Promise reject，外层程序失败后 DSH 会取消并 drain 尚未完成的绑定。若必须保留成功分支结果，使用 `Promise.allSettled` 或对每项绑定调用单独 `try/catch`，再分别处理成功/失败结果：

- 只有工具对当前参数明确被标记为 concurrency-safe，才允许实际重叠执行。
- `isConcurrencySafe(args)` 必须明确返回 `true` 才能进入 parallel；未声明、未知、非法或判断异常均按 exclusive 处理。
- exclusive 子调用形成串行屏障；不要把有顺序依赖的写操作放进并行批次。
- 实际并发上限由 `maxParallelSubCalls` 运行时配置控制；参考实现默认值为 10，执行时以当前环境配置为准。
- 即使多个调用在程序中并发发起，工具执行策略、权限检查和最终结果顺序仍由 DSH 工具流水线管理。

## 5 结果与上下文

- 子调用的中间值保留在 PTC 程序内。
- 通常只有程序外层 logs 和 return value 进入模型上下文。**例外**：成功的图像子调用及工具返回的 `additionalContexts` 可由 dispatcher 独立转发为延迟附加上下文，不一定包含在外层 return/log 中；它们仍消耗模型上下文预算，应把大型图像/附加内容纳入总上下文成本评估。
- 程序内完成筛选、映射、聚合，只返回决策所需字段。
- 不要把大文件、完整搜索结果或重复原始输出全部 return。
- 需要审计的工具操作仍经过完整工具流水线；不要把“中间结果不进上下文”误解为“没有执行记录”。

## 6 错误和副作用

- SDK 绑定调用失败会在程序内表现为 `ToolCallError`；可捕获并读取 `toolName` 定位具体失败工具。
- PTC 程序自身运行失败会作为结构化 `CODE_RUN_FAILED` 结果返回，检查具体错误后再调整程序。
- `Promise.all` 任一 binding reject 时，聚合结果整体 reject；未捕获时 DSH 会取消并 drain 尚未完成的绑定。需要保存已成功分支时，在可能失败的扇出中使用 `Promise.allSettled` 或逐项捕获，先整理每项成功/失败，再决定是否让程序整体失败。
- 一个绑定调用失败不代表此前的普通副作用已回滚；不要假设 PTC 提供事务。
- 程序结束/失败时，运行时会取消并 drain 未完成的绑定调用，但已经产生的外部副作用仍需按工具语义处理。
- 对写入、提交、发布、删除等非幂等操作，先完成只读预检；将可并行的只读部分与写入阶段分开；失败后先检查实际状态，不盲目重跑。
- 对多个文件写入，使用明确文件边界并串行处理共享文件；按工具契约验证每个写入结果。

## 7 运行时安全边界

Node PTC provider 按所选模式执行 TypeScript；sandbox 能力由实际 provider/宿主策略决定。Python experimental provider 的执行与隔离边界也不能直接套用 Node 结论。不能仅凭 runtime 语言、VM/REPL context 或 worker 线程推断已具备 OS 级文件、网络或进程沙箱能力。通过当前 SDK 绑定调用工具，并遵守工具权限、审批和 sandbox 策略；不要通过程序直接访问 Node API 或子进程来绕过宿主工具边界。
