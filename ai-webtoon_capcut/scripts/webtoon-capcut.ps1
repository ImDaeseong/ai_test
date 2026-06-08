#Requires -Version 5.1
<#
.SYNOPSIS
    webtoon_capcut CLI 래퍼 스크립트

.DESCRIPTION
    python -m webtoon_capcut 를 프로젝트 루트에서 실행합니다.
    .venv 가 있으면 자동 활성화하고, 모든 인자를 그대로 전달합니다.

.EXAMPLE
    .\scripts\webtoon-capcut.ps1 discover --output-root "..\ai-webtoon\output"
    .\scripts\webtoon-capcut.ps1 build --song-dir "..\ai-webtoon\output\UPGRADE"
    .\scripts\webtoon-capcut.ps1 build-all --output-root "..\ai-webtoon\output" --ready-only
#>

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PassThruArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# 프로젝트 루트 = 이 스크립트의 상위 디렉토리
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# 프로젝트 루트로 이동
Push-Location $ProjectRoot

try {
    # venv 자동 활성화
    $VenvActivate = Join-Path $ProjectRoot '.venv\Scripts\Activate.ps1'
    if (Test-Path $VenvActivate) {
        . $VenvActivate
    }

    # Python 3.12+ 탐색 (py launcher 우선, 그 다음 PATH의 python)
    $PyExe = $null
    foreach ($candidate in @('py -3.12', 'py -3.11', 'python3', 'python')) {
        $parts = $candidate -split ' '
        $cmd = Get-Command $parts[0] -ErrorAction SilentlyContinue
        if ($cmd) {
            if ($parts.Count -gt 1) {
                $ver = & $parts[0] $parts[1] --version 2>&1
            } else {
                $ver = & $parts[0] --version 2>&1
            }
            if ($ver -match 'Python 3\.(1[1-9]|[2-9]\d)') {
                $PyExe = $parts
                break
            }
        }
    }
    if (-not $PyExe) {
        Write-Error '[ERROR] Python 3.11 이상을 찾을 수 없습니다.'
        Write-Host '  py -3.12 -m venv .venv  으로 가상환경을 만드세요.'
        exit 1
    }

    # 인자 없이 호출하면 도움말 표시
    if (-not $PassThruArgs -or $PassThruArgs.Count -eq 0) {
        & $PyExe[0] ($PyExe | Select-Object -Skip 1) -m webtoon_capcut --help
        exit $LASTEXITCODE
    }

    # 모든 인자를 그대로 전달
    & $PyExe[0] ($PyExe | Select-Object -Skip 1) -m webtoon_capcut @PassThruArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
