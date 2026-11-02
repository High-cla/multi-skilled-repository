---
name: cmd-powershell-pitfalls
description: "Windows CMD 和 PowerShell 错误排查与陷阱规避指南，含跨平台差异和修复模式"
---

# CMD + PowerShell 混合脚本避坑指南


## 1. 编码与代码页

`chcp` 只改变当前控制台的活动代码页，不会改变 CMD 的变量展开规则、PowerShell 文件编码或所有子进程的编码。不要把 `chcp 65001` 描述成会破坏 `%VAR%` 展开，也不要假设所有系统默认都是 936/GBK。

**规则：**
- 区分控制台输入/输出代码页、PowerShell 的 `Console.InputEncoding` / `Console.OutputEncoding`、发给原生程序的 `$OutputEncoding`，以及文件读写的 `-Encoding`；它们不是同一个设置。
- 编码问题通常表现为乱码、替换字符或字节损坏，不应归因于 CMD 的变量展开机制。
- 文件读写在边界显式指定编码；先确认目标程序实际支持 UTF-8、BOM 和代码页。
- 不要为了避免乱码而强制把脚本、参数或数据改成英文；应使用明确且兼容的编码。

## 2. `for` 循环体中的括号 `)`

`for` 的括号块由未转义的 `)` 结束。在括号块内，只有当右括号会被 CMD 解析为块结束符时才需要写成 `^)`；不要把所有字符串中的右括号都机械替换。

```batch
REM 错误
for %%f in (*.lua) do (
  echo addappid(%%f, 1)    REM 这里的 ) 被当作 for 体结束
)

REM 正确
for %%f in (*.lua) do (
  echo addappid(%%f, 1^)   REM ^) 将 ) 转义为字面字符
)
```

**规则：** 对 CMD 解析器会识别为块结束符的右括号使用 `^)`；能用引号或拆分命令避免复杂解析时，优先简化结构。

## 3. 括号块与重定向

对整个命令组重定向时，把重定向放在关闭括号之后；括号块内命令参数中的字面 `)` 仍需按 CMD 规则处理。

```batch
(
  echo first
  echo second
) > out.txt
```

这会把整个命令组的输出写入 `out.txt`。不要把重定向放到一个尚未闭合的块中，也不要把参数里的 `)` 与关闭命令组的 `)` 混为一谈。

## 4. `%~dp0` 路径处理

```batch
cd /d "%~dp0"    REM 进入脚本所在目录（含末尾 \）
```

**规则：**
- `%~dp0` 返回值含尾部 `\`（如 `C:\dir\`）
- 拼接文件时不需要额外加 `\`：`"%~dp0file.lua"`

### `~` 修饰符速查

| 语法 | 含义 | 示例 |
|------|------|------|
| `%~dp0` | 盘符+路径 | `C:\tools\` |
| `%~f0` | 完整路径 | `C:\tools\script.cmd` |
| `%~n0` | 文件名（无扩展名） | `script` |
| `%~x0` | 扩展名 | `.cmd` |

## 5. cmd 行续 `^` 的引用限制

`^` 续行只在引号外生效。

```batch
REM 错误：^ 在 "" 内部是字面字符
powershell -Command "Write-Host 'hello' ^
  'world'"

REM 正确
powershell -Command ^
  "$a=1;" ^
  "$b=2;" ^
  "Write-Host ($a+$b)"
```

## 6. PowerShell 嵌入 cmd 的引号逃逸

cmd 的 `"..."` 内不支持 `\"` 作为转义。

```batch
REM 错误
powershell -Command "Write-Host \"hello\""

REM 正确：用单引号
powershell -Command "Write-Host 'hello'"
```


## 7. 路径对象与路径拼接

`Get-Location` 返回 `PathInfo`。需要构造路径时使用路径 API，而不是依赖对象与字符串的隐式转换：

```powershell
$dir = (Get-Location).Path
$file = Join-Path $dir 'file.lua'
# 或
$file = Join-Path (Get-Location) 'file.lua'
```

**规则：** 优先 `Join-Path`、`Resolve-Path` 和 `[IO.Path]::Combine()`；不要手工拼接路径分隔符。

