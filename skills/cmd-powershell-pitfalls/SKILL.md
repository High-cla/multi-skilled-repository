---
name: cmd-powershell-pitfalls
description: ALWAYS use BEFORE thinking, BEFORE writing/debugging .cmd/.bat scripts with embedded PowerShell, and BEFORE executing any Windows command operations. Trigger on: ANY task involving Windows batch files, PowerShell commands, cmd scripting, file encoding issues, path handling, special character escaping, variable expansion, pipeline operations, error handling, or when fixing hybrid script failures caused by cmd parsing quirks, quoting issues, and edge cases. This skill MUST be triggered before any Windows command operation or when about to think about shell scripting approaches.
---

# CMD + PowerShell 混合脚本避坑指南

## 1. 编码 (Code Page)

### `chcp 65001` 破坏变量展开

```batch
@echo off
chcp 65001 >nul
set "VAR=中文路径"
echo %VAR%   REM 可能输出乱码或空 — 65001 下 cmd 解析异常
```

**规则：**
- `chcp 65001` 后 cmd 对 `%VAR%` 的解析在某些 Windows 版本有 bug，尤其是路径含中文时
- 修复：不在 cmd 中用中文注释/输出，改用英文；或保持默认 936 (GBK)
- 最佳实践：批处理脚本避免中文字符，使用英文

### 推荐替代

```batch
@echo off
rem use English comments only
echo %VAR%
```

## 2. `for` 循环体中的括号 `)`

`for` 的 `()` 体用 `)` 关闭。如果命令本身含 `)`，必须用 `^` 转义。

### 错误示范

```batch
for %%f in (*.lua) do (
  echo addappid(%%a, 1)    REM 这里的 ) 被当作 for 体结束
)
```

### 正确做法

```batch
for %%f in (*.lua) do (
  echo addappid(%%a, 1^)   REM ^) 将 ) 转义为字面字符
)
```

**规则：** `for` 循环体内任何 `)` 都必须写作 `^)`。

## 3. 括号引起的重定向顺序问题

```batch
REM 错误 — 输出重定向被 ) 截断
(
  echo addappid(1, 2^)
) > out.txt

REM 正确 — 用 ^ 转义后输出正常
(
  echo addappid(1, 2^)
) > out.txt
```

## 4. `%~dp0` 路径处理

```batch
cd /d "%~dp0"    REM 进入脚本所在目录（含末尾 \）
```

**规则：**
- `%~dp0` 返回值**含**尾部 `\`（如 `C:\dir\`）
- 拼接文件时不需要额外加 `\`：`"%~dp0Steamtools.lua"`
- `%~dp0` 是运行时动态的，不会硬编码

### `~` 修饰符速查

| 语法       | 含义                  | 示例 (`C:\tools\script.cmd`) |
| ---------- | --------------------- | ---------------------------- |
| `%~dp0`    | 盘符+路径              | `C:\tools\`                  |
| `%~f0`     | 完整路径               | `C:\tools\script.cmd`        |
| `%~n0`     | 文件名（无扩展名）     | `script`                     |
| `%~x0`     | 扩展名                 | `.cmd`                       |
| `%~nx0`    | 文件名+扩展名          | `script.cmd`                 |
| `%~dpnx0`  | = `%~f0`                | 全路径                        |

## 5. cmd 行续 `^` 的引用限制

`^` 续行**只在引号外生效**。不能用来续接引号内的内容。

### 错误

```batch
REM 错误：^ 在 "" 内部是字面字符，不会续行
powershell -Command "Write-Host 'hello' ^
  'world'"
```

### 正确

```batch
REM 正确：每行作为独立的引号参数，PowerShell 拼接时插入空格
powershell -Command ^
  "$a=1;" ^
  "$b=2;" ^
  "Write-Host ($a+$b)"
```

**或单行：**

```batch
REM 最稳妥的方式：全部写在一行
powershell -Command "Write-Host 'hello world'"
```

## 6. PowerShell 嵌入 cmd 的引号逃逸

cmd 的 `"..."` 内**不支持** `\"` 作为转义。`\"` 在 cmd 解析中是 `\` 字面 + `"` 结束引号。

```batch
REM 错误：\" 会提前闭合 cmd 的字符串
powershell -Command "Write-Host \"hello\""   REM cmd 看到的是两个引号段

REM 正确：用单引号
powershell -Command "Write-Host 'hello'"

