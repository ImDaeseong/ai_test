#Requires -Version 5.1
<#
.SYNOPSIS
    자막 정렬(WhisperX/Demucs) 의존성 설치

.DESCRIPTION
    requirements-alignment.txt를 pip install로 설치합니다. CPU 환경에서는
    다운로드·설치에 시간이 걸릴 수 있습니다.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RequirementsFile = Join-Path $ProjectRoot 'requirements-alignment.txt'

if (-not (Test-Path $RequirementsFile)) {
    Write-Error "[ERROR] requirements-alignment.txt를 찾을 수 없습니다: $RequirementsFile"
    exit 1
}

# venv Python 우선 탐색
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$PyExe = $null

if (Test-Path $VenvPython) {
    $PyExe = @($VenvPython)
} else {
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
}

if (-not $PyExe) {
    Write-Error '[ERROR] Python 3.11 이상을 찾을 수 없습니다.'
    exit 1
}

Write-Host '[SETUP] 자막 정렬 의존성 설치 중 (WhisperX/Demucs, 시간이 걸릴 수 있습니다)...'
& $PyExe[0] ($PyExe | Select-Object -Skip 1) -m pip install -r $RequirementsFile
exit $LASTEXITCODE
