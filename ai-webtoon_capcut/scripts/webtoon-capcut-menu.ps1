#Requires -Version 5.1
<#
.SYNOPSIS
    webtoon_capcut 대화형 메뉴

.DESCRIPTION
    텍스트 메뉴를 표시하고 사용자 선택에 따라 webtoon-capcut.ps1 을 호출합니다.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$ScriptDir  = $PSScriptRoot
$Runner     = Join-Path $ScriptDir 'webtoon-capcut.ps1'
$ProjectRoot = Split-Path -Parent $ScriptDir

function Invoke-Runner {
    param([string[]]$RunnerArgs)
    & $Runner @RunnerArgs
}

function Show-Menu {
    Write-Host ''
    Write-Host '==============================='
    Write-Host '   webtoon-capcut  메뉴'
    Write-Host '==============================='
    Write-Host '  1) Discover songs'
    Write-Host '  2) Inspect song'
    Write-Host '  3) Build song'
    Write-Host '  4) Build all (ready songs)'
    Write-Host '  5) Exit'
    Write-Host '==============================='
}

while ($true) {
    Show-Menu
    $Choice = Read-Host '번호를 입력하세요'

    switch ($Choice.Trim()) {
        '1' {
            $OutputRoot = Read-Host 'output-root 경로 (기본값: ..\ai-webtoon\output)'
            if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
                $OutputRoot = Join-Path $ProjectRoot '..\ai-webtoon\output'
            }
            Invoke-Runner @('discover', '--output-root', $OutputRoot)
        }
        '2' {
            $SongDir = Read-Host 'song-dir 경로를 입력하세요'
            if ([string]::IsNullOrWhiteSpace($SongDir)) {
                Write-Host '[SKIP] song-dir 이 비어 있어 건너뜁니다.'
            } else {
                Invoke-Runner @('inspect', '--song-dir', $SongDir)
            }
        }
        '3' {
            $SongDir = Read-Host 'song-dir 경로를 입력하세요'
            if ([string]::IsNullOrWhiteSpace($SongDir)) {
                Write-Host '[SKIP] song-dir 이 비어 있어 건너뜁니다.'
            } else {
                Invoke-Runner @('build', '--song-dir', $SongDir)
            }
        }
        '4' {
            $OutputRoot = Read-Host 'output-root 경로 (기본값: ..\ai-webtoon\output)'
            if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
                $OutputRoot = Join-Path $ProjectRoot '..\ai-webtoon\output'
            }
            Invoke-Runner @('build-all', '--output-root', $OutputRoot, '--ready-only')
        }
        '5' {
            Write-Host '종료합니다.'
            exit 0
        }
        default {
            Write-Host "[WARN] '$Choice' 는 유효하지 않은 선택입니다. 1~5 중에서 선택하세요."
        }
    }

    Write-Host ''
    $Continue = Read-Host '계속하려면 Enter, 종료하려면 q 를 누르세요'
    if ($Continue.Trim() -eq 'q') {
        Write-Host '종료합니다.'
        exit 0
    }
}