## 8. cmd 中 `$` 与 `%` 传递给 PowerShell

| 在 cmd 中写 | 传递给 PowerShell |
|-------------|-------------------|
| `$_` | 当前管道对象 (`$_`) |
| `$var` | PowerShell 变量 |
| `%VAR%` | cmd 展开环境变量（先于 PS 执行） |
| `%%f` (for 内) | for 循环变量 |

## 9. `if /i not` 字符串比较

```batch
if /i not "%%f"=="file.lua" (
  REM 大小写不敏感比较
)
```

注意 `==` 前后不能加空格。

## 10. `findstr` 正则过滤

```batch
dir /b *.lua | findstr /r "^[0-9][0-9]*\.lua$"
```

**`findstr` 局限：** 不支持 `\d`、`+`、`?`、`{n,m}`，不支持非贪婪。

## 11. 管道 `|` 在 cmd 字符串中

```batch
REM 正确：| 在 "..." 内不会被 cmd 当作管道
powershell -Command "Get-ChildItem | Where-Object { $_.Length -gt 1kb }"
```


## 12. 延迟变量扩展 (Delayed Expansion)

```batch
@echo off
setlocal EnableDelayedExpansion
set "count=0"
for %%f in (*.lua) do (
  set /a count+=1
  echo !count!: %%f
)
endlocal
```

**规则：**
- CMD 在解析括号块时会提前展开 `%var%`；需要读取块内更新后的值时，才启用延迟展开并用 `!var!`。
- 延迟展开会把文件名/数据中的字面 `!` 当成展开边界，可能损坏内容。处理任意文件名时，优先禁用延迟展开、拆分代码块或改用 PowerShell。


## 13. `Set-Content` 编码陷阱

Windows PowerShell 5.1 与 PowerShell 7+ 的默认值不同，而且 Windows PowerShell 5.1 的不同 cmdlet 默认编码并不统一。

```powershell
# Windows PowerShell 5.1：Set-Content 默认使用系统活动代码页
Set-Content -Path .\out.txt -Value 'text'

# Windows PowerShell 5.1：-Encoding UTF8 会写入 UTF-8 BOM
Set-Content -Path .\out.txt -Value 'text' -Encoding UTF8

# PowerShell 7+：默认 UTF-8 No BOM；也可显式指定
Set-Content -Path .\out.txt -Value 'text' -Encoding utf8NoBOM

# 需要在 Windows PowerShell 5.1 写 UTF-8 No BOM 时
[IO.File]::WriteAllText(
  '.\out.txt',
  'text',
  [Text.UTF8Encoding]::new($false)
)
```

**规则：** 明确目标版本和文件格式；不要把 Windows PowerShell 5.1 的 `Set-Content` 默认值说成 UTF-8 BOM。覆盖文件、追加文件和重定向运算符也要分别查对应 cmdlet 的编码规则。


## 14. 错误处理

```batch
some_command
if errorlevel 1 (
  echo Command failed
  exit /b 1
)
```

**规则：**
- CMD 中 `if errorlevel N` 表示退出码大于或等于 N；它适合常见的正数失败码判断。
- 在括号块中，`%ERRORLEVEL%` 会在块解析时展开，可能读到旧值；需要当前值时使用适当的延迟展开，或把判断拆到块外。
- PowerShell 中，`$LASTEXITCODE` 用于最近的原生程序退出码；PowerShell cmdlet 的成功/失败还要检查 `$?`、错误记录或 `-ErrorAction Stop`。
- 跨 CMD/PowerShell 边界时，显式使用 `exit <code>` 将需要传播的状态传回调用方。

## 15. 逐 `>>` 追加 vs 一次性重定向

每次循环都执行 `>> out.txt` 会反复打开/追加/关闭文件。将整个命令组重定向为 `> out.txt` 可让 CMD 对整组命令只建立一次重定向。

```batch
REM 整个 for 输出一次重定向
(
  for %%f in (*.lua) do echo %%f
) > out.txt
```

这只是减少重复打开操作的常见写法；真实收益取决于文件系统、缓冲和输出量，应按 workload 测量。

