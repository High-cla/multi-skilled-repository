param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(5, 7)]
    [int]$ExpectedMajor
)

$ErrorActionPreference = 'Stop'
$actualMajor = $PSVersionTable.PSVersion.Major
if ($actualMajor -ne $ExpectedMajor) {
    throw "Expected PowerShell major $ExpectedMajor but running $actualMajor ($($PSVersionTable.PSVersion))"
}

$tempFile = Join-Path ([IO.Path]::GetTempPath()) ("ps-encoding-" + [Guid]::NewGuid().ToString('N') + ".txt")
try {
    $encoding = [Text.UTF8Encoding]::new($false)
    [IO.File]::WriteAllText($tempFile, '中文 UTF-8 no BOM', $encoding)
    [byte[]]$bytes = [IO.File]::ReadAllBytes($tempFile)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        throw 'UTF-8 output unexpectedly contains a BOM'
    }
    $roundTrip = [Text.Encoding]::UTF8.GetString($bytes)
    if ($roundTrip -ne '中文 UTF-8 no BOM') {
        throw "UTF-8 round trip failed: $roundTrip"
    }

    $process = Start-Process -FilePath $env:ComSpec -ArgumentList '/d', '/c', 'exit 7' -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 7) {
        throw "Native process exit code propagation failed: expected 7, got $($process.ExitCode)"
    }

    $policies = Get-ExecutionPolicy -List
    if (-not $policies -or $policies.Count -lt 1) {
        throw 'Get-ExecutionPolicy -List returned no scope information'
    }

    Write-Output ("PASS PowerShell {0}; UTF8NoBOM bytes={1}; nativeExitCode={2}; policyScopes={3}" -f $PSVersionTable.PSVersion, $bytes.Length, $process.ExitCode, $policies.Count)
}
finally {
    Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
}