REM 正确：避免内层双引号
powershell -Command "Write-Host ('hello ' + 'world')"
```

**规则：** 在 `-Command "..."` 中永远不要用 `\"`。用：
- PowerShell 单引号 `'...'` 表达字面字符串
- `'prefix ' + $var` 拼接变量
- 或改用 `-EncodedCommand`

## 7. `Get-Location` 返回 `PathInfo` 非字符串

```powershell
$d = Get-Location               # PathInfo 对象
$d + "\file.lua"                 # 错误：PathInfo 不支持 +
$d.Path + "\file.lua"            # 正确
(Get-Location).Path + "\file.lua" # 正确
Join-Path (Get-Location) "file"  # 正确：Join-Path 接受对象
```

## 8. cmd 中 `$` 与 `%` 传递给 PowerShell

| 在 cmd 中写 | 传递给 PowerShell 的含义       |
| ----------- | ------------------------------ |
| `$_`        | 当前管道对象 (`$_`)             |
| `$var`      | PowerShell 变量                |
| `%VAR%`     | cmd 展开环境变量（先于 PS 执行）|
| `%%f` (for 内) | for 循环变量                |
| `%%` (for 外)  | 字面 `%%` 或 `%`（取决于位置）    |

**规则：** 在 cmd 的 `-Command "..."` 中：
- `$_` 是字面传递给 PowerShell 的 `$_`
- `%USERNAME%` 会在 cmd 层先展开成值，再传给 PowerShell

### `%` 传递给 PowerShell ForEach-Object

```batch
REM 在 for 循环外，% 可作为 PS 的 ForEach-Object 别名传递
REM 但为保险，始终用 ForEach-Object 全称
powershell -Command "Get-ChildItem | ForEach-Object { $_.Name }"
```

## 9. `if /i not` 字符串比较

```batch
if /i not "%%f"=="Steamtools.lua" (
  REM 大小写不敏感比较
)
```

注意 `.cmd` 中 `==` 前后不能加空格（除非空格是你想比较的一部分）。

## 10. `findstr` 正则过滤

```batch
REM 只保留纯数字的文件名
dir /b *.lua | findstr /r "^[0-9][0-9]*\.lua$"
```

**`findstr` 注意事项：**
- 正则语法有限，不支持 `\d`、`+`、`?`、`{n,m}` 等高级语法
- `^` 和 `$` 是行首行尾锚点
- `\.` 匹配字面点号
- 不支持非贪婪匹配

## 11. 管道 `|` 在 cmd 字符串中

```batch
REM 正确：| 在 "..." 内是字面字符，不会被 cmd 当作管道
powershell -Command "Get-ChildItem | Where-Object { $_.Length -gt 1kb }"
```

## 12. 延迟变量扩展 (Delayed Expansion)

```batch
setlocal enabledelayedexpansion
set "count=0"
for %%f in (*.lua) do (
  set /a count+=1
  REM 必须用 !count! 而非 %count%（for 内 %count% 不会更新）
  echo !count!: %%f
)
endlocal
```

**规则：** `for` / `if` 内修改并读取变量必须用 `!var!`，否则读到的是循环开始前的值。

## 13. `Set-Content` 编码陷阱

```powershell
# Windows PowerShell (≤ 5.1)：默认 UTF-8 With BOM
Set-Content path "text"               # UTF-8 + BOM
Set-Content path "text" -Encoding ASCII   # ASCII（无BOM）
Set-Content path "text" -Encoding UTF8    # UTF-8 + BOM (Win PS)
Set-Content path "text" -Encoding Default # ANSI (GBK)

# PowerShell 7+：默认 UTF-8 No BOM
Set-Content path "text"               # UTF-8 No BOM
```

**规则：**
- Lua/C 等工具读文件时 BOM 可能导致解析错误
- 写文本文件时指定 `-Encoding ASCII` 最安全
- PowerShell 7+ 默认 UTF8 No BOM，写脚本时指定版本

## 14. 错误处理

```batch
some_command
if %ERRORLEVEL% neq 0 (
  echo Failed with code %ERRORLEVEL%
  exit /b %ERRORLEVEL%
)

REM PowerShell 部分：
powershell -NoProfile -Command "..."
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
```

**规则：**
- cmd 用 `%ERRORLEVEL%` 获取上一个命令的退出码
- PowerShell 用 `$LASTEXITCODE` 获取原生程序退出码
- `exit /b` 退出脚本并设置退出码（不关闭终端）

## 15. 逐 `>>` 追加 vs 一次性重定向

