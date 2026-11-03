#!/bin/bash
# ==============================================================================
# Movie Land Ultra Bot - Linux VPS Xavfsiz To'xtatish skripti
# ==============================================================================
cd "$(dirname "$0")"

if [ -f "bot.pid" ]; then
    PID=$(cat bot.pid 2>/dev/null || true)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "🛑 Bot (PID: $PID) to'xtatilmoqda..."
        kill -15 "$PID" 2>/dev/null || true
        for i in {1..5}; do
            if kill -0 "$PID" 2>/dev/null; then
                sleep 1
            else
                break
            fi
        done
        kill -9 "$PID" 2>/dev/null || true
        echo "✅ Bot xavfsiz to'xtatildi."
    else
        echo "ℹ️ bot.pid faylida ko'rsatilgan jarayon faol emas."
    fi
    rm -f bot.pid
else
    echo "⚠️ bot.pid fayli topilmadi. Barcha main.py jarayonlari tekshirilmoqda..."
    pkill -f "python.*main.py" 2>/dev/null && echo "✅ Bot jarayoni to'xtatildi." || echo "ℹ️ Faol bot jarayoni topilmadi."
fi
