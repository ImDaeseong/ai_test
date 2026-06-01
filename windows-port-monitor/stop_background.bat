@echo off
setlocal

set "APP_DIR=%~dp0"
set "PID_FILE=%APP_DIR%data\port_monitor.pid"
set "STOP_FILE=%APP_DIR%data\port_monitor.stop"
set "START_FILE=%APP_DIR%data\port_monitor.started_at"
set "HISTORY_FILE=%APP_DIR%data\port_records.jsonl"
set "REPORT_FILE=%APP_DIR%data\port_process_history.txt"

if not exist "%APP_DIR%data" mkdir "%APP_DIR%data"

echo stop>"%STOP_FILE%"
echo Stop signal written: %STOP_FILE%

if not exist "%PID_FILE%" (
    echo PID file not found. If the monitor is running, it should stop after the next polling cycle.
    call :OPEN_HISTORY_REPORT 0
    exit /b %errorlevel%
)

for /f "usebackq delims=" %%P in ("%PID_FILE%") do set "PID=%%P"
if not defined PID (
    echo PID file is empty.
    call :OPEN_HISTORY_REPORT 1
    exit /b %errorlevel%
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pidValue = [int]'%PID%';" ^
  "$deadline = (Get-Date).AddSeconds(20);" ^
  "while ((Get-Date) -lt $deadline) {" ^
  "  $p = Get-Process -Id $pidValue -ErrorAction SilentlyContinue;" ^
  "  if (-not $p) { Remove-Item -LiteralPath '%PID_FILE%' -Force -ErrorAction SilentlyContinue; Write-Host 'Windows Port Monitor stopped gracefully.'; exit 0 }" ^
  "  Start-Sleep -Milliseconds 500" ^
  "}" ^
  "Write-Warning 'Process did not exit within 20 seconds. Leaving PID file in place for inspection.'; exit 1"

set "STOP_RESULT=%errorlevel%"
call :OPEN_HISTORY_REPORT %STOP_RESULT%
exit /b %errorlevel%

:OPEN_HISTORY_REPORT
set "REPORT_EXIT_CODE=%~1"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$historyPath = '%HISTORY_FILE%';" ^
  "$startPath = '%START_FILE%';" ^
  "$reportPath = '%REPORT_FILE%';" ^
  "$stopAt = (Get-Date).ToUniversalTime();" ^
  "$startAt = $null;" ^
  "if (Test-Path -LiteralPath $startPath) { try { $startAt = [datetimeoffset]::Parse([string](Get-Content -LiteralPath $startPath -TotalCount 1)).UtcDateTime } catch { $startAt = $null } }" ^
  "$lines = New-Object System.Collections.Generic.List[string];" ^
  "$lines.Add('Windows Port Monitor - Process / Port History');" ^
  "$lines.Add(('Generated: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')));" ^
  "$lines.Add(('Stop result code: ' + '%REPORT_EXIT_CODE%'));" ^
  "$lines.Add(('Session start: ' + $(if ($startAt) { $startAt.ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss') } else { 'unknown' })));" ^
  "$lines.Add(('Session stop: ' + $stopAt.ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss')));" ^
  "$lines.Add('');" ^
  "$lines.Add('Process and port are shown first by default. Windows system processes are excluded.');" ^
  "$lines.Add('Only records collected between start_background.bat and stop_background.bat are shown. Duplicate records are removed.');" ^
  "$lines.Add('');" ^
  "if (-not (Test-Path -LiteralPath $historyPath)) {" ^
  "  $lines.Add('No history file found: ' + $historyPath)" ^
  "} else {" ^
  "  $records = Get-Content -LiteralPath $historyPath -ErrorAction SilentlyContinue | ForEach-Object { try { $_ | ConvertFrom-Json } catch { $null } } | Where-Object { $include = $false; if ($_ -and $_.type -eq 'port_record') { try { $collectedAt = [datetimeoffset]::Parse([string]$_.collection_time).UtcDateTime; $include = (((-not $startAt) -or $collectedAt -ge $startAt) -and $collectedAt -le $stopAt) } catch { $include = $false } }; $include } | Sort-Object collection_time -Descending;" ^
  "  if (-not $records) {" ^
  "    $lines.Add('No process/port history records were found.')" ^
  "  } else {" ^
  "    $userRecords = $records | Where-Object { $name = [string]$_.process_name; $exe = [string]$_.process_exe; $user = [string]$_.username; ($name -notin @('System', 'System Idle Process', 'Idle', 'Registry', 'Memory Compression')) -and ($name -notlike 'svchost.exe') -and ($exe -notlike 'C:\Windows\*') -and ($user -notlike 'NT AUTHORITY\*') -and ($user -notlike 'Window Manager\*') -and ($user -notlike 'Font Driver Host\*') };" ^
  "    $userRecords = $userRecords | Group-Object { @($_.protocol, $_.local_ip, $_.local_port, $_.remote_ip, $_.remote_port, $_.state, $_.pid, $_.process_name) -join '|' } | ForEach-Object { $_.Group | Sort-Object collection_time -Descending | Select-Object -First 1 } | Sort-Object collection_time -Descending;" ^
  "    if (-not $userRecords) { $lines.Add('No non-system process/port history records were found.'); $lines.Add(''); $userRecords = @() }" ^
  "    $rows = foreach ($r in $userRecords) {" ^
  "      [pscustomobject]@{" ^
  "        Process = if ($r.process_name) { $r.process_name } else { '<unknown>' };" ^
  "        Port = if ($null -ne $r.local_port) { $r.local_port } else { '' };" ^
  "        Protocol = $r.protocol;" ^
  "        PID = if ($null -ne $r.pid) { $r.pid } else { '' };" ^
  "        State = $r.state;" ^
  "        LocalAddress = (($r.local_ip, $r.local_port) -join ':');" ^
  "        RemoteAddress = if ($null -ne $r.remote_ip -and $null -ne $r.remote_port) { (($r.remote_ip, $r.remote_port) -join ':') } else { '' };" ^
  "        User = $r.username;" ^
  "        CollectedAt = $r.collection_time" ^
  "      }" ^
  "    };" ^
  "    $lines.Add(('Latest records: ' + @($rows).Count));" ^
  "    $lines.Add('');" ^
  "    ($rows | Format-Table -AutoSize | Out-String -Width 240).TrimEnd() -split [Environment]::NewLine | ForEach-Object { $lines.Add($_) }" ^
  "  }" ^
  "};" ^
  "Set-Content -LiteralPath $reportPath -Value $lines -Encoding UTF8;" ^
  "Start-Process -FilePath notepad.exe -ArgumentList ('""' + $reportPath + '""')"
exit /b %REPORT_EXIT_CODE%