```batch
REM 慢：每次 >> 打开/关闭文件
(for %%f in (*.lua) do echo %%f) > out.txt

REM 快：整个 for 输出一次重定向
(
  for %%f in (*.lua) do echo %%f
) > out.txt
```

**规则：** 尽量用 `(for ...) > file` 代替循环内 `>> file`。

## 16. .NET API 加速 PowerShell

```powershell
# 慢 (cmdlet)	          # 快 (.NET 直调)
Get-ChildItem *.lua	  [IO.Directory]::GetFiles($dir, '*.lua')
Get-Content file.txt	  [IO.File]::ReadAllLines($path)
Set-Content path txt	  [IO.File]::WriteAllText($path, $text)
Get-Location            (Get-Location).Path / $PWD.Path
Join-Path $d 'x.lua'    $d + '\x.lua'
```

## 17. 退出码检测

PowerShell 的退出码需要显式设置才能在 cmd 中获取：

```batch
powershell -NoProfile -Command "...; exit $LASTEXITCODE"
if %ERRORLEVEL% neq 0 echo PowerShell failed
```

## 18. `@echo off` 位置与调试

```batch
REM 错误：@echo off 前有输出会显示命令本身
echo starting...
@echo off

REM 正确：第一行就是 @echo off
@echo off
echo starting...

REM 调试时临时开启回显
@echo on
REM 调试代码...
@echo off
```

**规则：** `@echo off` 必须是脚本第一行（除注释外），否则之前的命令会回显。

## 19. PowerShell 执行策略绕过

```batch
REM 错误：未指定执行策略可能因系统设置失败
powershell -File script.ps1

REM 正确：显式指定执行策略
powershell -ExecutionPolicy Bypass -File script.ps1
powershell -Exec Bypass -Command "..."

REM 常用策略：
REM   Restricted - 不允许运行任何脚本 (默认)
REM   Bypass     - 不阻止任何脚本
REM   RemoteSigned - 本地脚本可运行，远程需签名
```

**规则：** 始终用 `-ExecutionPolicy Bypass` 确保脚本可执行。

## 20. 特殊字符转义表

| 字符 | cmd 转义 | PowerShell 转义 | 示例 |
|------|----------|-----------------|------|
| `^`  | `^^`     | `` `^ ``        | `echo ^^` → `^` |
| `&`  | `^&`     | `` `& ``        | `echo ^&` → `&` |
| `\|`  | `^\|`     | `` `\| ``         | `echo ^\|` → `\|` |
| `<`  | `^<`     | `` `< ``        | `echo ^<` → `<` |
| `>`  | `^>`     | `` `> ``        | `echo ^>` → `>` |
| `"`  | `\"` (无效) | `` `" ``       | 用单引号替代 |
| `'`  | 无需     | `''`            | `echo 'it''s'` → `it's` |
| `$`  | `$$`     | `` `$ ``        | `echo $$var` → `$var` |
| `%`  | `%%`     | `` `% ``        | `echo %%` → `%` |

**规则：** 嵌套调用时需双重转义，先满足外层再满足内层。

## 21. 路径含空格的处理

```batch
REM 错误：空格导致参数分裂
set path=C:\Program Files\app
cd %path%

REM 正确：始终用引号包裹
set "path=C:\Program Files\app"
cd "%path%"

REM PowerShell 同理
powershell -Command "cd 'C:\Program Files\app'"
powershell -Command "cd `"$env:ProgramFiles\app`""
```

**规则：** 路径变量赋值和使用时都要加引号：`set "var=value"` 和 `"%var%"`。

## 22. 环境变量作用域

```batch
REM cmd 设置环境变量
set MY_VAR=value           REM 当前进程
setx MY_VAR value          REM 用户级永久 (新终端生效)
setx MY_VAR value /M       REM 系统级永久 (需管理员)

REM PowerShell 设置
$env:MY_VAR = "value"      REM 当前进程
[Environment]::SetEnvironmentVariable("MY_VAR","value","User")    REM 用户级
[Environment]::SetEnvironmentVariable("MY_VAR","value","Machine") REM 系统级
```

**规则：**
- `set` 仅在当前会话有效
- `setx` 写入注册表，新终端生效
- PowerShell `$env:` 仅当前进程
- 跨进程持久化需用 `setx` 或 .NET API

## 23. 数组与集合处理

```batch
REM cmd 无原生数组，用延迟展开模拟
setlocal enabledelayedexpansion
set i=0
for %%f in (*.txt) do (
  set "file[!i!]=%%f"
  set /a i+=1
)

