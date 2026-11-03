@echo off
chcp 65001 >nul
title Movie Land BOT - To'xtatish
echo ======================================================
echo 🛑 Movie Land BOT to'xtatilmoqda...
echo ======================================================

:: 1. bot.pid orqali aniq jarayonni to'xtatish
if exist bot.pid (
    for /f %%i in (bot.pid) do (
        echo [INFO] bot.pid dagi jarayon (PID: %%i) to'xtatilmoqda...
        taskkill /F /PID %%i >nul 2>&1
    )
    del /f /q bot.pid >nul 2>&1
)

:: 2. Barcha fonda osilib qolgan main.py jarayonlarini majburiy to'xtatish
powershell -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%main.py%%' and Name like '%%python%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo.
echo ✅ Barcha bot jarayonlari to'liq to'xtatildi!
echo ======================================================
timeout /t 3 >nul
