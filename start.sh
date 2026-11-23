#!/bin/bash
# ==============================================================================
# Movie Land Ultra Bot - MyXvest / CloudLinux / Linux VPS Avto-O'rnatish, SSL & Start
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

# 5. Eski bot va tunnel jarayonlarini xavfsiz to'xtatish
if [ -f "bot.pid" ]; then
    OLD_PID=$(cat bot.pid 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️ Eski bot jarayoni (PID: $OLD_PID) to'xtatilmoqda..."
        kill -15 "$OLD_PID" 2>/dev/null || kill -9 "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f bot.pid
fi
if [ -f "cloudflared.pid" ]; then
    CF_OLD=$(cat cloudflared.pid 2>/dev/null || true)
    if [ -n "$CF_OLD" ] && kill -0 "$CF_OLD" 2>/dev/null; then
        kill -15 "$CF_OLD" 2>/dev/null || kill -9 "$CF_OLD" 2>/dev/null || true
    fi
    rm -f cloudflared.pid
fi
pkill -f "main.py" 2>/dev/null || true
pkill -f "\.cloudflared tunnel" 2>/dev/null || true
rm -f .webapp_port
sleep 1

# 6. Botni (ichki WebApp HTTP serveri — 100% bo'sh kernel portda!) orqa fonda ishga tushirish
export WEBAPP_PORT=0
nohup "$PY_BIN" main.py > bot.log 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > bot.pid

# Lokal WebApp server tayyor bo'lishini va AYNAN Movie Land javob berishini tekshirish (maks 25 soniya)
LOCAL_PORT=""
for i in $(seq 1 25); do
    if [ -f ".webapp_port" ]; then
        CAND_PORT=$(cat .webapp_port 2>/dev/null | tr -dc '0-9' || true)
        if [ -n "$CAND_PORT" ] && curl -sf --max-time 2 "http://127.0.0.1:${CAND_PORT}/health" 2>/dev/null | grep -q "Movie Land"; then
            LOCAL_PORT="$CAND_PORT"
            break
        fi
    fi
    sleep 1
done

# 7. Mobil Telegram WebApp uchun ISHONCHLI HTTPS SSL tekshiruvi va Avto-Tunnel!
SITE_URL="https://6b02fedeb2d06.myxvest1.ru/"
ACTIVE_WEBAPP_URL="$SITE_URL"

if curl -sfI --max-time 6 "$SITE_URL" >/dev/null 2>&1; then
    echo "🔒 MyXvest domeni ishonchli SSL sertifikatga ega: $SITE_URL"
elif [ -z "$LOCAL_PORT" ]; then
    echo "❌ Lokal Movie Land WebApp serveri 25 soniyada ko'tarilmadi! bot.log ni tekshiring:"
    tail -n 20 bot.log 2>/dev/null || true
else
    echo "✅ Movie Land lokal WebApp serveri tayyor: http://127.0.0.1:${LOCAL_PORT}"
    echo "⚠️ MyXvest SSL hali self-signed — telefonda oq ekran bo'lmasligi uchun Cloudflare HTTPS Tunnel ishga tushirilmoqda..."
    if [ ! -x "./.cloudflared" ]; then
        echo "📦 cloudflared yuklab olinmoqda (bir martalik)..."
        curl -sSL -o ./.cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" || true
        chmod +x ./.cloudflared 2>/dev/null || true
    fi
    if [ -x "./.cloudflared" ]; then
        rm -f cloudflared.log
        nohup ./.cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${LOCAL_PORT}" > cloudflared.log 2>&1 &
        CF_PID=$!
        echo "$CF_PID" > cloudflared.pid
        TUNNEL_URL=""
        for i in $(seq 1 18); do
            TUNNEL_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' cloudflared.log 2>/dev/null | head -n 1 || true)
            if [ -n "$TUNNEL_URL" ]; then
                break
            fi
            sleep 1
        done
        if [ -n "$TUNNEL_URL" ]; then
            ACTIVE_WEBAPP_URL="${TUNNEL_URL}/"
            echo "✅ Ishonchli Yashil-Qulfli HTTPS WebApp tayyor: $ACTIVE_WEBAPP_URL"
        else
            echo "⚠️ Cloudflare tunnel URL olinmadi (cloudflared.log ni tekshiring). Standart manzil qoldirildi."
        fi
    fi
fi

# 8. Aniqlangan ishonchli HTTPS URL ni SQLite baza + Telegram Menu tugmasiga sinxronlash
"$PY_BIN" - "$ACTIVE_WEBAPP_URL" <<'PYEOF'
import sys, sqlite3, json, urllib.request, config
url = sys.argv[1].strip()
if url:
    try:
        conn = sqlite3.connect("database.db", timeout=15)
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('webapp_url', ?)", (url,))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB webapp_url sync warning:", e)
    try:
        payload = json.dumps({
            "menu_button": {
                "type": "web_app",
                "text": "🎬 WebApp",
                "web_app": {"url": url}
            }
        }).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{config.BOT_TOKEN}/setChatMenuButton",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        print("🔗 Telegram Menu WebApp sinxronlandi:", url)
    except Exception as e:
        print("Telegram menu sync warning:", e)
PYEOF

echo "=========================================================="
echo "🚀 Movie Land Ultra Bot 24/7 rejimda ishga tushdi!"
echo "📌 Bot PID: $NEW_PID | Lokal WebApp Port: $LOCAL_PORT"
echo "🌐 Faol HTTPS WebApp: $ACTIVE_WEBAPP_URL"
echo "📜 Oxirgi loglar:"
tail -n 10 bot.log 2>/dev/null || true
echo "=========================================================="