REM PowerShell 数组
$files = Get-ChildItem *.txt
$files[0]              # 访问元素
$files.Count           # 数量
$files | Where-Object { $_.Length -gt 100 }
```

**规则：** 复杂数据结构优先用 PowerShell 处理，cmd 只负责调用。

## 24. 正则表达式差异

```batch
REM cmd findstr 正则 (有限)
findstr /r "^[0-9]*\.txt$" files.txt

REM PowerShell Select-String (.NET 完整正则)
Select-String -Pattern "^\d+\.txt$" -Path files.txt
Get-ChildItem | Where-Object { $_.Name -match "^\d+\.txt$" }
```

**findstr 不支持但 PowerShell 支持：**
- `\d` `\w` `\s` 等快捷类
- `+` `?` `{n,m}` 量词
- 非贪婪匹配 `*?`
- 分组捕获 `()` 和反向引用

**规则：** 复杂正则用 PowerShell，简单过滤用 findstr。

## 25. 多行字符串处理

```batch
REM cmd 多行字符串困难，用 ^ 续行
set "sql=SELECT * ^
FROM users ^
WHERE id=1"

REM PowerShell 多行字符串 (推荐)
$sql = @"
SELECT *
FROM users
WHERE id=1
"@

REM 或用 Here-String
$text = @'
包含 "双引号" 和 $变量 不会被展开
'@
```

**规则：** 多行内容优先用 PowerShell 的 Here-String (`@"..."@`)。

## 26. 后台执行与静默模式

```batch
REM cmd 启动隐藏窗口
start /min powershell -WindowStyle Hidden -Command "..."
start /b powershell -Command "..."  REM 不创建新窗口

REM PowerShell 后台作业
Start-Job -ScriptBlock { ... }
Receive-Job -Id 1
Stop-Job -Id 1

REM 计划任务方式 (完全隐藏)
schtasks /Create /TN "MyTask" /TR "powershell -File script.ps1" /SC ONCE /ST 00:00
```

**规则：** 需要完全静默时用 `start /min` + `-WindowStyle Hidden`。

## 27. Unicode 与字节序标记 (BOM) 深度处理

```batch
REM 检查文件是否有 BOM
powershell -Command "$b=[IO.File]::ReadAllBytes('file.txt'); if($b[0]-eq 0xEF -and $b[1]-eq 0xBB -and $b[2]-eq 0xBF){'Has BOM'}else{'No BOM'}"

REM 移除 BOM
powershell -Command "$t=[IO.File]::ReadAllText('in.txt'); [IO.File]::WriteAllText('out.txt',$t,(New-Object Text.UTF8Encoding $false))"

REM 批量转换编码
powershell -Command "Get-ChildItem *.txt | ForEach-Object { $c=[IO.File]::ReadAllText($_.FullName); [IO.File]::WriteAllText($_.FullName,$c,(New-Object Text.UTF8Encoding $false)) }"
```

**规则：** Lua/C 解析器通常不支持 BOM，写文件时用 `UTF8Encoding($false)` 创建无 BOM 的 UTF-8。

## 28. 管道数据流与编码传递

```batch
REM 错误：cmd 管道传递 ANSI 编码给 PowerShell，中文变乱码
dir /b | powershell -Command "Get-StdIn | ForEach-Object { $_ }"

REM 正确：指定输入编码
dir /b | powershell -InputFormat Text -Command "Get-StdIn | ForEach-Object { $_ }"

REM 最佳实践：用 PowerShell 完整处理
powershell -Command "Get-ChildItem *.txt | ForEach-Object { $_.Name }"
```

**规则：**
- cmd 管道默认 ANSI (GBK)，PowerShell 默认 UTF-8
- 跨管道传递中文时，优先让 PowerShell 全程处理
- 或用 `[Console]::OutputEncoding` 统一编码

## 29. 临时文件竞争条件

```batch
REM 错误：多进程可能使用相同临时文件名
set tmp=%TEMP%\process.tmp

REM 正确：使用 GUID 保证唯一性
powershell -Command "$tmp=[IO.Path]::GetTempFileName()"

REM 或使用时间戳+PID
set tmp=%TEMP%\process_%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%RANDOM%.tmp
```

**规则：** 并发场景下临时文件必须用唯一标识（GUID/PID/时间戳）。

## 30. 权限提升检测

```batch
REM 检测是否管理员权限
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 需要管理员权限
    REM 自动请求提权
    powershell -Command "Start-Process cmd -ArgumentList '/c','%~f0' -Verb RunAs"
    exit /b
)

