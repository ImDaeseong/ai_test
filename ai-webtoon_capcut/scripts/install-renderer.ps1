#Requires -Version 5.1
<#
.SYNOPSIS
    Remotion 렌더러 의존성 설치

.DESCRIPTION
    remotion/ 디렉터리에서 npm install을 실행합니다.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RemotionDir = Join-Path $ProjectRoot 'remotion'

if (-not (Test-Path $RemotionDir)) {
    Write-Error "[ERROR] remotion 디렉터리를 찾을 수 없습니다: $RemotionDir"
    exit 1
}

$Npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $Npm) {
    Write-Error '[ERROR] npm을 찾을 수 없습니다. Node.js를 설치하세요.'
    exit 1
}

Push-Location $RemotionDir
try {
    Write-Host '[SETUP] remotion 의존성 설치 중 (npm install)...'
    npm install
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
