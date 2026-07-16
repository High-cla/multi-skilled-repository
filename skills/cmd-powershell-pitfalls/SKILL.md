---
name: cmd-powershell-pitfalls
description: "Windows CMD 和 PowerShell 错误排查与陷阱规避指南，含跨平台差异和修复模式"
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

## 2. `for` 循环体中的括号 `)`

`for` 的 `()` 体用 `)` 关闭。如果命令本身含 `)`，必须用 `^` 转义。

```batch
REM 错误
for %%f in (*.lua) do (
  echo addappid(%%a, 1)    REM 这里的 ) 被当作 for 体结束
)

REM 正确
for %%f in (*.lua) do (
  echo addappid(%%a, 1^)   REM ^) 将 ) 转义为字面字符
)
```

**规则：** `for` 循环体内任何 `)` 都必须写作 `^)`。

## 3. 括号引起的重定向顺序问题

同第 2 条，`()` 体内的重定向需注意 `)` 被截断。

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

## 7. `Get-Location` 返回 `PathInfo` 非字符串

```powershell
$d = Get-Location               # PathInfo 对象
$d + "\file.lua"                 # 错误
$d.Path + "\file.lua"            # 正确
```

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
setlocal enabledelayedexpansion
set "count=0"
for %%f in (*.lua) do (
  set /a count+=1
  echo !count!: %%f
)
endlocal
```

**规则：** `for`/`if` 内修改并读取变量必须用 `!var!`。

## 13. `Set-Content` 编码陷阱

```powershell
# Windows PowerShell (<= 5.1)：默认 UTF-8 With BOM
Set-Content path "text"               # UTF-8 + BOM
Set-Content path "text" -Encoding ASCII   # ASCII（无BOM）

# PowerShell 7+：默认 UTF-8 No BOM
Set-Content path "text"               # UTF-8 No BOM
```

## 14. 错误处理

```batch
some_command
if %ERRORLEVEL% neq 0 (
  echo Failed with code %ERRORLEVEL%
  exit /b %ERRORLEVEL%
)
```

**规则：** cmd 用 `%ERRORLEVEL%`，PowerShell 用 `$LASTEXITCODE`。

## 15. 逐 `>>` 追加 vs 一次性重定向

```batch
REM 快：整个 for 输出一次重定向
(
  for %%f in (*.lua) do echo %%f
) > out.txt
```

## 16. .NET API 加速 PowerShell

| 慢 (cmdlet) | 快 (.NET 直调) |
|---|---|
| `Get-ChildItem *.lua` | `[IO.Directory]::GetFiles($dir, '*.lua')` |
| `Get-Content file.txt` | `[IO.File]::ReadAllLines($path)` |
| `Set-Content path txt` | `[IO.File]::WriteAllText($path, $text)` |

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

## 19. PowerShell 执行策略绕过

```batch
powershell -ExecutionPolicy Bypass -File script.ps1
```

## 20. 特殊字符转义表

| 字符 | cmd 转义 | PowerShell 转义 |
|------|----------|-----------------|
| `^` | `^^` | `` `^ `` |
| `&` | `^&` | `` `& `` |
| `\|` | `^\|` | `` `\| `` |
| `<`/`>` | `^<`/`^>` | `` `< ``/`` `> `` |
| `"` | `\"` (无效) | 用单引号替代 |
| `$` | `$$` | `` `$ `` |
| `%` | `%%` | `` `% `` |

## 21. 路径含空格的处理

```batch
set "path=C:\Program Files\app"
cd "%path%"
```

## 22. 环境变量作用域

| 级别 | cmd | PowerShell |
|------|-----|------------|
| 当前进程 | `set VAR=val` | `$env:VAR = "val"` |
| 用户永久 | `setx VAR val` | `[Environment]::SetEnvironmentVariable("VAR","val","User")` |
| 系统永久 | `setx VAR val /M` | `[Environment]::SetEnvironmentVariable("VAR","val","Machine")` |

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

## 26. 后台执行

```batch
start /min powershell -WindowStyle Hidden -Command "..."
```

## 27. Unicode 与 BOM

写文件时用 `UTF8Encoding($false)` 创建无 BOM 的 UTF-8。

## 28. 管道编码传递

cmd 管道默认 ANSI (GBK)，PowerShell 默认 UTF-8。跨管道传中文时优先让 PowerShell 全程处理。

## 29. 临时文件竞争条件

并发场景下必须用唯一标识 (GUID/PID/时间戳)。

## 30. 权限提升检测

```batch
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    powershell -Command "Start-Process cmd -ArgumentList '/c','%~f0' -Verb RunAs"
    exit /b
)
```

## 31. 长路径支持 (>260 字符)

Windows 10 1607+ 启用长路径支持或使用 `\\?\` 前缀。

## 32. 超时与中断

长时间运行命令必须设置超时机制。
```powershell
$p=[Diagnostics.Process]::Start('cmd','/c command'); if(!$p.WaitForExit(5000)){ $p.Kill(); exit 1 }
```

## 33. 日志记录

所有生产脚本必须记录带时间戳的操作日志。

## 34. 返回值标准化

使用标准化的退出码便于调用方判断错误类型。

## 35. 配置文件读取

复杂配置用 JSON/YAML，通过 PowerShell 解析；简单配置用环境变量。

## Git Bash 与 MSYS2 路径转换

Git Bash 的 MSYS2 层自动将 `/` 开头的参数（如 `/PID`）转换为 Windows 路径，导致传给 `powershell.exe` 的参数被破坏。

| 问题 | 表现 | 修复 |
|------|------|------|
| `/PID` -> 路径 | `spawnSync powershell.exe ETIMEDOUT` | 设 `MSYS2_ARG_CONV_EXCL=*` |
| 路径参数丢失 | 传参失败 | 用 `//` 前缀绕过转换 |

## 重复安装

opencode 同时通过 npm 和 WinGet 安装时，PATH 顺序决定生效版本。当前仅保留 npm 版。

## 检查清单

- [ ] `)` 在 `for` 体内是否用 `^)` 转义
- [ ] `"..."` 内无 `\"`（用单引号替代）
- [ ] `Get-Location` 是否调用了 `.Path`
- [ ] `chcp 65001` 后无中文/特殊字符变量
- [ ] `for` 内修改变量是否用了延迟展开 `!var!`
- [ ] `Set-Content` 指定了正确编码
- [ ] `%~dp0` 路径拼接无多余 `\`
- [ ] `.ps1` 执行策略用 `-ExecutionPolicy Bypass`
- [ ] `@echo off` 是否为第一行
- [ ] 路径含空格时是否用引号包裹
- [ ] 特殊字符是否按层级正确转义
- [ ] 输出文件是否确认无 BOM 问题
- [ ] 管道传递中文时是否统一编码
- [ ] 需要管理员权限时是否先检测
- [ ] 长路径是否启用支持或使用 `\\?\` 前缀
- [ ] 长时间命令是否设置超时
- [ ] 退出码是否标准化
