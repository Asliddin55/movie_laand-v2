```bat
@echo off
chcp 65001 >nul
setlocal
title Movie Land BOT - Ishga tushirish

echo ======================================================
echo Movie Land BOT - Eski jarayonlar tekshirilmoqda...
echo ======================================================
echo.

:: 1. bot.pid fayli orqali eski jarayonni to'xtatish
if exist "bot.pid" (
    for /f "usebackq delims=" %%i in ("bot.pid") do (
        taskkill /F /PID %%i >nul 2>&1
    )
    del /F /Q "bot.pid" >nul 2>&1
)

:: 2. main.py bilan ishlayotgan Python jarayonlarini topish
powershell -NoProfile -ExecutionPolicy Bypass -Command "$self = $PID; Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'main\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo.
echo Movie Land BOT ishga tushirilmoqda...
echo ======================================================
echo.

python main.py

echo.
echo ======================================================
echo Bot jarayoni yakunlandi.

if exist "bot.pid" del /F /Q "bot.pid" >nul 2>&1

pause
endlocal
```