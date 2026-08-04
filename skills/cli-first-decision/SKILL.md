---
name: cli-first-decision
description: "任务执行前的工具路径决策框架。任何需要多步操作、代码改动、文件搜索、批量处理、子智能体委派或最优工具选择时，必须先用此 skill 判断最短路径。触发词：怎么执行、先做什么、用哪个工具、能不能并行、能不能合并、怎么更快、要不要派子智能体、批量处理、多文件、搜索替换、机械操作。"
compatibility: "Requires OpenCode with Bash, task(), Read/Edit/Write, grep/glob, and CLI tools (fd, rg, sd, jq, yq, curl, ast-grep)"
metadata:
  author: opencode
  version: "2.1"
---

# CLI-First Decision

**核心原则**：先选最短路径；能合并就合并；能并行就并行；闭合后 compress。

## 何时使用

每个任务执行前，先用本框架做 5 秒内决策。尤其适用于：

- 多步骤操作
- 涉及多个文件或模块
- 需要搜索/替换/过滤/统计
- 需要委派子智能体
- 不确定用内置工具、CLI 还是 skill/MCP
- 用户问"怎么执行""先做什么""能不能并行"

## 决策流程（按顺序）

```
1. 任务是什么？
   ├─ 修复 bug → 定位 → 最小修复 → 验证
   ├─ 实现功能 → 规划 → 拆分 → 并行实现 → 验证
   ├─ 调研 → 并行收集事实 → 综合
   ├─ 评估/选型 → 同轮按轴批评 → 选优
   └─ 机械操作 → CLI 优先

2. 需要几步？
   ├─ 1 步且已知文件/内容 → 直接内置工具
   ├─ 多步且无依赖 → 同轮全部并行发出
   ├─ 多步且可管道 → 一条 CLI
   └─ 多步且有依赖 → 分层：层内并行，层间串行

3. 选工具
   ├─ 批量替换/搜索/过滤 → CLI (sd/rg/fd/jq)
   ├─ 需要语义理解 → 子智能体 task()
   ├─ 已知模式 → skill / MCP
   └─ 单文件读写 → Read/Edit/Write

4. 执行后 → 验证 → compress
```

## 合并规则（硬规则）

**默认：同一响应里发出所有无依赖调用。禁止串行往返。**

| 类型 | 合并方式 | 示例 | 反例（禁止） |
|------|----------|------|--------------|
| 内置工具 | 同轮并行 | 多个 Read / Grep / Glob / lsp_diagnostics 同时发 | 先 Read A 再 Grep |
| CLI | 一条管道 | `fd -e ts src \| xargs rg 'pattern'` | fd 一轮，rg 一轮 |
| 子智能体 | 一次派 N 个 | 3 个独立 explore 同时启动 | 等 explore1 完再派 explore2 |
| 混合 | 同轮批出 | CLI + Read + task 无依赖时一起发 | 先 CLI 等完再 Read |

### 合并决策树

```
需要 ≥2 次工具调用？
  ├─ 完全无依赖 → 同轮全部发出
  ├─ 可管道（A\|B\|C）→ 合成一条 CLI
  ├─ 有依赖但可分层 → 层内并行，层间串行
  └─ 仅 1 步 → 直接内置工具
```

## 工具选择矩阵