REM PowerShell 检测
powershell -Command "if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')) { exit 1 }"
```

**规则：** 需要管理员操作前先检测权限，必要时自动提权。

## 31. 长路径支持 (>260 字符)

```batch
REM 错误：默认不支持超过 260 字符的路径
cd C:\VeryLongPathThatExceedsMaxPathLimit...

REM 正确：启用长路径支持 (Windows 10 1607+)
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f

REM PowerShell 使用 \\?\ 前缀
powershell -Command "$path='\\?\C:\VeryLongPath...'; Get-ChildItem $path"
```

**规则：** 处理深层嵌套目录时启用长路径支持或使用 `\\?\` 前缀。

## 32. 超时与中断处理

```batch
REM 设置命令超时
powershell -Command "$p=[Diagnostics.Process]::Start('cmd','/c your_command'); if(!$p.WaitForExit(5000)){ $p.Kill(); exit 1 }"

REM cmd 原生超时 (ping 技巧)
ping -n 6 127.0.0.1 >nul REM 约 5 秒延迟

REM PowerShell Start-Sleep
powershell -Command "Start-Sleep -Seconds 5"
```

**规则：** 长时间运行的命令必须设置超时机制防止挂起。

## 33. 日志记录最佳实践

```batch
REM 带时间戳的日志
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,4%-%dt:~4,2%-%dt:~6,2% %dt:~8,2%:%dt:~10,2%:%dt:~12,2%"

echo [%timestamp%] Starting process... >> "%~dp0script.log"

REM PowerShell 日志
powershell -Command "Add-Content 'script.log' \"[$(Get-Date 'yyyy-MM-dd HH:mm:ss')] Message\""
```

**规则：** 所有生产脚本必须记录带时间戳的操作日志。

## 34. 返回值标准化

```batch
REM 定义标准退出码
set EXIT_SUCCESS=0
set EXIT_ERROR_ARGS=1
set EXIT_ERROR_FILE=2
set EXIT_ERROR_NETWORK=3
set EXIT_ERROR_PERMISSION=4

REM 统一出口
goto :EOF

:error
echo Error: %1 >&2
exit /b %EXIT_ERROR_ARGS%
```

**规则：** 使用标准化的退出码便于调用方判断错误类型。

## 35. 配置文件读取

```batch
REM 读取 INI 配置 (cmd 原生不支持，用 PowerShell)
powershell -Command ^
  "$ini=@{}; Get-Content 'config.ini' | ForEach-Object { if($_ -and $_[0]-ne ';' -and $_.Contains('=')) { $k,$v=$_.Split('=',2); $ini[$k.Trim()]=$v.Trim() } }; Write-Output $ini['key']"

REM 或读取 JSON 配置
powershell -Command "(Get-Content 'config.json' | ConvertFrom-Json).setting"
```

**规则：** 复杂配置用 JSON/YAML，通过 PowerShell 解析；简单配置用环境变量。

## 检查清单

- [ ] `)` 在 `for` 体内是否用 `^)` 转义
- [ ] `"..."` 内无 `\"`（用单引号替代）
- [ ] `Get-Location` 是否调用了 `.Path`
- [ ] `chcp 65001` 后无中文/特殊字符变量
- [ ] `for` 内修改变量是否用了延迟展开 `!var!`
- [ ] `Set-Content` 指定了正确编码
- [ ] `%~dp0` 路径拼接无多余 `\`
- [ ] PowerShell `$_` 在 cmd 中无冲突
- [ ] `.ps1` 执行策略用 `-ExecutionPolicy Bypass`
- [ ] `@echo off` 是否为第一行
- [ ] 路径含空格时是否用引号包裹
- [ ] 特殊字符是否按层级正确转义
- [ ] 多行字符串是否用 PowerShell Here-String
- [ ] 输出文件是否确认无 BOM 问题
- [ ] 管道传递中文时是否统一编码
- [ ] 临时文件是否使用唯一标识
- [ ] 需要管理员权限时是否先检测
- [ ] 长路径是否启用支持或使用 `\\?\` 前缀
- [ ] 长时间命令是否设置超时
- [ ] 是否有带时间戳的日志记录
- [ ] 退出码是否标准化
- [ ] 配置文件格式是否合适
