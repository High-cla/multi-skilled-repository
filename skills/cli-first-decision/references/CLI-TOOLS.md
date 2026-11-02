# CLI 工具链参考

权威来源与版本策略见 [AUTHORITATIVE-SOURCES.md](AUTHORITATIVE-SOURCES.md)。

本文件记录 DSH + FastCtx 环境中的命令行路由。FastCtx 是本地文件与命令操作入口；CLI 是组合、过滤、转换和批处理执行层。不要把工具清单误解为所有机器都必然安装了全部二进制：优先使用已配置工具，只有遇到缺失或参数不确定时才做轻量能力检查。

## 1. 工具链路由总表

| 场景 | 第一选择 | 具体命令/入口 | 备注 |
|---|---|---|---|
| 本地文件读写、搜索、替换、命令 | FastCtx MCP | `inspect_local_file`、`grep`、`glob`、`replace`、`run` | 本地文件工具优先，不用 shell 等价物绕开 |
| 后台命令 | FastCtx MCP | `run_background`、`job_output`、`job_list`、`job_kill` | 超过 run 四分钟限制 |
| 符号、调用链、架构、影响面 | codebase-memory MCP | `mcp__codebase_memory__*` | 先图谱定位，再检查源码 |
| 结构搜索和结构改写 | ast-grep CLI | `sg` | 路径按 DSH 约定使用 `C:/...` |
| 全文搜索 | ripgrep | `rg` / `rg-search` | 纯文本检索 |
| 文件查找 | fd | `fd` / `fd-find` | 文件名、扩展名、目录 |
| 文本替换 | sd | `sd` / `git-sed` | 仅纯文本替换；先预览 |
| JSON | jq | `jq` / `jq-query` | 结构化查询和变换 |
| YAML/XML | yq | `yq` | 确认 yq 版本和输入格式 |
| HTTP | curl | `curl` / `git-curl` | 检查状态码、headers、错误体 |
| 模糊过滤 | fzf | `fzf` / `fzf-filter` | 非交互脚本用 `--filter` |
| 代码统计 | tokei | `tokei` | 统计需服务于实际决策 |
| 文件查看 | bat | `bat` | 大文件优先按范围读取 |
| 打包/归档 | tar | `git-tar` | 优先一次性归档，不手工循环打包 |
| 行尾转换 | dos2unix | `git-dos2unix` | 先识别目标文件行尾和编码 |
| 命令定位 | which / command -v | `git-which` | 检查实际 PATH 命令 |
| 压缩数据搜索 | ripgrep / zstd | `rg -z`、`zstd -d -c` | 确认压缩格式和版本 |
| JSONL 聚合 | DuckDB | `duckdb` | 大数据优先流式输入/聚合 |
| 结构化 diff | difftastic | `difft` | 适合代码重构审查 |
| Git diff 展示 | delta | `delta` | 仅改善展示，不改变 diff 内容 |
| 任务编排/项目体检 | just | `just` | 先查看项目 `justfile` 和可用任务 |
| 已 bake MCP 的 CLI 退路 | mcp2cli | `mcp2cli @<name>` | 当前环境已 bake 的 12 个服务；使用前检查映射/help |

## 2. FastCtx 优先级和文件边界

| 操作 | 优先工具 | 避免 |
|---|---|---|
| 读文件 | `inspect_local_file` | `cat` / `Get-Content` |
| 搜内容 | `grep` | `rg` / `findstr` / `Select-String` 作为首选 |
| 找文件 | `glob` | `dir` / `ls -R` / `find` 作为首选 |
| 批量替换 | `replace` | 逐文件 edit |
| 执行命令 | `run` | 内置 shell 的多轮拆分 |

多文件读取必须尽可能一次传入 `files=[{"path":...}, ...]`。结果尾行是 `Partial` 时，只按返回的原样续读参数继续；尾行是 `Complete` 时停止读取。

批量替换优先 dry-run；写入前拒绝并发修改；保留文件编码和行尾。生成式/语义改写用 edit/write，不用 replace 伪装语义理解。

## 3. DSH 终端规则

FastCtx `run` 使用 Bash；Windows 下使用 Git Bash 兼容的 POSIX 语法。

- 不写 PowerShell 专属语法。
- 必须非交互、无 TTY；关闭 pager/editor。
- 使用 `--yes`、`--no-edit` 等自动化选项。
- 命令默认受四分钟上限约束；长任务用后台机制。
- 非零退出码也要读取 stdout/stderr 和状态后判断，不可直接吞错。
- 所有路径正确引用；含空格/特殊字符的批处理优先 NUL 分隔。
- 避免在命令中拼接不可信输入，避免不必要的 `eval`。