## 16. 比较 PowerShell cmdlet 与 .NET API

直接调用 .NET API 可以减少部分 PowerShell 对象管线和 cmdlet 开销，但**不能普遍断言更快或更省内存**；还要比较是否物化完整结果、编码、异常语义和资源释放。

| 需求 | 可比较的实现 | 需要注意 |
|---|---|---|
| 枚举文件 | `Get-ChildItem -File` / `[IO.Directory]::EnumerateFiles()` | `EnumerateFiles()` 惰性枚举；`GetFiles()` 一次性返回数组 |
| 逐行读取 | `Get-Content` / `[IO.File]::ReadLines()` | `ReadAllLines()` 会把全部行加载到内存；大文件优先流式处理 |
| 写入已存在的字符串 | `Set-Content` / `[IO.File]::WriteAllText()` | 显式指定编码；超大内容用流式 writer，不要先构造重复的大字符串 |

选择前确认 PowerShell 版本和目标编码，在代表性输入上 benchmark，并测量峰值内存；小文件/少量对象时差异可能不值得牺牲可读性。

## 17. 退出码检测

```batch
powershell -NoProfile -Command "...; exit $LASTEXITCODE"
if %ERRORLEVEL% neq 0 echo PowerShell failed
```

## 18. `@echo off` 位置

```batch
REM 正确：第一行就是 @echo off
@echo off
echo starting...
```


## 19. PowerShell 执行策略

不要把 `-ExecutionPolicy Bypass` 作为每个脚本的默认启动参数，也不要把它描述成保证脚本可执行的通用修复。

```powershell
# 先检查有效策略及其作用域
Get-ExecutionPolicy -List
Get-ExecutionPolicy
```

**规则：**
- 优先遵守机器/组织策略，确认脚本来源、签名和信任状态。
- Execution Policy 是纵深防御机制，不是安全边界；它也不能覆盖 Group Policy 设置的 `MachinePolicy` / `UserPolicy`。
- 只有在用户/管理员明确授权、且不违反组织策略时，才考虑对单次进程使用临时策略；不要永久放宽 `CurrentUser` 或 `LocalMachine`。
- `Bypass` 会取消阻止、警告和提示；不能用它绕过安全审查或执行未知脚本。


## 20. CMD 与 PowerShell 的分层转义

CMD 先解析外层命令行，PowerShell 再解析传入的脚本文本。不存在一张适用于所有嵌套层级的通用转义表。

- CMD 中未被引号保护的 `&`、`|`、`<`、`>`、`^` 和括号等字符可能具有控制含义；`^` 的行为取决于所在解析层和引号状态。
- 批处理文件中的 `%VAR%` 是 CMD 环境变量展开；`%%f` 是批处理文件中的 FOR 变量写法（交互式 CMD 通常写 `%f`）。
- `$` 不是 CMD 环境变量展开符；不要用 `$$` 作为 CMD 的通用转义。
- PowerShell 字符串使用 PowerShell 自己的单引号/双引号和反引号规则；双引号字符串会展开变量，单引号字符串是字面字符串。
- 对复杂脚本，写入独立 `.ps1` 文件并使用明确参数传递，通常比嵌套多层引号可靠。


## 21. 路径含空格的处理

```batch
REM 不要使用 path 作为临时变量名；CMD 的环境变量名不区分大小写，
REM path 与 PATH 相同，可能覆盖当前进程的搜索路径。
set "appPath=C:\Program Files\app"
cd /d "%appPath%"
```

**规则：** 路径参数始终正确引用；临时变量使用 `appPath`、`targetDir` 等名称，不覆盖系统变量 `PATH`。


## 22. 环境变量作用域

| 级别 | CMD | PowerShell |
|---|---|---|
| 当前进程 | `set VAR=value` | `$env:VAR = 'value'` |
| 用户永久 | `setx VAR value` | `[Environment]::SetEnvironmentVariable('VAR','value','User')` |
| 系统永久 | `setx VAR value /M` | `[Environment]::SetEnvironmentVariable('VAR','value','Machine')` |

