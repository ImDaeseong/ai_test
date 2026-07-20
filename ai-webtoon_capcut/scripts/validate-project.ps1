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
# 3. 하드코딩 검사 — 특정 곡명 (fixture 폴더 제외)
# ---------------------------------------------------------------------------
$HardcodedSongs = @('UPGRADE', '디저트', '떠나고')
$HardcodePattern = ($HardcodedSongs | ForEach-Object { [regex]::Escape($_) }) -join '|'

$HardcodeHits = @(
    Get-ChildItem -Path $ProjectRoot -Recurse -File |
    Where-Object {
        # fixture 폴더, .git, __pycache__, .pytest_cache, output, workspace 제외
        $RelPath = $_.FullName.Substring($ProjectRoot.Length)
        $RelPath -notmatch '(\\fixtures?\\|\\\.git\\|\\__pycache__\\|\\\.pytest_cache\\|\\output\\|\\workspace\\)'
    } |
    Where-Object { $_.Extension -match '\.(py|json|yaml|yml|toml|bat|ps1|txt|md)$' } |
    ForEach-Object {
        $File = $_
        Select-String -Path $File.FullName -Pattern $HardcodePattern |
        ForEach-Object { "$($File.FullName):$($_.LineNumber): $($_.Line.Trim())" }
    }
)
$HardcodePass = $HardcodeHits.Count -eq 0
if (-not $HardcodePass) { $OverallPass = $false }
Write-CheckResult -Label "하드코딩 곡명 검사 ($($HardcodedSongs -join ' / '))" -Passed $HardcodePass -Hits $HardcodeHits

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