建议：

```bash
# 查找 TS 文件并搜索，使用 NUL 分隔路径
fd -0 -e ts src | xargs -0 -r rg -n 'AuthService'

# 搜索时限定文件类型和上下文
rg -n -C 2 'featureFlag' src --glob '*.ts'

# JSON 处理使用管道，不落临时文件
curl -fsS "$URL" | jq '.items[] | {id, name}'

# 先看项目已有任务，再执行
just --list
```

## 4. PATH 和别名约定

当前 DSH Windows 环境的常见 CLI 来源目录：

- `~/AppData/Local/Microsoft/WinGet/Links/`
- `~/.cargo/bin/`

常见别名/包装：

| 常见命令 | 实际工具 |
|---|---|
| `find` | `fd` |
| `grep` | `rg` |
| `cat` | `bat` |
| `sed` | `sd` |
| `man` | `tldr` |
| `cd` | `z` |

别名只保证在配置对应 shell 中生效。脚本中优先使用明确二进制名，不依赖交互式 shell alias。检查命令是否存在用 `command -v <name>` 或 `git-which`，不要猜测安装路径。

## 5. 组合命令和管道

| 目标 | 组合思路 | 注意 |
|---|---|---|
| 找文件再搜索 | `fd -0 ... | xargs -0 rg ...` | 空格和换行文件名安全 |
| 过滤大结果集 | `rg ... | fzf --filter=...` | 非交互模式，不等待键盘输入 |
| HTTP 取数并解析 | `curl -fsS ... | jq ...` | 先检查 HTTP 错误 |
| 压缩数据过滤 | `zstd -d -c ... | jq/duckdb ...` | 不落盘解压整个文件 |
| 结构审查 | `sg` + `difft` | AST 搜索与结构 diff 分工 |
| 代码修改验证 | edit/replace 后 `git diff --check` | 继续运行针对性测试 |

管道不是目的。如果中间结果需要模型判断、用户确认或工具调用之间存在强依赖，应拆成可验证阶段。

## 6. 命令选择边界

- `rg`：文本、日志、文档、配置中的字符串。
- `sg`：代码 AST 形状、语法节点、结构规则与代码重写。
- `fd`：文件路径集合。
- `sd`：不依赖语法结构的文本替换。
- `jq/yq`：JSON/YAML/XML 数据结构。
- `curl`：HTTP API；优先检查状态码和响应体。
- `zstd -d -c`：流式解压，不需要保留解压文件时优先。
- `duckdb`：需要 SQL 聚合 JSONL/Parquet/CSV 等数据时。
- `difft`：按语法结构比较代码变化。
- `delta`：提高 Git diff 可读性。
- `just`：复用项目任务，不重复发明脚本入口。

遇到工具缺失时：FastCtx 专用能力优先；其次使用已安装等价 CLI；最后才使用内置工具/手动处理。不要未经用户授权静默安装依赖。


## 7. 官方文档与版本来源速查

- **DSH/FastCtx 自身契约**：查看 [AUTHORITATIVE-SOURCES.md](AUTHORITATIVE-SOURCES.md) 的 DSH 与 FastCtx 两节；不要把别的 MCP 宿主或其他版本行为套过来。
- **Shell/Windows**：GNU Bash Manual、POSIX.1-2024、Git for Windows Technical Overview、MSYS2 Filesystem Paths。
- **结构与文本搜索**：ast-grep CLI Reference、ripgrep User Guide、fd 与 sd 上游 README/man page。
- **数据与网络**：jq Manual、Mike Farah yq docs、curl docs/Everything curl、zstd CLI manual、DuckDB CLI docs。
- **查看与比较**：Difftastic Manual、delta manual、bat、tokei、fzf、just 的上游手册。
- **MCP 命令适配**：mcp2cli 官方 Usage Guide；动态工具列表需从目标 server 实时发现。

调用前版本检查建议：

```bash
for tool in sg rg fd sd jq yq curl zstd duckdb difft delta just fzf bat tokei mcp2cli; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '%-12s %s\n' "$tool" "$(command -v "$tool")"
    "$tool" --version 2>/dev/null | head -n 1 || true
  fi
done
```

此脚本是轻量环境盘点，不替代工具自己的帮助文档；有些工具不支持 `--version`，需要按上游手册使用 `--help` 或 `version` 子命令。版本/参数输出异常时，不要继续猜参数。
