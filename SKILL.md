---
name: cmd-powershell-pitfalls
description: Use when writing or debugging .cmd/.bat scripts with embedded PowerShell, or when fixing hybrid script failures caused by cmd parsing quirks, variable expansion, quoting, and encoding edge cases.
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