| 场景 | 首选 | 次选 | 禁用 |
|------|------|------|------|
| 批量文本替换 | `sd` / `git-sed` | `ast-grep_replace` | 逐文件 Edit |
| 文件查找 | `fd-find` / `fd` | `glob` | 多层 bash `find` |
| 内容搜索 | `rg-search` / `rg` | `grep` | 全文 Read 再肉眼找 |
| AST 搜索替换 | `ast-grep` | - | 正则硬改代码 |
| JSON 处理 | `jq-query` / `jq` | - | 手动解析 |
| YAML/XML | `yq` | - | 手动字符串替换 |
| HTTP 请求 | `git-curl` / `curl` | `webfetch` | 多层 wrapper |
| 模糊过滤 | `fzf-filter` / `fzf` | - | 手动排序 |
| 代码统计 | `tokei` | `wc -l` | 多次 ls |
| 文本查看 | `bat` | `Read` 小文件 | 大文件整读 |
| 打包/换行 | `git-tar` / `git-dos2unix` | - | 手动压缩 |
| 跨模块分析 | `task(explore, background)` × N | `codebase-memory-mcp` | 自己逐个查 |
| 不熟库调研 | `task(librarian, background)` | `context7` | `webfetch` 硬啃 |
| 单文件已知修改 | `Edit` / `Write` | - | 派子智能体 |
| 复杂语义任务 | `task(deep/ultrabrain)` | `task(unspecified-high)` | 自推硬写 |
| 架构/审查 | Oracle / 自推 | 多专家评审并行 | 边做边想 |

### 管道优先示例

| 目标 | 一条命令 |
|------|----------|
| 找 TS 文件再搜内容 | `fd -e ts src \| xargs rg 'pattern'` |
| 搜再过滤 | `rg 'pattern' \| fzf --filter='term'` |
| JSON 提取 | `curl url \| jq '.data[]'` |
| 批量替换 | `sd 'old' 'new' file1 file2 file3` |
| 统计文件数 | `fd -e ts \| wc -l` |

## 并行规则

| 依赖关系 | 策略 |
|----------|------|
| 无依赖 | **全并行，同轮启动** |
| 有依赖 | 层内并行，层间串行 |
| 互斥决策 | 同轮按轴批评，再选优 |
| 强因果单链 | 一条 sequential-thinking 或分步执行 |

### 文件级并行决策（子智能体/任务派发）

**核心规则：不同文件可并行，相同文件必须串行。**

```
批处理 ≥2 个子智能体/任务？
  ├─ 两个任务编辑同一文件 → SERIAL（后者等前者 review 干净再派）
  ├─ 消费对方输出/接口/共享模块 → SERIAL（消费者等生产者 review）
  ├─ 文件全不相交 + 无共享依赖 → PARALLEL（同轮全发）
  └─ 混合 → 不相交组并行，重叠组串行
```

| 依赖 | 策略 |
|------|------|
| 同文件双方编辑 | **SERIAL** |
| 消费对方输出/接口 | **SERIAL** |
| 共享模块一方修改 | **SERIAL** |
| 不相交文件 | **PARALLEL** |
| 只读任务（搜索/审查/调研） | **PARALLEL** 永远，同文件也不冲突 |

**判断法**：派发前 5 秒列出每个任务的触达文件 + 消费接口；集合不相交 → 并行，有重叠 → 串行。拿不准（"扩展"他人工作、共享模块）→ 按共享依赖串行化。

### 推理任务并行

```
需要决策？
  ├─ 缺事实 → 同轮批出全部事实调用 → 再决策
  ├─ 多独立判断轴 → 同轮并行判断 → 合成
  ├─ 互斥选项 → 同轮按轴批评 → 选优
  ├─ 强因果单链 → sequential-thinking
  └─ 已够信息 → 直接决策
```

## 子智能体委派

### 必须拆分的信号

- 跨 ≥2 个模块
- 需要语义理解或设计决策
- 需要调研外部库/文档
- 需要搜索代码库模式
- 实现复杂功能
- 安全/架构审查

### 一次只派一件事

每个子智能体只负责一个原子目标。禁止把多个独立任务塞进一个 prompt。

### Prompt 模板（6 段必填）

```
1. TASK: 原子、具体的目标
2. EXPECTED OUTCOME: 交付物 + 成功标准
3. REQUIRED TOOLS: 工具白名单
4. MUST DO: 穷举需求
5. MUST NOT DO: 禁止操作
6. CONTEXT: 文件路径 + 现有模式 + 约束

WORKING_DIR=<绝对路径>
```

**必填项**：
- `WORKING_DIR` 必须在 TASK 段后首行
- 新任务不传 `task_id`；`task_id` 仅用于续聊（ses_...）

