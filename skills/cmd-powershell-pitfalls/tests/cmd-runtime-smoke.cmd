@echo off
setlocal DisableDelayedExpansion
set "OUT=%TEMP%\cmd-runtime-smoke-%RANDOM%-%RANDOM%.txt"
set "COUNT=%TEMP%\cmd-runtime-count-%RANDOM%-%RANDOM%.txt"

REM A right parenthesis that would close a parsed block must be escaped.
(
  for %%F in (fixture) do (
    echo addappid(123, 1^)
  )
) > "%OUT%"
findstr /x /c:"addappid(123, 1)" "%OUT%" >nul
if errorlevel 1 (
  del "%OUT%" "%COUNT%" 2>nul
  exit /b 41
)

REM Delayed expansion is needed to read a variable updated inside the block.
setlocal EnableDelayedExpansion
set "N=0"
for %%F in (one two) do (
  set /a N+=1
  echo !N!>>"%COUNT%"
)
endlocal
findstr /x /c:"2" "%COUNT%" >nul
if errorlevel 1 (
  del "%OUT%" "%COUNT%" 2>nul
  exit /b 42
)

REM Literal exclamation marks are preserved while delayed expansion is off.
> "%OUT%" echo literal!bang
findstr /x /c:"literal!bang" "%OUT%" >nul
if errorlevel 1 (
  del "%OUT%" "%COUNT%" 2>nul
  exit /b 43
)

REM PowerShell's explicit exit code must propagate to CMD.
powershell.exe -NoProfile -NonInteractive -Command "exit 7"
if errorlevel 8 (
  del "%OUT%" "%COUNT%" 2>nul
  exit /b 44
)
if not errorlevel 7 (
  del "%OUT%" "%COUNT%" 2>nul
  exit /b 45
)

del "%OUT%" "%COUNT%" 2>nul
exit /b 0
