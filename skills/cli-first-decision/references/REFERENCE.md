# CLI-First Decision 3.0 — Reference

本参考表以 DSH 环境提供的信息为基准。工具调用前仍需确认当前注册状态和参数 schema；未注册的可选工具不得假设存在。

## 1. 工具路由速查

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

## 2. FastCtx 操作约定

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

## 3. CLI 命令模板

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

## 4. ast-grep 规则调试

1. 定义正例、反例和边界样例。
2. 将目标表达式拆成最小子模式。
3. 检查目标语言解析器是否支持该语法。
4. 使用最小样例验证 pattern。
5. 逐个组合子规则，定位误匹配来源。
6. 对结构关系使用关系规则，而不是扩大通配符。
7. rewrite 前先输出匹配和预览结果。
8. 检查命中数量、diff、格式和类型检查。

## 5. codebase-memory 交叉验证

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

## 6. 并行与写入冲突

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

## 7. 工具不可用时的降级

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

## 8. DSH PTC TypeScript SDK

PTC preset 使用 §run_code§ 传输入口和自动生成的 §tools:sdk§ 类型化工具 SDK。SDK 根据当前 agent 可见的工具注册表生成；读取本会话注入的签名，不硬编码或猜测工具名/参数。

- 多步骤程序通过 §tools.<tool_name>(args)§ 使用当前 SDK 暴露的工具绑定。
- PTC-only 模式下，具名工具调用通过 SDK 绑定进入执行流水线，不绕过 §run_code§ 直接调用。
- 仅 §run_code§ 外层 logs/return value 进入模型上下文；程序内部中间值不自动回传。
- §packages/sdk§（进程外驱动 Harness）与 PTC §tools:sdk§（模型程序调用当前工具）是不同概念。

### PTC 示例

假设当前生成 SDK 中存在 §tools.read_file({ path })§，并且参数已被工具调度策略判定为可安全并行：

~~~~ts
const paths = ["/project/a.ts", "/project/b.ts"];
const contents = await Promise.all(
  paths.map((path) => tools.read_file({ path }))
);
return contents.map((text, index) => ({
  path: paths[index],
  chars: text.length,
  preview: text.slice(0, 800),
}));
~~~~

示例中的 §read_file§ 和参数形状不是固定内置承诺，必须以当前 §tools:sdk§ 为准。

### 并发约束

- 只有 §isConcurrencySafe(args)§ 明确返回 §true§ 的工具调用才允许重叠。
- 未声明/未知/判断失败默认 §exclusive§，作为串行屏障。
- 并行上限由 §maxParallelSubCalls§ 控制；参考实现默认 10，以当前运行时配置为准。
- §Promise.all§ 只是程序层并发表达，不可用来绕过工具自身的并发策略。

### 错误、安全与副作用

- 绑定调用失败在程序中表现为 §ToolCallError§，可读取 §toolName§。
- 程序运行失败返回结构化 §CODE_RUN_FAILED§。
- 普通副作用不会因程序失败自动回滚；非幂等写入失败后先检查实际状态。
- worker-thread 不是 OS 级文件/网络权限沙箱；按 DSH 工具权限和 sandbox 契约执行，不用 Node API/子进程绕过工具边界。
## 9. 验收记录

一次任务至少记录：

- 实际使用的工具和降级路径。
- 读取/修改的文件集合。
- 修改前后范围或 diff。
- 命令退出码及关键输出。
- 测试/检查是否真实运行。
- 未解决的问题和限制。
