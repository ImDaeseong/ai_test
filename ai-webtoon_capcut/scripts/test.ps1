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

    # webtoon_capcut 패키지가 editable install 안 된 인터프리터를 선택했을 수 있음
    # (venv 미존재 + PATH상 다른 python이 먼저 잡히는 경우) -- 조용히 ModuleNotFoundError로
    # 실패하는 대신 여기서 감지하고 자동으로 editable install을 시도한다.
    # 네이티브 명령의 stderr을 터미네이팅 에러로 바꾸는 Stop 정책을 이 검사 동안만 완화한다.
    $PrevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $PyExe[0] ($PyExe | Select-Object -Skip 1) -c "import webtoon_capcut" *> $null
    $ImportExitCode = $LASTEXITCODE
    $ErrorActionPreference = $PrevEAP
    if ($ImportExitCode -ne 0) {
        Write-Host "[SETUP] webtoon_capcut 미설치 감지 -- pip install -e . 실행 중..."
        & $PyExe[0] ($PyExe | Select-Object -Skip 1) -m pip install -e $ProjectRoot --quiet
        if ($LASTEXITCODE -ne 0) {
            Write-Error '[ERROR] webtoon_capcut editable install 실패. 수동으로 `pip install -e .` 실행 후 재시도하세요.'
            exit 1
        }
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