### 子智能体并行策略

| 场景 | 派几个 | 类型 |
|------|--------|------|
| 找多个模块信息 | 2-5 个 explore | 后台并行 |
| 调研多个外部库 | 2-3 个 librarian | 后台并行 |
| 多维度审查 | 安全∥质量∥规格 | 后台并行 |
| 复杂实现 | 1 个 deep/unspecified-high | 同步或后台 |

## Compress 时机

| 时机 | 动作 |
|------|------|
| 单步完成 | compress 该步 |
| 子智能体验证通过 | compress（文件名 + 签名 + 状态） |
| context 警告 | **立即** compress |
| 用户确认方向后 | compress 讨论过程 |

## 红旗（立刻停止并修正）

- 本可并行的 Read/Grep 排成队列
- 三次独立 bash 本可合成一条管道
- 等一个 explore 完再派下一个
- 两个任务编辑同一文件却并行派发（必须串行）
- 不相交文件任务却串行排队（白耗墙钟时间）
- 「先看看再决定」却只发了 1 个工具
- 多判断轴串成队列
- 事实未齐就开始写实现
- 决策未定就双轨实现
- 新任务误传 `task_id`
- 机械替换不用 CLI 而派子智能体
- 单文件已知修改派子智能体

## 常见错误与修正

| # | 问题 | 修正 |
|---|------|------|
| 1 | 自己动手不委派 | 复杂语义 → 子智能体 |
| 2 | 串行不并行 | N 独立单元 → N 并行 |
| 3 | 多轮工具往返 | 无依赖 → 同轮全发出 |
| 4 | 可管道却拆轮 | A\|B\|C 一条命令 |
| 5 | 跳过 CLI 直接 task | 机械替换用 sd/git-sed |
| 6 | 找到文件后手改循环 | 一次批量替换 |
| 7 | 单文件也派代理 | 直接 Edit |
| 8 | CLI 不懂语义却硬 CLI | 语义任务用 task |
| 9 | sd 不 preview | 先 `--preview` |
| 10 | yq XML 参数混 | v4: `-p xml` |
| 11 | prompt 模糊 | 必须 6 段 |
| 12 | 不拆分复杂任务 | 一代理一事 |
| 13 | 闭合不 compress | 查 Compress 表 |
| 14 | 决策前串行摸底 | 事实调用同轮批出 |
| 15 | 多方案串行深挖 | 同轮按轴批评再选 |
| 16 | 决策后双轨实现 | 选定一条主路径 |
| 17 | task_id 误用于新任务 | 新任务不传 task_id |

## 示例

### 示例 1：批量替换

**任务**：把项目里所有 `console.log` 改成 `logger.debug`

**错误做法**：
1. grep 找文件
2. 逐个 Read
3. 逐个 Edit

**正确做法**：
```bash
sd 'console\.log' 'logger.debug' $(fd -e ts -e js)
```

### 示例 2：改前摸底

**任务**：修改 auth 模块前了解现状

**错误做法**：先 Read auth.ts，等完再 Grep

**正确做法**：同轮并行
- Read auth.ts
- Read middleware.ts
- Grep 'auth' --include='*.ts'
- lsp_symbols(auth.ts)

### 示例 3：多方案选型

**任务**：选状态管理库

**错误做法**：先深度调研 Zustand，再调研 Jotai，再对比

**正确做法**：同轮并行 3 个 librarian，分别调研 Zustand / Jotai / Redux Toolkit，再综合对比

### 示例 4：复杂功能实现

**任务**：实现 JWT 认证

**错误做法**：自己写所有代码

**正确做法**：
1. 同轮并行 explore：找现有 auth 模式、错误处理、路由结构
2. 同轮并行 librarian：查 JWT 安全最佳实践、Express 模式
3. 拆分子智能体：middleware、handlers、token utils、tests
4. 并行实现后验证

## 详细参考

完整工具矩阵、CLI alias、进阶场景 → [references/REFERENCE.md](references/REFERENCE.md)
