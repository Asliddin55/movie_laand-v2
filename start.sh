#!/bin/bash
# ==============================================================================
# Movie Land Ultra Bot - Linux VPS Production Ishga tushirish skripti
# ==============================================================================
set -e
cd "$(dirname "$0")"

# Virtual muhit mavjud bo'lsa faollashtiramiz
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Eski jarayon va port qulfini tozalash
if [ -f "bot.pid" ]; then
    OLD_PID=$(cat bot.pid 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️ Eski bot jarayoni (PID: $OLD_PID) aniqlandi, to'xtatilmoqda..."
        kill -15 "$OLD_PID" 2>/dev/null || kill -9 "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f bot.pid
fi

# Botni fonda nohup orqali ishga tushiramiz
nohup python3 main.py > bot.log 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > bot.pid

echo "=========================================================="
echo "🚀 Movie Land Ultra Bot muvaffaqiyatli ishga tushdi!"
echo "📌 Yangi Jarayon (PID): $NEW_PID"
echo "📜 Jonli loglarni ko'rish: tail -f bot.log"
echo "🛑 To'xtatish uchun: ./stop.sh"
echo "=========================================================="
