#Requires -Version 5.1
<#
.SYNOPSIS
    프로젝트 단위·통합 테스트 실행

.DESCRIPTION
    python -m pytest tests/ -v 를 프로젝트 루트에서 실행합니다.
    테스트 실패 시 exit 1 로 종료합니다.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot

try {
    # venv 자동 활성화
    $VenvActivate = Join-Path $ProjectRoot '.venv\Scripts\Activate.ps1'
    if (Test-Path $VenvActivate) {
        . $VenvActivate
    }

    # Python 3.11+ 탐색
    $PyExe = $null
    foreach ($c in @('py -3.12', 'py -3.11', 'python3', 'python')) {
        $p = $c -split ' '
        $cmd = Get-Command $p[0] -ErrorAction SilentlyContinue
        if ($cmd) {
            $ver = & $p[0] ($p | Select-Object -Skip 1) --version 2>&1
            if ($ver -match 'Python 3\.(1[1-9]|[2-9]\d)') { $PyExe = $p; break }
        }
    }
    if (-not $PyExe) {
        Write-Error '[ERROR] Python 3.11 이상을 찾을 수 없습니다.'
        exit 1
    }

    Write-Host '[TEST] pytest 실행 중...'
    Write-Host "  루트: $ProjectRoot"
    Write-Host ''

    & $PyExe[0] ($PyExe | Select-Object -Skip 1) -m pytest tests/ -v
    $ExitCode = $LASTEXITCODE

    Write-Host ''
    if ($ExitCode -eq 0) {
        Write-Host '[PASS] 모든 테스트가 통과했습니다.'
    } else {
        Write-Host "[FAIL] 테스트 실패 (exit $ExitCode)"
    }

    exit $ExitCode
}
finally {
    Pop-Location
}
