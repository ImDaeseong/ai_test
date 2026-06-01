@echo off
netstat -ano | findstr ":5000" | findstr "LISTENING" > "%temp%\lrctag_pid.txt"
for /f "tokens=5" %%a in (%temp%\lrctag_pid.txt) do taskkill /f /pid %%a >nul 2>&1
del "%temp%\lrctag_pid.txt" >nul 2>&1
echo stopped.
timeout /t 2 /nobreak >nul
