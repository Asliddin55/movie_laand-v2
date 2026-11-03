@echo off
chcp 65001 >nul
title GitHub-ga yuklash (Movie Land Bot v2.0)
cd /d "%~dp0"

echo ======================================================
echo 🎬 MOVIE LAND BOT -> GITHUB (movie_laand-v2) YUKLASH
echo ======================================================
echo.
echo Git holati tekshirilmoqda...
git status
echo.
echo Kodlar GitHub-ga yuborilmoqda (git push origin main)...
echo.
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================
    echo ✅ MUVAFFAQIYATLI YUKLANDI!
    echo https://github.com/Asliddin55/movie_laand-v2 sahifasini yangilang (F5).
    echo ======================================================
) else (
    echo.
    echo ❌ Xatolik yuz berdi. Iltimos, GitHub tizimiga kirishni tasdiqlang.
)

echo.
pause
