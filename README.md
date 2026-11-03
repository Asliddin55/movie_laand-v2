# 🎬 Movie Land Telegram Bot (v2.0 Ultimate Edition)

Telegram orqali kino va seriallarni qidirish, avtomatik TheMovieDB posterlari, ko'p qismli kinolarni jamlash, mavzuli guruh (forum) ekotizimi, VIP iqtisodiyoti va kuchli admin paneli bilan jihozlangan professional Telegram bot.

---

## 🚀 Asosiy Imkoniyatlar

1. **TMDB Rasmli Avto-Qidiruv**:
   - Bot nomi `@movieeland_bot` yozilganda yoki «🔍 Inline rejimda qidirish» tugmasi bosilganda TheMovieDB (TMDB) rasmiy HD posterlari va ma'lumotlari bilan avtomatik ochiladi.
   - Tanlangan kinoning videosi bir zumda yuboriladi.

2. **Ko'p qismli kinolar va Seriallar Ekotizimi**:
   - Bir nechta qismli kinolar (masalan: Mumiyo 1, 2, 3) bitta kod ostida `[▶️ Kino ko'rish]` yoki `[1] [2] [3]` inline tugmalari bilan jamlanadi.
   - Seriallar (masalan: Afsungar Merlin 1..65-qism) umumiy serial kartasi sifatida yig'iladi.

3. **Mavzuli Guruh (Forum) Ekotizimi**:
   - ⚡ **Активный Faolik** (`thread_id: 196`) — yangi a'zolar, VIP xaridlar va to'lov cheklari.
   - 💸 **Premium Otzivlar** (`thread_id: 190`) — fikr va sharhlar.
   - ⭐ **Buyurtmalar** (`thread_id: 193`) — kino buyurtmalari.
   - 💎 **Qoidalar** (`thread_id: 195`) & 👑 **Muhokama Chati** (`thread_id: 194`).
   - Telegram Bot API `setChatMemberTag` orqali VIP a'zolarga kanalda maxsus nishonlar (`PREMIUM`, `VIP KING`, `SPONSOR`).

4. **Iqtisodiyot va VIP Tizimi**:
   - Kunlik bonuslar (1000 so'm), do'stlarni taklif qilish (referal — 1500 so'm).
   - VIP obunalar do'koni (7, 30, 90 kun).
   - Karta orqali to'lov chekini yuborish va admin tomonidan tasdiqlash/rad etish.

5. **Yuqori Unumdorlik va Himoya**:
   - SQLite WAL rejimi, 64MB RAM kesh, mmap 256MB va 23 ta tezyurar indeks.
   - Kontentni forward qilish va saqlashni 100% cheklash (`protect_content`).
   - 100 bosqichli to'liq avtomatlashtirilgan audit tizimi (`test_100_audit.py`).

---

## ⚙️ O'rnatish va Sozlash

### 1. Talablar
- Python 3.10+
- SQLite3

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. Konfiguratsiya
`.env.example` faylidan nusxa olib `.env` yarating va ma'lumotlarni kiriting:
```env
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMINS=YOUR_TELEGRAM_ID
ADMIN_SECRET_CODE=your_super_admin_password
```

---

## ▶️ Ishga tushirish

### Windows:
`start.bat` fayliga bosing yoki terminalda:
```bash
python main.py
```

### Linux / VPS Server:
```bash
chmod +x start.sh stop.sh
./start.sh
```

**Systemd servisi orqali (24/7 avto-restart):**
```bash
sudo cp movieland.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable movieland
sudo systemctl start movieland
```

---

## 📄 Litsenziya
Ushbu loyiha [Apache 2.0 License](LICENSE) asosida litsenziyalangan.