**注意：**
- `set` 和 `$env:` 只修改当前进程及其后代进程的环境。
- `setx` 写入注册表，通常只影响之后启动的进程，不会更新当前 CMD/PowerShell 会话。
- Microsoft 文档注明 `setx` 写入值有 1024 字符上限，超出可能被截断；它还会展开环境变量引用。不要用它不加检查地追加或重写长 `PATH`。
- 系统级变量修改需要相应权限；除非用户明确要求，不要持久修改机器环境。

## 23. 数组与集合

复杂数据结构优先用 PowerShell，cmd 只负责调用。

## 24. 正则表达式差异

复杂正则用 PowerShell (Select-String)，简单过滤用 findstr。

## 25. 多行字符串

```powershell
$sql = @"
SELECT *
FROM users
WHERE id=1
"@
```


## 26. 后台执行与窗口可见性

`start /min` 是最小化，不等于隐藏；`-WindowStyle Hidden` 则会隐藏进程窗口，不应作为常规后台执行方式。

**规则：**
- 长任务优先使用可观察的 job/process supervisor：保留 job id、状态、输出、退出码和取消能力。
- 只有产品需求明确要求无窗口运行时，才使用隐藏窗口；同时仍需可审计的日志、退出状态和停止机制。
- 无 TTY 环境下不要依赖交互式确认、前台输入或用户手动关闭窗口。

## 27. Unicode 与 BOM

写文件时用 `UTF8Encoding($false)` 创建无 BOM 的 UTF-8。


## 28. 管道数据流与编码传递

不要笼统地说 CMD 管道固定使用 ANSI/GBK、PowerShell 管道固定使用 UTF-8。实际字节行为取决于 Windows 代码页、PowerShell 版本、控制台设置和目标原生程序。

**规则：**
- `chcp` 只更改控制台代码页；它不等同于文件编码，也不控制所有 PowerShell 到原生程序的管道编码。
- Windows PowerShell 5.1 与 PowerShell 7+ 的文件输出、原生程序输入输出默认值不同；特别区分 `$OutputEncoding`（PowerShell 发往原生程序）与 `Console.OutputEncoding`（控制台）。
- 跨进程传递文本时，优先使用明确的 UTF-8 文件/协议或能声明编码的接口；避免依赖当前机器的本地代码页。
- 遇到乱码时先检查两端实际字节和编码，再调整代码页/编码参数。

## 29. 临时文件竞争条件

并发场景应使用系统临时目录、GUID 或具备原子 `CreateNew` 语义的 API 创建临时文件。PID/时间戳可以参与命名，但单独使用不能保证跨进程/跨重启唯一；不要采用“先检查文件不存在，再普通创建”的非原子流程。任务完成后在 `finally` 中清理，保留文件时需明确所有权和生命周期。


## 30. 权限提升与 UAC

不要在检测到非管理员后自动重启整份脚本并请求管理员权限。

**规则：**
- 默认以当前权限执行；先区分哪些具体操作确实需要管理员权限。
- 需要提权时说明目标、影响范围和副作用，并取得用户明确授权；只提升必要的单个操作，不把整个工作流无条件提升。
- `net session` 依赖 Server 服务状态，不适合作为所有 Windows 环境的通用管理员检测。
- 对安全敏感的操作检查有效访问令牌/实际操作结果；不能把“用户属于 Administrators 组”简单等同于当前进程已提升。


## 31. 长路径支持 (>260 字符)

Windows 长路径支持不是只改一个注册表值就能让所有程序都支持。

