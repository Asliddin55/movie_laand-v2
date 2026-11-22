#!/bin/bash
# ==============================================================================
# Movie Land Ultra Bot - MyXvest / CloudLinux / Linux VPS Avto-O'rnatish va Start
# ==============================================================================
set -e
cd "$(dirname "$0")"

echo "=========================================================="
echo "🎬 MOVIE LAND ULTRA BOT — MYXVEST SERVER SOZLANMOQDA..."
echo "=========================================================="

PY_BIN=""

# 1. Tayyor lokal virtual muhit bormi tekshiramiz
if [ -x ".py311/bin/python" ]; then
    PY_BIN="$(pwd)/.py311/bin/python"
elif [ -x "venv/bin/python" ]; then
    PY_BIN="$(pwd)/venv/bin/python"
fi

# 2. Agar virtual muhit hali yaratilmagan bo'lsa, CloudLinux (/opt/alt/python311) ni tekshiramiz
if [ -z "$PY_BIN" ]; then
    SYS_PY=""
    for candidate in /opt/alt/python312/bin/python3 /opt/alt/python311/bin/python3 /opt/alt/python310/bin/python3 /usr/local/bin/python3.12 /usr/local/bin/python3.11 /usr/local/bin/python3.10 /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3.10; do
        if [ -x "$candidate" ]; then
            SYS_PY="$candidate"
            break
        fi
    done

    if [ -n "$SYS_PY" ]; then
        echo "✅ Serverda yangi Python topildi: $SYS_PY"
        "$SYS_PY" -m venv venv 2>/dev/null || "$SYS_PY" -m virtualenv venv 2>/dev/null || true
        if [ -x "venv/bin/python" ]; then
            PY_BIN="$(pwd)/venv/bin/python"
        fi
    fi
fi

# 3. Agar CloudLinux venv ishlamasa yoki faqat Python 3.6.8 bo'lsa, Micromamba orqali Python 3.11 o'rnatamiz
if [ -z "$PY_BIN" ]; then
    echo "📦 Python 3.11 lokal muhiti (.py311) yuklab olinmoqda..."
    if [ ! -x "./micromamba" ]; then
        curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
        mv bin/micromamba ./micromamba
        rmdir bin 2>/dev/null || true
        chmod +x ./micromamba
    fi
    ./micromamba create -y -p ./.py311 python=3.11 pip -c conda-forge
    PY_BIN="$(pwd)/.py311/bin/python"
fi

echo "🐍 Ishlatilayotgan Python: $($PY_BIN -V)"

# 4. Kutubxonalarni o'rnatish
echo "📥 Kutubxonalar o'rnatilmoqda..."
"$PY_BIN" -m pip install --upgrade pip -q
"$PY_BIN" -m pip install -r requirements.txt -q

# 5. Eski bot jarayonini to'xtatish
if [ -f "bot.pid" ]; then
    OLD_PID=$(cat bot.pid 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️ Eski bot jarayoni (PID: $OLD_PID) to'xtatilmoqda..."
        kill -15 "$OLD_PID" 2>/dev/null || kill -9 "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f bot.pid
fi
pkill -f "main.py" 2>/dev/null || true
sleep 1

# 6. Botni orqa fonda (24/7) ishga tushirish
nohup "$PY_BIN" main.py > bot.log 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > bot.pid
sleep 3

echo "=========================================================="
echo "🚀 Movie Land Ultra Bot 24/7 rejimda ishga tushdi!"
echo "📌 Jarayon (PID): $NEW_PID"
echo "📜 Oxirgi loglar:"
tail -n 10 bot.log 2>/dev/null || true
echo "=========================================================="
