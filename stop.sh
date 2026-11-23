#!/bin/bash
# ==============================================================================
# Movie Land Ultra Bot - Linux VPS / MyXvest Xavfsiz To'xtatish skripti
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

if [ -f "cloudflared.pid" ]; then
    CF_PID=$(cat cloudflared.pid 2>/dev/null || true)
    if [ -n "$CF_PID" ] && kill -0 "$CF_PID" 2>/dev/null; then
        echo "🛑 Cloudflare HTTPS Tunnel (PID: $CF_PID) to'xtatilmoqda..."
        kill -15 "$CF_PID" 2>/dev/null || kill -9 "$CF_PID" 2>/dev/null || true
        echo "✅ Tunnel to'xtatildi."
    fi
    rm -f cloudflared.pid
fi
pkill -f "\.cloudflared tunnel" 2>/dev/null || true
rm -f .webapp_port