- Win32 长路径通常需要系统启用 `LongPathsEnabled`，并且应用程序 manifest 声明 `longPathAware`；旧程序仍可能受 `MAX_PATH` 限制。
- `\\?\` 是面向支持它的 Win32 API 的路径前缀，不是所有 shell、CLI、库或相对路径都能通用使用。
- 修改系统级注册表需要权限，并且不会让未适配的程序自动获得长路径能力。先确认调用链中的每个工具是否支持。


## 32. 超时与中断

长任务应使用能够管理整个进程树的超时/取消机制。

**规则：**
- 仅对父进程调用 `Kill()` 可能留下孙进程；需要确认运行时是否支持整个进程树终止，并等待清理完成。
- 超时应有明确 deadline、取消传播、退出码、标准输出/错误收集和清理结果。
- 优先使用宿主任务管理器、FastCtx job、CI runner 或成熟 supervisor；不要把一个简单的 `WaitForExit` 示例当作跨版本可靠的进程树管理器。


## 33. 日志记录

不是所有脚本都必须写时间戳日志。日志需求取决于脚本是否承担生产运维、审计、排错或长任务追踪职责。

**规则：**
- 对需要审计/恢复的任务记录开始、结束、关键状态和退出码；对短小的一次性命令，不强制创建日志。
- 不记录密码、token、个人敏感信息和无必要的完整载荷。
- 长期日志设置大小/保留策略；并发写日志时使用独立文件或锁。


## 34. 返回值标准化

为脚本/项目定义稳定的退出码契约，调用方据此区分成功、参数错误、外部依赖失败和权限拒绝等类别。

**规则：** 退出码含义由项目接口定义；不要声称存在适用于所有 Windows 脚本的通用业务错误码表。

## 35. 配置文件读取

- JSON 可使用 PowerShell 内置的 `ConvertFrom-Json` / `ConvertTo-Json`，但需核验目标 PowerShell 版本对深度、日期、数值和大整数的处理。
- YAML 不是 Windows PowerShell / PowerShell 7 的通用内置解析器；使用已安装且版本确认的模块，或优先使用 Mike Farah `yq`。不要假设 `ConvertFrom-Yaml` 在干净环境中存在。
- 简单部署参数优先使用环境变量；复杂/需要类型验证的配置应使用正式解析器和 schema，而不是正则/字符串切割。


## Git Bash 与 MSYS2 路径转换

MSYS2 runtime 会把看起来像 POSIX 路径的参数/环境变量转换为 Windows 路径。某些原生 Windows CLI 的选项值可能因此被误转换。

**规则：**
- 先依据目标程序实际收到的 argv 复现问题，再使用 `MSYS2_ARG_CONV_EXCL` 排除特定参数前缀；该变量支持 `*` 或分号分隔的前缀列表。
- 优先排除最窄的选项前缀，不要全局禁用所有参数转换，除非已确认该命令所有参数都不需要 MSYS 路径转换。
- 不把 `//` 当作跨工具通用的绕过方案；实际转换规则以 Git for Windows/MSYS2 版本文档为准。

## 多来源重复安装

同一 CLI 可能通过 npm、WinGet、Scoop、Cargo 或系统包管理器重复安装；PATH 顺序和 shell 命令解析规则决定实际执行哪一个。使用 `where.exe`、PowerShell `Get-Command -All` 或 Bash `command -v` / `type -a` 检查所有解析结果，再对实际路径查询版本。不要在未确认调用链前自动删除任何一份安装。


## 检查清单

- [ ] CMD 括号块中的未转义 `)` 是否会提前结束代码块
- [ ] 多层 CMD/PowerShell 引号是否按两层解析分别验证
- [ ] 是否避免把 `PATH` 当作普通临时变量覆盖
- [ ] 括号块中是否存在提前展开的 `%VAR%`
- [ ] 启用延迟展开时是否可能损坏字面 `!`
- [ ] PowerShell 5.1 与 7+ 的编码默认值是否区分
- [ ] 文件读写与原生程序管道是否明确指定/核验编码
- [ ] `$LASTEXITCODE`、`$?` 和 CMD `ERRORLEVEL` 是否用在正确边界
- [ ] 是否检查并遵守组织执行策略，而不是默认 Bypass
- [ ] 是否避免未经授权的 UAC 自动提权
- [ ] 长路径是否同时满足 OS 设置与应用 manifest/工具能力
- [ ] 超时能否停止整个子进程树并等待清理
- [ ] 日志是否符合运维需求且未泄露敏感信息
- [ ] `setx` 是否避开 1024 字符截断与 PATH 风险
- [ ] MSYS2 参数转换是否按最窄前缀处理
