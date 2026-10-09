#Requires -Version 5.1
<#
.SYNOPSIS
    프로젝트 거버넌스 검사

.DESCRIPTION
    다음 세 가지 항목을 검사하고 결과를 출력합니다.

    1. 비밀값 검사   : src/ 내 API_KEY, password, secret, token 패턴
    2. 절대 경로 검사: C:\, D:\, E:\ 하드코딩
    3. 하드코딩 검사 : 특정 곡명(UPGRADE, 디저트, 떠나고) — fixture 폴더 제외

    모두 통과 시 exit 0, 하나라도 실패 시 exit 1.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OverallPass = $true

function Write-CheckResult {
    param(
        [string]$Label,
        [bool]$Passed,
        [string[]]$Hits
    )
    if ($Passed) {
        Write-Host "[PASS] $Label"
    } else {
        Write-Host "[FAIL] $Label"
        foreach ($Hit in $Hits) {
            Write-Host "       $Hit"
        }
    }
}

# ---------------------------------------------------------------------------
# 1. 비밀값 검사 — src/ 내 API_KEY, password, secret, token (대소문자 무시)
# ---------------------------------------------------------------------------
$SecretPattern = 'API_KEY|password|secret|token'
$SecretHits = @(
    Get-ChildItem -Path (Join-Path $ProjectRoot 'src') -Recurse -File |
    Where-Object { $_.Extension -match '\.(py|json|yaml|yml|toml|cfg|ini|txt)$' } |
    ForEach-Object {
        $File = $_
        Select-String -Path $File.FullName -Pattern $SecretPattern -CaseSensitive:$false |
        ForEach-Object { "$($File.FullName):$($_.LineNumber): $($_.Line.Trim())" }
    }
)
$SecretPass = $SecretHits.Count -eq 0
if (-not $SecretPass) { $OverallPass = $false }
Write-CheckResult -Label '비밀값 검사 (API_KEY / password / secret / token)' -Passed $SecretPass -Hits $SecretHits

# ---------------------------------------------------------------------------
# 2. 절대 경로 검사 — C:\, D:\, E:\ 하드코딩 (src/, config/, tests/ 대상)
# ---------------------------------------------------------------------------
$AbsPathPattern = '[CcDdEe]:\\'
$AbsPathDirs = @('src', 'config', 'tests')
$AbsPathHits = @(
    foreach ($Dir in $AbsPathDirs) {
        $DirPath = Join-Path $ProjectRoot $Dir
        if (Test-Path $DirPath) {
            Get-ChildItem -Path $DirPath -Recurse -File |
            Where-Object { $_.Extension -match '\.(py|json|yaml|yml|toml|bat|ps1|txt)$' } |
            ForEach-Object {
                $File = $_
                Select-String -Path $File.FullName -Pattern $AbsPathPattern |
                ForEach-Object { "$($File.FullName):$($_.LineNumber): $($_.Line.Trim())" }
            }
        }
    }
)
$AbsPathPass = $AbsPathHits.Count -eq 0
if (-not $AbsPathPass) { $OverallPass = $false }
Write-CheckResult -Label '절대 경로 검사 (C:\\ / D:\\ / E:\\)' -Passed $AbsPathPass -Hits $AbsPathHits

# ---------------------------------------------------------------------------
# 3. 하드코딩 검사 — 실행 가능한 Python 문자열만 AST로 검사
# ---------------------------------------------------------------------------
$PythonLauncher = (Get-Command py.exe -ErrorAction Stop).Source
$GuardScript = Join-Path $PSScriptRoot 'check_song_hardcoding.py'
$GuardRoot = Join-Path $ProjectRoot 'src'
$GuardStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$GuardStartInfo.FileName = $PythonLauncher
$GuardStartInfo.Arguments = '-3.12 "{0}" --root "{1}"' -f $GuardScript, $GuardRoot
$GuardStartInfo.UseShellExecute = $false
$GuardStartInfo.RedirectStandardOutput = $true
$GuardStartInfo.RedirectStandardError = $true
$GuardStartInfo.CreateNoWindow = $true
$GuardProcess = [System.Diagnostics.Process]::Start($GuardStartInfo)
$GuardStdout = $GuardProcess.StandardOutput.ReadToEnd()
$GuardStderr = $GuardProcess.StandardError.ReadToEnd()
$GuardProcess.WaitForExit()
$HardcodeOutput = @(($GuardStdout + $GuardStderr).Trim() -split "\r?\n" | Where-Object { $_ })
$HardcodePass = $GuardProcess.ExitCode -eq 0
$HardcodeHits = if ($HardcodePass) { @() } else { @($HardcodeOutput | ForEach-Object { $_.ToString() }) }
if (-not $HardcodePass) { $OverallPass = $false }
Write-CheckResult -Label '하드코딩 곡명 검사 (실행 Python AST)' -Passed $HardcodePass -Hits $HardcodeHits

# ---------------------------------------------------------------------------
# 최종 결과
# ---------------------------------------------------------------------------
Write-Host ''
if ($OverallPass) {
    Write-Host '[OK] 모든 검사가 통과했습니다.'
    exit 0
} else {
    Write-Host '[ERROR] 하나 이상의 검사가 실패했습니다. 위 항목을 수정하세요.'
    exit 1
}
