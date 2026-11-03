import aiosqlite
import json
import csv
import os
import re
from datetime import datetime, timedelta
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Mutlaq yo'l: bot qaysi papkadan ishga tushirilmasin, doim shu yagona bazadan foydalanadi
DB_NAME = os.path.join(BASE_DIR, "database.db")

_SETTINGS_CACHE = {}
_CHANNELS_CACHE = None
_USER_LANG_CACHE = {}

def normalize_channel_target(raw_ch: str) -> str:
    """https://t.me/movieee_land -> @movieee_land yoki -100... holatga keltiradi."""
    s = (raw_ch or "").strip()
    if not s:
        return config.DEFAULT_POST_CHANNEL_ID
    if s.startswith("https://t.me/") or s.startswith("http://t.me/") or s.startswith("t.me/"):
        uname = s.split("t.me/")[-1].strip("/").split("?")[0]
        if uname and not uname.startswith("+"):
            return f"@{uname}"
    return s

async def get_db_conn():
    db = await aiosqlite.connect(DB_NAME, timeout=30.0)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA busy_timeout=30000;")
    await db.execute("PRAGMA cache_size=-64000;")
    await db.execute("PRAGMA temp_store=MEMORY;")
    await db.execute("PRAGMA mmap_size=268435456;")
    return db


def _snapshot_sync(dst_path: str) -> str:
    import sqlite3
    src = sqlite3.connect(DB_NAME, timeout=30)
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return dst_path


async def make_db_snapshot(file_name: str = None) -> str:
    """
    Bot ishlab turgan paytda ham (WAL rejimida) bazaning 100% izchil nusxasini yaratadi.
    Backup yuborishda aynan shu nusxa yuboriladi — yarim yozilgan / buzilgan baza ketmaydi.
    """
    import asyncio
    bk_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(bk_dir, exist_ok=True)
    name = file_name or f"database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    dst = os.path.join(bk_dir, name)
    return await asyncio.to_thread(_snapshot_sync, dst)

async def init_db():
    db = await get_db_conn()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                is_admin INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                permissions TEXT DEFAULT '[]',
                sadmin_auth_until TEXT DEFAULT NULL,
                is_premium INTEGER DEFAULT 0,
                premium_until TEXT DEFAULT NULL,
                vip_tag TEXT DEFAULT 'PREMIUM',
                balance INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                last_daily_date TEXT DEFAULT NULL,
                is_banned INTEGER DEFAULT 0,
                ref_by INTEGER DEFAULT NULL,
                ref_count INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        new_user_cols = [
            ("role", "TEXT DEFAULT 'user'"),
            ("permissions", "TEXT DEFAULT '[]'"),
            ("sadmin_auth_until", "TEXT DEFAULT NULL"),
            ("is_premium", "INTEGER DEFAULT 0"),
            ("premium_until", "TEXT DEFAULT NULL"),
            ("vip_tag", "TEXT DEFAULT 'PREMIUM'"),
            ("balance", "INTEGER DEFAULT 0"),
            ("total_earned", "INTEGER DEFAULT 0"),
            ("daily_streak", "INTEGER DEFAULT 0"),
            ("last_daily_date", "TEXT DEFAULT NULL"),
            ("lang", "TEXT DEFAULT ''")
        ]
        for col_name, col_def in new_user_cols:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                name TEXT,
                genre TEXT DEFAULT '🎬 Boshqa',
                year TEXT DEFAULT '2025',
                country TEXT DEFAULT 'AQSH',
                language TEXT DEFAULT 'O''zbek tilida',
                quality TEXT DEFAULT '1080p Full HD',
                imdb TEXT DEFAULT '8.0',
                file_id TEXT,
                photo_id TEXT DEFAULT NULL,
                caption TEXT DEFAULT '',
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                dislikes INTEGER DEFAULT 0,
                is_serial INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_code TEXT,
                episode_num INTEGER,
                title TEXT,
                file_id TEXT,
                UNIQUE(movie_code, episode_num)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS archive_imported (
                msg_id INTEGER PRIMARY KEY,
                movie_code TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Mavzuli Kanallar va Guruhlar Ekotizimi jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topic_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT UNIQUE,
                title TEXT,
                invite_link TEXT,
                topic_category TEXT DEFAULT '🎬 Kinolar',
                is_vip_only INTEGER DEFAULT 0,
                auto_tag_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                movie_code TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, movie_code)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                user_id INTEGER,
                movie_code TEXT,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, movie_code)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS reactions (
                user_id INTEGER,
                movie_code TEXT,
                reaction TEXT,
                PRIMARY KEY (user_id, movie_code)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                title TEXT,
                invite_link TEXT,
                ch_type TEXT DEFAULT 'public'
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS join_requests (
                user_id INTEGER,
                channel_id TEXT,
                PRIMARY KEY (user_id, channel_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_members (
                user_id INTEGER,
                channel_id TEXT,
                status TEXT DEFAULT 'member',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, channel_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                full_name TEXT,
                username TEXT,
                movie_name TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS archive_catalog (
                msg_id INTEGER PRIMARY KEY,
                file_id TEXT DEFAULT '',
                file_name TEXT DEFAULT '',
                video_height INTEGER DEFAULT 0,
                raw_caption TEXT DEFAULT '',
                parsed_name TEXT DEFAULT '',
                base_title TEXT DEFAULT '',
                year TEXT DEFAULT '2024',
                country TEXT DEFAULT 'AQSH',
                genre TEXT DEFAULT '🔥 Jangari',
                quality TEXT DEFAULT '1080p Full HD',
                is_serial INTEGER DEFAULT 0,
                part_num INTEGER DEFAULT 1,
                is_imported INTEGER DEFAULT 0,
                imported_code TEXT DEFAULT ''
            )
        """)

        default_settings = [
            ("protect_content", "1"),
            ("auto_post_channel", config.DEFAULT_POST_CHANNEL_ID),
            ("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID),
            ("main_topic_group_id", config.MAIN_TOPIC_GROUP_ID),
            ("auto_grab_archive", "1"),
            ("archive_auto_post", "0"),
            ("tmdb_auto_poster", "1"),
            ("bot_active", "1"),
            ("super_admin_password", config.DEFAULT_SUPER_ADMIN_PASSWORD),
            ("free_order_limit", "1"),
            ("premium_order_limit", "5"),
            ("daily_reward_amount", config.DEFAULT_DAILY_REWARD),
            ("ref_reward_amount", config.DEFAULT_REF_REWARD),
            ("vip_7_price", config.DEFAULT_VIP_7_PRICE),
            ("vip_30_price", config.DEFAULT_VIP_30_PRICE),
            ("vip_90_price", config.DEFAULT_VIP_90_PRICE),
            ("payment_card_info", config.DEFAULT_PAYMENT_CARD),
            ("tmdb_api_key", config.TMDB_API_KEY),
            ("tmdb_read_token", config.TMDB_READ_TOKEN),
            ("auto_backup_hours", "168"),
            ("auto_backup_target", config.DEFAULT_ARCHIVE_CHANNEL_ID),
            ("ai_enabled", "1"),
            ("ai_active_provider", "gemini")
        ]
        for k, v in default_settings:
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

        await db.execute(
            "UPDATE settings SET value = '168' WHERE key = 'auto_backup_hours' AND (value IS NULL OR value = '' OR value = '0')"
        )
        await db.execute(
            "UPDATE settings SET value = ? WHERE key = 'auto_backup_target' AND (value IS NULL OR value = '')",
            (config.DEFAULT_ARCHIVE_CHANNEL_ID,)
        )

        await db.execute(
            "UPDATE settings SET value = ? WHERE key = 'tmdb_api_key' AND (value IS NULL OR value = '')",
            (config.TMDB_API_KEY,)
        )
        await db.execute(
            "UPDATE settings SET value = ? WHERE key = 'tmdb_read_token' AND (value IS NULL OR value = '')",
            (config.TMDB_READ_TOKEN,)
        )

        # Yagona rasmiy Mavzuli Guruhni (-1002748514315) avtomatik ulab qo'yish
        await db.execute("DELETE FROM topic_channels WHERE chat_id != ?", (config.MAIN_TOPIC_GROUP_ID,))
        await db.execute("""
            INSERT OR REPLACE INTO topic_channels
            (chat_id, title, invite_link, topic_category, is_vip_only, auto_tag_enabled)
            VALUES (?, ?, ?, ?, 0, 1)
        """, (
            config.MAIN_TOPIC_GROUP_ID,
            "Movie Land Group (Mavzuli Guruh)",
            config.MAIN_TOPIC_GROUP_LINK,
            "🌐 Rasmiy Mavzuli Guruh"
        ))

        # Arxivdan tashqari 2 ta asosiy kanal/guruhni majburiy obunaga avto-ulash:
        # 1) Post yuboradigan asosiy kanal (@movieee_land / -1003536154725)
        # 2) Mavzuli Guruh (-1002748514315)
        # Arxiv kanali (-1003124847141) majburiy obunada bo'lmasligi shart!
        await db.execute("DELETE FROM channels WHERE channel_id = ?", (config.DEFAULT_ARCHIVE_CHANNEL_ID,))
        await db.execute("""
            INSERT OR IGNORE INTO channels (channel_id, title, invite_link, ch_type)
            VALUES (?, ?, ?, 'public')
        """, (
            config.DEFAULT_POST_CHANNEL_CHAT_ID,
            "🎬 Movie Land | Rasmiy Kanal",
            config.DEFAULT_POST_CHANNEL_LINK
        ))
        await db.execute("""
            INSERT OR IGNORE INTO channels (channel_id, title, invite_link, ch_type)
            VALUES (?, ?, ?, 'public')
        """, (
            config.MAIN_TOPIC_GROUP_ID,
            "💬 Movie Land | Mavzuli Guruh",
            config.MAIN_TOPIC_GROUP_LINK
        ))

        async with db.execute("SELECT value FROM settings WHERE key = 'auto_post_channel'") as cur:
            row = await cur.fetchone()
            if row:
                norm_ch = normalize_channel_target(row[0])
                await db.execute("UPDATE settings SET value = ? WHERE key = 'auto_post_channel'", (norm_ch,))

        await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_name ON movies(name);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_genre ON movies(genre);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_views ON movies(views DESC);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_serial ON movies(is_serial);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_created ON movies(created_at DESC);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_episodes_lookup ON episodes(movie_code, episode_num);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_date ON orders(user_id, created_at);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_arch_grouping ON archive_catalog(is_serial, is_imported, base_title);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_premium_chk ON users(is_premium, premium_until);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_ref_lookup ON users(ref_by);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_history_user_time ON history(user_id, viewed_at DESC);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_favs_user_lookup ON favorites(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_reactions_code ON reactions(movie_code);")
        await db.commit()
    finally:
        await db.close()


# ===================== SOZLAMALAR =====================
async def get_setting(key: str, default: str = "") -> str:
    if key in _SETTINGS_CACHE:
        return _SETTINGS_CACHE[key]
    db = await get_db_conn()
    try:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            val = row[0] if row else default
            _SETTINGS_CACHE[key] = val
            return val
    finally:
        await db.close()

async def set_setting(key: str, value: str):
    if key == "auto_post_channel":
        value = normalize_channel_target(value)
    _SETTINGS_CACHE[key] = str(value)
    db = await get_db_conn()
    try:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        await db.commit()
    finally:
        await db.close()


# ===================== ARXIV KANAL TRACKING =====================
async def is_archive_msg_imported(msg_id: int) -> bool:
    db = await get_db_conn()
    try:
        async with db.execute("SELECT 1 FROM archive_imported WHERE msg_id = ?", (msg_id,)) as cur:
            return bool(await cur.fetchone())
    finally:
        await db.close()

async def mark_archive_msg_imported(msg_id: int, movie_code: str):
    db = await get_db_conn()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO archive_imported (msg_id, movie_code) VALUES (?, ?)",
            (msg_id, str(movie_code))
        )
        await db.commit()
    finally:
        await db.close()

async def get_archive_imported_count() -> int:
    db = await get_db_conn()
    try:
        async with db.execute("SELECT COUNT(*) FROM archive_imported") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0
    finally:
        await db.close()

async def clear_archive_imported_history():
    db = await get_db_conn()
    try:
        await db.execute("DELETE FROM archive_imported")
        await db.commit()
    finally:
        await db.close()

async def get_archive_msg_id_for_code(code: str):
    """Kino qaysi Arxiv xabaridan olinganini qaytaradi (eng birinchi msg_id)."""
    db = await get_db_conn()
    try:
        async with db.execute(
            "SELECT MIN(msg_id) FROM archive_imported WHERE movie_code = ?",
            (str(code).strip(),)
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row and row[0] is not None else None
    finally:
        await db.close()


# ===================== MAVZULI KANALLAR VA EKOTIZIM =====================
async def add_topic_channel(
    chat_id: str,
    title: str,
    invite_link: str,
    topic_category: str = "🎬 Kinolar",
    is_vip_only: int = 0,
    auto_tag_enabled: int = 1
):
    db = await get_db_conn()
    try:
        await db.execute("""
            INSERT OR REPLACE INTO topic_channels
            (chat_id, title, invite_link, topic_category, is_vip_only, auto_tag_enabled)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(chat_id).strip(), title.strip(), invite_link.strip(), topic_category, is_vip_only, auto_tag_enabled))
        await db.commit()
    finally:
        await db.close()

async def get_topic_channels():
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM topic_channels ORDER BY is_vip_only DESC, id ASC") as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def delete_topic_channel(chat_id_or_id: str) -> bool:
    db = await get_db_conn()
    try:
        res = await db.execute(
            "DELETE FROM topic_channels WHERE chat_id = ? OR id = ?",
            (str(chat_id_or_id).strip(), str(chat_id_or_id).strip())
        )
        await db.commit()
        return res.rowcount > 0
    finally:
        await db.close()


# ===================== FOYDALANUVCHILAR, BALANS, KUNLIK BONUS VA REFERAL PUL ISHLASH =====================
async def add_user(user_id: int, username: str, full_name: str, ref_by: int = None) -> dict:
    """
    Yangi foydalanuvchini qo'shadi va agar ref_by bo'lsa,
    taklif qilgan odamga ref_reward_amount miqdorida so'm (balans) yozadi!
    """
    ref_reward = int(await get_setting("ref_reward_amount", config.DEFAULT_REF_REWARD))
    db = await get_db_conn()
    try:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cur:
            exists = await cur.fetchone()
        if exists:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username, full_name, user_id)
            )
            await db.commit()
            return {"is_new": False, "ref_reward": 0}
        else:
            if ref_by and ref_by == user_id:
                ref_by = None
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, ref_by) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, ref_by)
            )
            if ref_by:
                await db.execute("""
                    UPDATE users
                    SET ref_count = ref_count + 1,
                        balance = COALESCE(balance, 0) + ?,
                        total_earned = COALESCE(total_earned, 0) + ?
                    WHERE user_id = ?
                """, (ref_reward, ref_reward, ref_by))
            await db.commit()
            return {"is_new": True, "ref_reward": ref_reward if ref_by else 0}
    finally:
        await db.close()

async def add_user_balance(user_id: int, amount: int):
    db = await get_db_conn()
    try:
        await db.execute("""
            UPDATE users
            SET balance = MAX(0, COALESCE(balance, 0) + ?),
                total_earned = CASE WHEN ? > 0 THEN COALESCE(total_earned, 0) + ? ELSE COALESCE(total_earned, 0) END
            WHERE user_id = ?
        """, (amount, amount, amount, user_id))
        await db.commit()
    finally:
        await db.close()

async def claim_daily_reward(user_id: int) -> dict:
    """
    Kunlik Bonus (Daily Reward) + 7 kunlik Streak tizimi!
    7-kunga yetganda 2x Bonus + 1 kunlik Bepul VIP beradi!
    """
    base_reward = int(await get_setting("daily_reward_amount", config.DEFAULT_DAILY_REWARD))
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    u = await get_user(user_id)
    if not u:
        return {"ok": False, "reason": "not_found"}

    last_date = u.get("last_daily_date")
    cur_streak = u.get("daily_streak") or 0

    if last_date == today_str:
        return {
            "ok": False,
            "reason": "already_claimed",
            "streak": cur_streak,
            "balance": u.get("balance", 0)
        }

    if last_date == yesterday_str:
        new_streak = (cur_streak % 7) + 1
    else:
        new_streak = 1

    # Streak multiplikatori: har kun uchun +15%, 7-kunda esa 2 barobar + 1 kun VIP!
    if new_streak == 7:
        earned = base_reward * 2
        bonus_vip_days = 1
    else:
        earned = int(base_reward * (1 + (new_streak - 1) * 0.15))
        bonus_vip_days = 0

    db = await get_db_conn()
    try:
        await db.execute("""
            UPDATE users
            SET balance = COALESCE(balance, 0) + ?,
                total_earned = COALESCE(total_earned, 0) + ?,
                daily_streak = ?,
                last_daily_date = ?
            WHERE user_id = ?
        """, (earned, earned, new_streak, today_str, user_id))
        await db.commit()
    finally:
        await db.close()

    if bonus_vip_days > 0:
        await extend_user_premium(user_id, bonus_vip_days)

    updated_u = await get_user(user_id)
    return {
        "ok": True,
        "earned": earned,
        "streak": new_streak,
        "bonus_vip_days": bonus_vip_days,
        "balance": updated_u.get("balance", 0)
    }

async def get_user(user_id: int):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
    finally:
        await db.close()

async def get_user_role(user_id: int) -> str:
    if user_id in config.ADMINS:
        return "superadmin"
    u = await get_user(user_id)
    if not u:
        return "user"
    role = u.get("role") or ("admin" if u.get("is_admin") else "user")
    return role

async def set_user_role(user_id: int, role: str):
    perms = config.DEFAULT_ROLE_PERMS.get(role, [])
    is_adm = 1 if role in ("moderator", "admin", "superadmin") else 0
    db = await get_db_conn()
    try:
        async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cur:
            if not await cur.fetchone():
                await db.execute("INSERT INTO users (user_id, username, full_name) VALUES (?, '', 'Staff User')", (user_id,))
        await db.execute(
            "UPDATE users SET role = ?, permissions = ?, is_admin = ? WHERE user_id = ?",
            (role, json.dumps(perms), is_adm, user_id)
        )
        await db.commit()
    finally:
        await db.close()

async def get_user_permissions(user_id: int) -> list:
    if user_id in config.ADMINS:
        return list(config.PERMISSIONS.keys())
    u = await get_user(user_id)
    if not u:
        return []
    if u.get("role") == "superadmin":
        return list(config.PERMISSIONS.keys())
    try:
        perms = json.loads(u.get("permissions") or "[]")
        return perms if isinstance(perms, list) else []
    except Exception:
        return []

async def has_permission(user_id: int, perm_key: str) -> bool:
    role = await get_user_role(user_id)
    if role == "superadmin":
        return True
    if role not in ("moderator", "admin"):
        return False
    perms = await get_user_permissions(user_id)
    return perm_key in perms

async def toggle_user_permission(user_id: int, perm_key: str) -> bool:
    perms = await get_user_permissions(user_id)
    if perm_key in perms:
        perms.remove(perm_key)
        added = False
    else:
        perms.append(perm_key)
        added = True
    db = await get_db_conn()
    try:
        await db.execute("UPDATE users SET permissions = ? WHERE user_id = ?", (json.dumps(perms), user_id))
        await db.commit()
        return added
    finally:
        await db.close()

async def get_all_staff():
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE role IN ('moderator', 'admin', 'superadmin') OR is_admin = 1") as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def is_sadmin_session_valid(user_id: int) -> bool:
    u = await get_user(user_id)
    if not u or not u.get("sadmin_auth_until"):
        return False
    try:
        until_dt = datetime.fromisoformat(u["sadmin_auth_until"])
        return datetime.utcnow() < until_dt
    except Exception:
        return False

async def grant_sadmin_session(user_id: int):
    until_str = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    perms = json.dumps(list(config.PERMISSIONS.keys()))
    db = await get_db_conn()
    try:
        await db.execute(
            "UPDATE users SET role = 'superadmin', is_admin = 1, permissions = ?, sadmin_auth_until = ? WHERE user_id = ?",
            (perms, until_str, user_id)
        )
        await db.commit()
    finally:
        await db.close()


# ===================== PREMIUM (VIP) TIZIMI VA TEGLAR =====================
async def is_user_premium(user_id: int) -> bool:
    u = await get_user(user_id)
    if not u or not u.get("is_premium"):
        return False
    if u.get("premium_until"):
        try:
            until_dt = datetime.fromisoformat(u["premium_until"])
            if datetime.utcnow() > until_dt:
                await set_user_premium(user_id, 0)
                return False
        except Exception:
            pass
    return True

async def set_user_premium(user_id: int, days: int = 30):
    db = await get_db_conn()
    try:
        async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cur:
            if not await cur.fetchone():
                await db.execute("INSERT INTO users (user_id, username, full_name) VALUES (?, '', 'VIP User')", (user_id,))
        if days > 0:
            until_str = (datetime.utcnow() + timedelta(days=days)).isoformat()
            await db.execute(
                "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
                (until_str, user_id)
            )
        else:
            await db.execute(
                "UPDATE users SET is_premium = 0, premium_until = NULL WHERE user_id = ?",
                (user_id,)
            )
        await db.commit()
    finally:
        await db.close()

async def extend_user_premium(user_id: int, add_days: int):
    """Mavjud Premium muddatiga kun qo'shadi (yoki yangidan ochadi)."""
    u = await get_user(user_id)
    now = datetime.utcnow()
    base_dt = now
    if u and u.get("is_premium") and u.get("premium_until"):
        try:
            old_dt = datetime.fromisoformat(u["premium_until"])
            if old_dt > now:
                base_dt = old_dt
        except Exception:
            pass
    new_until = (base_dt + timedelta(days=add_days)).isoformat()
    db = await get_db_conn()
    try:
        await db.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
            (new_until, user_id)
        )
        await db.commit()
    finally:
        await db.close()

async def buy_premium_with_balance(user_id: int, days: int, price: int) -> dict:
    """Foydalanuvchi balansidan pul yechib Premium sotib olish."""
    u = await get_user(user_id)
    if not u:
        return {"ok": False, "reason": "not_found"}
    bal = u.get("balance") or 0
    if bal < price:
        return {"ok": False, "reason": "insufficient", "balance": bal, "needed": price - bal}

    db = await get_db_conn()
    try:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        await db.commit()
    finally:
        await db.close()

    await extend_user_premium(user_id, days)
    new_u = await get_user(user_id)
    return {
        "ok": True,
        "new_balance": new_u.get("balance", 0),
        "premium_until": (new_u.get("premium_until") or "")[:10]
    }

async def set_user_vip_tag(user_id: int, tag: str):
    clean_tag = (tag or "PREMIUM").strip()[:16]
    db = await get_db_conn()
    try:
        await db.execute("UPDATE users SET vip_tag = ? WHERE user_id = ?", (clean_tag, user_id))
        await db.commit()
    finally:
        await db.close()

async def get_all_premium_users():
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_premium = 1") as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def pop_expired_premium_users() -> list:
    """
    Muddati tugagan Premium foydalanuvchilarni topib, bazadan VIP maqomini o'chiradi
    va ularning ro'yxatini qaytaradi (Mavzuli guruhdan tegni olib tashlash uchun).
    """
    now_dt = datetime.utcnow()
    expired_list = []
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_premium = 1 AND premium_until IS NOT NULL") as cur:
            rows = [dict(r) for r in await cur.fetchall()]
        for u in rows:
            try:
                until_dt = datetime.fromisoformat(u["premium_until"])
                if now_dt >= until_dt:
                    await db.execute(
                        "UPDATE users SET is_premium = 0, premium_until = NULL WHERE user_id = ?",
                        (u["user_id"],)
                    )
                    expired_list.append(u)
            except Exception:
                pass
        if expired_list:
            await db.commit()
    finally:
        await db.close()
    return expired_list

async def get_user_lang(user_id: int) -> str:
    if user_id in _USER_LANG_CACHE and _USER_LANG_CACHE[user_id] in ("uz", "ru"):
        return _USER_LANG_CACHE[user_id]
    u = await get_user(user_id)
    lang = (u.get("lang") or "") if u else ""
    if lang in ("uz", "ru"):
        _USER_LANG_CACHE[user_id] = lang
        return lang
    return "uz"

async def has_chosen_lang(user_id: int) -> bool:
    if user_id in _USER_LANG_CACHE and _USER_LANG_CACHE[user_id] in ("uz", "ru"):
        return True
    u = await get_user(user_id)
    lang = (u.get("lang") or "") if u else ""
    if lang in ("uz", "ru"):
        _USER_LANG_CACHE[user_id] = lang
        return True
    return False

async def set_user_lang(user_id: int, lang: str):
    lang = "ru" if lang == "ru" else "uz"
    _USER_LANG_CACHE[user_id] = lang
    db = await get_db_conn()
    try:
        await db.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await db.commit()
    finally:
        await db.close()


# ===================== BAN VA UMUMIY USER FUNKSIYALARI =====================
async def set_ban(user_id: int, status: int = 1):
    db = await get_db_conn()
    try:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (status, user_id))
        await db.commit()
    finally:
        await db.close()

async def is_user_banned(user_id: int) -> bool:
    u = await get_user(user_id)
    return bool(u and u.get("is_banned") == 1)

async def get_all_users():
    db = await get_db_conn()
    try:
        async with db.execute("SELECT user_id FROM users") as cur:
            return [r[0] for r in await cur.fetchall()]
    finally:
        await db.close()

async def get_top_referrers(limit: int = 10):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, full_name, username, ref_count, balance, is_premium, vip_tag FROM users WHERE ref_count > 0 OR balance > 0 ORDER BY ref_count DESC, balance DESC LIMIT ?",
            (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


# ===================== STATISTIKA =====================
async def get_full_stats():
    db = await get_db_conn()
    try:
        now = datetime.utcnow()
        today_str = now.strftime("%Y-%m-%d")
        week_ago_str = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE date(joined_at) = ?", (today_str,)) as cur:
            today_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (week_ago_str,)) as cur:
            week_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1") as cur:
            vip_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1") as cur:
            banned_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE role IN ('moderator', 'admin', 'superadmin')") as cur:
            staff_count = (await cur.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(balance), 0) FROM users") as cur:
            total_balances = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM movies WHERE is_serial = 0") as cur:
            total_movies = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM movies WHERE is_serial = 1") as cur:
            total_serials = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM episodes") as cur:
            total_episodes = (await cur.fetchone())[0]
        async with db.execute("SELECT COALESCE(SUM(views), 0) FROM movies") as cur:
            total_views = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'") as cur:
            pending_orders = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM archive_imported") as cur:
            archive_count = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM topic_channels") as cur:
            topic_ch_count = (await cur.fetchone())[0]

        db_size_kb = round(os.path.getsize(DB_NAME) / 1024, 1) if os.path.exists(DB_NAME) else 0

        return {
            "total_users": total_users,
            "today_users": today_users,
            "week_users": week_users,
            "vip_users": vip_users,
            "banned_users": banned_users,
            "staff_count": staff_count,
            "total_balances": total_balances,
            "total_movies": total_movies,
            "total_serials": total_serials,
            "total_episodes": total_episodes,
            "total_views": total_views,
            "pending_orders": pending_orders,
            "archive_count": archive_count,
            "topic_ch_count": topic_ch_count,
            "db_size_kb": db_size_kb
        }
    finally:
        await db.close()


# ===================== KINOLAR VA SERIALLAR =====================
async def get_next_auto_code() -> str:
    db = await get_db_conn()
    try:
        async with db.execute("SELECT code FROM movies") as cur:
            codes = [r[0] for r in await cur.fetchall()]
        num_codes = [int(c) for c in codes if str(c).isdigit()]
        return str(max(num_codes) + 1) if num_codes else "1"
    finally:
        await db.close()

async def clear_all_movies_only() -> dict:
    """
    Bazani faqat kinolar bo'yicha top-toza qiladi:
    movies, episodes, archive_imported, favorites, history, reactions tozalanadi.
    Foydalanuvchilar, kanallar va sozlamalar saqlanib qoladi.
    """
    db = await get_db_conn()
    try:
        async with db.execute("SELECT COUNT(*) FROM movies") as cur:
            old_movies = (await cur.fetchone())[0]
        await db.execute("DELETE FROM movies")
        await db.execute("DELETE FROM episodes")
        await db.execute("DELETE FROM archive_imported")
        await db.execute("DELETE FROM favorites")
        await db.execute("DELETE FROM history")
        await db.execute("DELETE FROM reactions")
        try:
            await db.execute("UPDATE archive_catalog SET is_imported = 0, imported_code = ''")
        except Exception:
            pass
        await db.commit()
        return {"deleted_movies": old_movies}
    finally:
        await db.close()

async def boost_movies_views(target_spec: str, add_views: int) -> int:
    """
    Super Admin uchun: ma'lum kinolarga yoki barcha kinolarga ko'rishlar sonini qo'shish.
    target_spec: 'all' | '1-10' | '5' | '1,2,5'
    """
    if add_views <= 0:
        return 0
    spec = (target_spec or "").strip().lower()
    db = await get_db_conn()
    try:
        if spec in ("all", "hammasi", "barchasi", "*"):
            res = await db.execute("UPDATE movies SET views = views + ?", (add_views,))
            await db.commit()
            return res.rowcount
        elif "-" in spec:
            parts = spec.split("-", 1)
            if parts[0].strip().isdigit() and parts[1].strip().isdigit():
                start_c, end_c = int(parts[0].strip()), int(parts[1].strip())
                if start_c > end_c:
                    start_c, end_c = end_c, start_c
                codes = [str(c) for c in range(start_c, end_c + 1)]
                placeholders = ",".join("?" for _ in codes)
                res = await db.execute(
                    f"UPDATE movies SET views = views + ? WHERE code IN ({placeholders})",
                    [add_views] + codes
                )
                await db.commit()
                return res.rowcount
        elif "," in spec:
            codes = [c.strip().lstrip("#") for c in spec.split(",") if c.strip()]
            if not codes:
                return 0
            placeholders = ",".join("?" for _ in codes)
            res = await db.execute(
                f"UPDATE movies SET views = views + ? WHERE code IN ({placeholders})",
                [add_views] + codes
            )
            await db.commit()
            return res.rowcount
        else:
            code = spec.lstrip("#")
            res = await db.execute("UPDATE movies SET views = views + ? WHERE code = ?", (add_views, code))
            await db.commit()
            return res.rowcount
    finally:
        await db.close()
    return 0

async def find_movie_by_exact_name(name: str):
    clean = name.strip().lower()
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE LOWER(name) = ? LIMIT 1", (clean,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
    finally:
        await db.close()

async def find_movie_by_file_id(file_id: str):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE file_id = ? LIMIT 1", (file_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
    finally:
        await db.close()

async def add_movie(
    code: str,
    name: str,
    file_id: str,
    genre: str = "🎬 Boshqa",
    year: str = "2025",
    country: str = "AQSH",
    language: str = "O'zbek tilida",
    quality: str = "1080p Full HD",
    imdb: str = "8.2",
    photo_id: str = None,
    caption: str = "",
    is_serial: int = 0,
    first_ep_num: int = 1
):
    code = str(code).strip().lstrip("#")
    db = await get_db_conn()
    try:
        await db.execute("""
            INSERT OR REPLACE INTO movies
            (code, name, genre, year, country, language, quality, imdb, file_id, photo_id, caption, is_serial)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, name, genre, year, country, language, quality, imdb, file_id, photo_id, caption, is_serial))
        if is_serial and file_id:
            await db.execute("""
                INSERT OR REPLACE INTO episodes (movie_code, episode_num, title, file_id)
                VALUES (?, ?, ?, ?)
            """, (code, first_ep_num, f"{first_ep_num}-qism", file_id))
        await db.commit()
    finally:
        await db.close()

async def update_movie_caption(code: str, new_caption: str):
    db = await get_db_conn()
    try:
        await db.execute("UPDATE movies SET caption = ? WHERE code = ?", (new_caption, str(code).strip()))
        await db.commit()
    finally:
        await db.close()

async def update_movie_full_metadata(
    code: str,
    name: str,
    genre: str,
    year: str,
    country: str,
    quality: str,
    language: str,
    caption: str
):
    db = await get_db_conn()
    try:
        await db.execute(
            """
            UPDATE movies
            SET name = ?, genre = ?, year = ?, country = ?, quality = ?, language = ?, caption = ?
            WHERE code = ?
            """,
            (name, genre, year, country, quality, language, caption, str(code).strip())
        )
        await db.commit()
    finally:
        await db.close()

async def add_episode(movie_code: str, episode_num: int, file_id: str, title: str = None):
    movie_code = str(movie_code).strip().lstrip("#")
    if not title:
        title = f"{episode_num}-qism"
    db = await get_db_conn()
    try:
        await db.execute("UPDATE movies SET is_serial = 1 WHERE code = ?", (movie_code,))
        await db.execute("""
            INSERT OR REPLACE INTO episodes (movie_code, episode_num, title, file_id)
            VALUES (?, ?, ?, ?)
        """, (movie_code, episode_num, title, file_id))
        await db.commit()
    finally:
        await db.close()

async def get_episodes(movie_code: str):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM episodes WHERE movie_code = ? ORDER BY episode_num ASC",
            (str(movie_code).strip(),)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def get_episode(movie_code: str, episode_num: int):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM episodes WHERE movie_code = ? AND episode_num = ?",
            (str(movie_code).strip(), episode_num)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
    finally:
        await db.close()

async def get_movie(code: str, increment_view: bool = True):
    code = str(code).strip().lstrip("#")
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE code = ?", (code,)) as cur:
            row = await cur.fetchone()
            if row:
                if increment_view:
                    await db.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
                    await db.commit()
                data = dict(row)
                if increment_view:
                    data["views"] += 1
                return data
            return None
    finally:
        await db.close()

async def delete_movie(code: str) -> bool:
    code = str(code).strip().lstrip("#")
    db = await get_db_conn()
    try:
        res = await db.execute("DELETE FROM movies WHERE code = ?", (code,))
        await db.execute("DELETE FROM episodes WHERE movie_code = ?", (code,))
        await db.execute("DELETE FROM favorites WHERE movie_code = ?", (code,))
        await db.execute("DELETE FROM history WHERE movie_code = ?", (code,))
        await db.commit()
        return res.rowcount > 0
    finally:
        await db.close()

async def update_movie_photo(code: str, photo_id: str) -> bool:
    code = str(code).strip().lstrip("#")
    db = await get_db_conn()
    try:
        res = await db.execute("UPDATE movies SET photo_id = ? WHERE code = ?", (photo_id, code))
        await db.commit()
        return res.rowcount > 0
    finally:
        await db.close()

async def get_movies_paginated(offset: int = 0, limit: int = 10):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) FROM movies") as c_cur:
            total = (await c_cur.fetchone())[0]
        async with db.execute(
            "SELECT * FROM movies ORDER BY CAST(code AS INTEGER) DESC, created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ) as cur:
            items = [dict(r) for r in await cur.fetchall()]
        return items, total
    finally:
        await db.close()

def _norm_movie_key(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[ʻ‘’`ʼ'\ufffd]", "", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _deduplicate_movies(items: list, limit: int = 20) -> list:
    seen = set()
    unique = []
    for m in items:
        key = (_norm_movie_key(m.get("name", "")), str(m.get("year", "")).strip())
        if key not in seen:
            seen.add(key)
            unique.append(m)
            if len(unique) >= limit:
                break
    return unique


async def search_movies_by_name(query: str, limit: int = 20):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        raw_q = query.strip()
        q = f"%{raw_q}%"
        async with db.execute(
            "SELECT * FROM movies WHERE name LIKE ? OR caption LIKE ? OR code LIKE ? ORDER BY CAST(code AS INTEGER) DESC, views DESC LIMIT ?",
            (q, q, q, limit * 3)
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]

        # Apostrof yoki harf farqlari bo'lsa (masalan: "Orgimchak" -> "O'rgimchak"), barcha kinolar ichidan aqlli qidiruv
        norm_q = _norm_movie_key(raw_q)
        if norm_q and len(rows) < limit:
            async with db.execute(
                "SELECT * FROM movies ORDER BY CAST(code AS INTEGER) DESC, views DESC"
            ) as all_cur:
                for r in await all_cur.fetchall():
                    d = dict(r)
                    haystack = f"{_norm_movie_key(d.get('name', ''))} {_norm_movie_key(d.get('caption', ''))} {d.get('code', '')}"
                    if norm_q in haystack:
                        rows.append(d)

        return _deduplicate_movies(rows, limit)
    finally:
        await db.close()

async def get_movies_by_genre(genre: str, limit: int = 30):
    clean_g = re.sub(r"[^\w\s']", "", genre).strip()
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM movies WHERE genre LIKE ? ORDER BY CAST(code AS INTEGER) DESC, views DESC LIMIT ?",
            (f"%{clean_g}%", limit * 2)
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
        return _deduplicate_movies(rows, limit)
    finally:
        await db.close()

async def get_serials_list(limit: int = 25):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM movies WHERE is_serial = 1 ORDER BY CAST(code AS INTEGER) DESC, views DESC LIMIT ?",
            (limit * 2,)
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
        return _deduplicate_movies(rows, limit)
    finally:
        await db.close()

async def get_top_movies(limit: int = 10):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM movies ORDER BY views DESC, likes DESC, CAST(code AS INTEGER) DESC LIMIT ?",
            (limit * 3,)
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
        return _deduplicate_movies(rows, limit)
    finally:
        await db.close()

async def get_latest_movies(limit: int = 10):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM movies ORDER BY CAST(code AS INTEGER) DESC, created_at DESC LIMIT ?",
            (limit * 3,)
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
        return _deduplicate_movies(rows, limit)
    finally:
        await db.close()

async def get_random_movie():
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies ORDER BY RANDOM() LIMIT 1") as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
    finally:
        await db.close()

async def get_all_movies(limit: int = 1000):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies ORDER BY created_at DESC LIMIT ?", (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


# ===================== SEVIMLILAR, TARIX VA REAKSIYALAR =====================
async def toggle_favorite(user_id: int, movie_code: str) -> bool:
    db = await get_db_conn()
    try:
        async with db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND movie_code = ?",
            (user_id, movie_code)
        ) as cur:
            exists = await cur.fetchone()
        if exists:
            await db.execute("DELETE FROM favorites WHERE user_id = ? AND movie_code = ?", (user_id, movie_code))
            await db.commit()
            return False
        else:
            await db.execute("INSERT INTO favorites (user_id, movie_code) VALUES (?, ?)", (user_id, movie_code))
            await db.commit()
            return True
    finally:
        await db.close()

async def is_favorite(user_id: int, movie_code: str) -> bool:
    db = await get_db_conn()
    try:
        async with db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND movie_code = ?",
            (user_id, movie_code)
        ) as cur:
            return bool(await cur.fetchone())
    finally:
        await db.close()

async def get_user_favorites(user_id: int):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT m.* FROM movies m
            JOIN favorites f ON m.code = f.movie_code
            WHERE f.user_id = ?
            ORDER BY f.added_at DESC
        """, (user_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def add_history(user_id: int, movie_code: str):
    db = await get_db_conn()
    try:
        await db.execute("""
            INSERT OR REPLACE INTO history (user_id, movie_code, viewed_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (user_id, movie_code))
        await db.commit()
    finally:
        await db.close()

async def get_user_history(user_id: int, limit: int = 10):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT m.* FROM movies m
            JOIN history h ON m.code = h.movie_code
            WHERE h.user_id = ?
            ORDER BY h.viewed_at DESC LIMIT ?
        """, (user_id, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def get_user_movie_rating(user_id: int, movie_code: str) -> int:
    db = await get_db_conn()
    try:
        async with db.execute(
            "SELECT reaction FROM reactions WHERE user_id = ? AND movie_code = ?",
            (user_id, str(movie_code))
        ) as cur:
            row = await cur.fetchone()
            if row and str(row[0]).isdigit():
                return int(row[0])
            return 0
    finally:
        await db.close()

async def rate_movie_stars(user_id: int, movie_code: str, stars: int) -> dict:
    """5 yulduzli baholash tizimi (1..5 ⭐)."""
    stars = max(1, min(5, int(stars)))
    code = str(movie_code).strip()
    db = await get_db_conn()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO reactions (user_id, movie_code, reaction) VALUES (?, ?, ?)",
            (user_id, code, str(stars))
        )
        async with db.execute(
            "SELECT reaction FROM reactions WHERE movie_code = ?",
            (code,)
        ) as cur:
            rows = await cur.fetchall()
        numeric_votes = [int(r[0]) for r in rows if str(r[0]).isdigit() and 1 <= int(r[0]) <= 5]
        cnt = len(numeric_votes)
        avg = (sum(numeric_votes) / cnt) if cnt > 0 else float(stars)
        await db.execute(
            "UPDATE movies SET imdb = ?, likes = ? WHERE code = ?",
            (f"{avg:.1f}", cnt, code)
        )
        await db.commit()
        return {"stars": stars, "avg": round(avg, 1), "count": cnt}
    finally:
        await db.close()

async def react_movie(user_id: int, movie_code: str, new_reaction: str):
    db = await get_db_conn()
    try:
        async with db.execute(
            "SELECT reaction FROM reactions WHERE user_id = ? AND movie_code = ?",
            (user_id, movie_code)
        ) as cur:
            row = await cur.fetchone()

        if row:
            old_reaction = row[0]
            if old_reaction == new_reaction:
                await db.execute("DELETE FROM reactions WHERE user_id = ? AND movie_code = ?", (user_id, movie_code))
                col = "likes" if new_reaction == "like" else "dislikes"
                await db.execute(f"UPDATE movies SET {col} = MAX(0, {col} - 1) WHERE code = ?", (movie_code,))
                await db.commit()
                return "removed"
            else:
                await db.execute(
                    "UPDATE reactions SET reaction = ? WHERE user_id = ? AND movie_code = ?",
                    (new_reaction, user_id, movie_code)
                )
                if new_reaction == "like":
                    await db.execute("UPDATE movies SET likes = likes + 1, dislikes = MAX(0, dislikes - 1) WHERE code = ?", (movie_code,))
                else:
                    await db.execute("UPDATE movies SET dislikes = dislikes + 1, likes = MAX(0, likes - 1) WHERE code = ?", (movie_code,))
                await db.commit()
                return "switched"
        else:
            await db.execute(
                "INSERT INTO reactions (user_id, movie_code, reaction) VALUES (?, ?, ?)",
                (user_id, movie_code, new_reaction)
            )
            col = "likes" if new_reaction == "like" else "dislikes"
            await db.execute(f"UPDATE movies SET {col} = {col} + 1 WHERE code = ?", (movie_code,))
            await db.commit()
            return "added"
    finally:
        await db.close()


# ===================== MAJBURIY OBUNA KANALLARI =====================
async def add_channel(channel_id: str, title: str, invite_link: str, ch_type: str = "public"):
    global _CHANNELS_CACHE
    _CHANNELS_CACHE = None
    db = await get_db_conn()
    try:
        await db.execute("""
            INSERT OR REPLACE INTO channels (channel_id, title, invite_link, ch_type)
            VALUES (?, ?, ?, ?)
        """, (str(channel_id).strip(), title.strip(), invite_link.strip(), ch_type))
        await db.commit()
    finally:
        await db.close()

async def get_channels():
    global _CHANNELS_CACHE
    if _CHANNELS_CACHE is not None:
        return _CHANNELS_CACHE
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels") as cur:
            _CHANNELS_CACHE = [dict(r) for r in await cur.fetchall()]
            return _CHANNELS_CACHE
    finally:
        await db.close()

async def delete_channel(channel_id: str) -> bool:
    global _CHANNELS_CACHE
    _CHANNELS_CACHE = None
    db = await get_db_conn()
    try:
        res = await db.execute("DELETE FROM channels WHERE channel_id = ? OR id = ?", (str(channel_id), str(channel_id)))
        await db.commit()
        return res.rowcount > 0
    finally:
        await db.close()

async def save_join_request(user_id: int, channel_id: str):
    db = await get_db_conn()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO join_requests (user_id, channel_id) VALUES (?, ?)",
            (user_id, str(channel_id))
        )
        await db.execute(
            "INSERT OR REPLACE INTO channel_members (user_id, channel_id, status, updated_at) VALUES (?, ?, 'request', CURRENT_TIMESTAMP)",
            (user_id, str(channel_id))
        )
        await db.commit()
    finally:
        await db.close()

async def delete_join_request(user_id: int, channel_id: str):
    db = await get_db_conn()
    try:
        await db.execute(
            "DELETE FROM join_requests WHERE user_id = ? AND channel_id = ?",
            (user_id, str(channel_id))
        )
        await db.commit()
    finally:
        await db.close()

async def has_join_request(user_id: int, channel_id: str) -> bool:
    db = await get_db_conn()
    try:
        async with db.execute(
            "SELECT 1 FROM join_requests WHERE user_id = ? AND channel_id = ?",
            (user_id, str(channel_id))
        ) as cur:
            return bool(await cur.fetchone())
    finally:
        await db.close()

async def set_channel_member_status(user_id: int, channel_id: str, status: str):
    """
    1,000,000+ a'zoli kanallarda ham kirish-chiqishni real-time qayd etish.
    Agar user kanaldan chiqib ketsa ('left' yoki 'kicked'), uning join_request
    yozuvi ham darhol o'chiriladi, shunda u qayta obuna bo'lmaguncha botdan foydalana olmaydi!
    """
    ch_str = str(channel_id)
    db = await get_db_conn()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO channel_members (user_id, channel_id, status, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, ch_str, status)
        )
        if status in ("left", "kicked"):
            await db.execute(
                "DELETE FROM join_requests WHERE user_id = ? AND channel_id = ?",
                (user_id, ch_str)
            )
        await db.commit()
    finally:
        await db.close()

async def has_user_left_channel(user_id: int) -> bool:
    db = await get_db_conn()
    try:
        async with db.execute(
            "SELECT 1 FROM channel_members WHERE user_id = ? AND status IN ('left', 'kicked')",
            (user_id,)
        ) as cur:
            return bool(await cur.fetchone())
    finally:
        await db.close()


# ===================== KINO BUYURTMALAR =====================
async def get_user_today_orders_count(user_id: int) -> int:
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    db = await get_db_conn()
    try:
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND date(created_at) = ?",
            (user_id, today_str)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0
    finally:
        await db.close()

async def create_order(user_id: int, full_name: str, username: str, movie_name: str) -> int:
    db = await get_db_conn()
    try:
        cur = await db.execute("""
            INSERT INTO orders (user_id, full_name, username, movie_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, full_name, username, movie_name))
        await db.commit()
        return cur.lastrowid
    finally:
        await db.close()

async def get_pending_orders(limit: int = 15):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE status IN ('pending', 'accepted') ORDER BY created_at DESC LIMIT ?", (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()

async def get_order(order_id: int):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
    finally:
        await db.close()

async def accept_order(order_id: int):
    db = await get_db_conn()
    try:
        await db.execute("UPDATE orders SET status = 'accepted' WHERE id = ?", (order_id,))
        await db.commit()
    finally:
        await db.close()

async def close_order(order_id: int):
    db = await get_db_conn()
    try:
        await db.execute("UPDATE orders SET status = 'done' WHERE id = ?", (order_id,))
        await db.commit()
    finally:
        await db.close()


# ===================== ARXIV KATALOGI ( AQLLI KINO VA SERIAL YUKLASH ) =====================
async def upsert_archive_catalog_item(
    msg_id: int,
    file_id: str = "",
    file_name: str = "",
    video_height: int = 0,
    raw_caption: str = "",
    parsed_name: str = "",
    base_title: str = "",
    year: str = "2024",
    country: str = "AQSH",
    genre: str = "🔥 Jangari",
    quality: str = "1080p Full HD",
    is_serial: int = 0,
    part_num: int = 1,
    is_imported: int = 0,
    imported_code: str = ""
):
    db = await get_db_conn()
    try:
        async with db.execute("SELECT file_id, is_imported, imported_code FROM archive_catalog WHERE msg_id = ?", (msg_id,)) as cur:
            existing = await cur.fetchone()
        if existing:
            if not file_id and existing[0]:
                file_id = existing[0]
            if not is_imported and existing[1]:
                is_imported = existing[1]
            if not imported_code and existing[2]:
                imported_code = existing[2]
        await db.execute("""
            INSERT OR REPLACE INTO archive_catalog
            (msg_id, file_id, file_name, video_height, raw_caption, parsed_name, base_title,
             year, country, genre, quality, is_serial, part_num, is_imported, imported_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id, file_id, file_name, video_height, raw_caption, parsed_name, base_title,
            year, country, genre, quality, is_serial, part_num, is_imported, imported_code
        ))
        await db.commit()
    finally:
        await db.close()

async def update_archive_catalog_file_id(msg_id: int, file_id: str):
    db = await get_db_conn()
    try:
        await db.execute("UPDATE archive_catalog SET file_id = ? WHERE msg_id = ?", (file_id, msg_id))
        await db.commit()
    finally:
        await db.close()

async def replace_archive_catalog_msg_id(old_mid: int, new_mid: int, new_caption: str, file_id: str = ""):
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM archive_catalog WHERE msg_id = ?", (old_mid,)) as cur:
            row = await cur.fetchone()
        if row:
            d = dict(row)
            fid = file_id or d.get("file_id", "")
            await db.execute("DELETE FROM archive_catalog WHERE msg_id = ?", (old_mid,))
            await db.execute("""
                INSERT OR REPLACE INTO archive_catalog
                (msg_id, file_id, file_name, video_height, raw_caption, parsed_name, base_title,
                 year, country, genre, quality, is_serial, part_num, is_imported, imported_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_mid, fid, d.get("file_name", ""), d.get("video_height", 0),
                new_caption, d.get("parsed_name", ""), d.get("base_title", ""),
                d.get("year", "2024"), d.get("country", "AQSH"), d.get("genre", "🔥 Jangari"),
                d.get("quality", "1080p Full HD"), d.get("is_serial", 0), d.get("part_num", 1),
                d.get("is_imported", 0), d.get("imported_code", "")
            ))
            await db.commit()
    finally:
        await db.close()

async def mark_archive_catalog_imported(msg_ids: list, movie_code: str):
    if not msg_ids:
        return
    db = await get_db_conn()
    try:
        for mid in msg_ids:
            await db.execute(
                "UPDATE archive_catalog SET is_imported = 1, imported_code = ? WHERE msg_id = ?",
                (str(movie_code), int(mid))
            )
            await db.execute(
                "INSERT OR REPLACE INTO archive_imported (msg_id, movie_code) VALUES (?, ?)",
                (int(mid), str(movie_code))
            )
        await db.commit()
    finally:
        await db.close()

async def get_unimported_archive_movies_grouped(limit_groups: int = 10) -> list:
    """
    Arxivdagi hali yuklanmagan KINOLARNI (seriallarni skip qilib!) eng boshidan tartib bilan oladi.
    Agar kinoning bir nechta qismlari bo'lsa (hatto orada boshqa kino bo'lsa yoki 3-qism 2-qismdan oldin tursa ham),
    barchasini bitta 'base_title' guruhiga jamlaydi va qismlarni 1, 2, 3... tartibida saralaydi!
    """
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM archive_catalog
            WHERE is_serial = 0
            ORDER BY msg_id ASC
        """) as cur:
            all_rows = [dict(r) for r in await cur.fetchall()]

        # Guruhlash: base_title bo'yicha
        groups_map = {}
        group_order = []
        for r in all_rows:
            btitle = (r.get("base_title") or r.get("parsed_name") or f"movie_{r['msg_id']}").strip()
            key = btitle.lower()
            if key not in groups_map:
                groups_map[key] = {
                    "base_title": btitle,
                    "first_msg_id": r["msg_id"],
                    "items": []
                }
                group_order.append(key)
            groups_map[key]["items"].append(r)

        result_groups = []
        for key in group_order:
            grp = groups_map[key]
            items = grp["items"]
            # Agar ushbu kinoning barcha qismlari allaqachon yuklangan bo'lsa, skip qilamiz
            unimported_items = [it for it in items if not it.get("is_imported")]
            if not unimported_items:
                continue
            # Qismlarni part_num, so'ngra msg_id bo'yicha 1, 2, 3... qilib tartiblaymiz
            # Dublikat part_num (masalan Mumiyo 2 marta tashlangan bo'lsa) ni filtrlaymiz
            sorted_items = sorted(items, key=lambda x: (x.get("part_num", 1), x["msg_id"]))
            unique_parts = []
            seen_parts = set()
            for it in sorted_items:
                pnum = it.get("part_num", 1)
                if len(sorted_items) > 1:
                    if pnum in seen_parts:
                        continue
                    seen_parts.add(pnum)
                unique_parts.append(it)
            grp["items"] = unique_parts
            grp["all_msg_ids"] = [it["msg_id"] for it in items]
            result_groups.append(grp)
            if len(result_groups) >= limit_groups:
                break
        return result_groups
    finally:
        await db.close()

async def get_unimported_archive_serials_grouped(limit_groups: int = 5) -> list:
    """
    Arxivdagi hali yuklanmagan SERIALLARNI (masalan, Afsungar Merlin 1..65, Envel Qahramonlari 1..52)
    tahlil qilib, har bir serialning barcha qismlarini 1 ta serial kodi ostida 1, 2, 3... qilib jamlaydi.
    """
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM archive_catalog
            WHERE is_serial = 1
            ORDER BY msg_id ASC
        """) as cur:
            all_rows = [dict(r) for r in await cur.fetchall()]

        groups_map = {}
        group_order = []
        for r in all_rows:
            btitle = (r.get("base_title") or r.get("parsed_name") or f"serial_{r['msg_id']}").strip()
            key = btitle.lower()
            if key not in groups_map:
                groups_map[key] = {
                    "base_title": btitle,
                    "first_msg_id": r["msg_id"],
                    "items": []
                }
                group_order.append(key)
            groups_map[key]["items"].append(r)

        result_groups = []
        for key in group_order:
            grp = groups_map[key]
            items = grp["items"]
            unimported_items = [it for it in items if not it.get("is_imported")]
            if not unimported_items:
                continue
            sorted_items = sorted(items, key=lambda x: (x.get("part_num", 1), x["msg_id"]))
            grp["items"] = sorted_items
            grp["all_msg_ids"] = [it["msg_id"] for it in items]
            result_groups.append(grp)
            if len(result_groups) >= limit_groups:
                break
        return result_groups
    finally:
        await db.close()

async def get_messy_archive_catalog_items() -> list:
    """
    Arxiv kanalida tavsifi chala yoki tartiblanmagan postlarni qaytaradi.
    Standart shablon: '🎬 Nomi:' va '🌏 Davlati:' va '📅 Yili:' va '📀 Sifati:' bo'lishi shart.
    """
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM archive_catalog ORDER BY msg_id ASC") as cur:
            rows = [dict(r) for r in await cur.fetchall()]
        messy = []
        for r in rows:
            cap = (r.get("raw_caption") or "").strip()
            has_standard = (
                "🎬 Nomi:" in cap
                and "🌏 Davlati:" in cap
                and "📅 Yili:" in cap
                and "📀 Sifati:" in cap
            )
            if not has_standard:
                messy.append(r)
        return messy
    finally:
        await db.close()

async def get_archive_catalog_stats() -> dict:
    db = await get_db_conn()
    try:
        async with db.execute("SELECT COUNT(*) FROM archive_catalog WHERE is_serial = 0") as cur:
            total_movie_files = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(DISTINCT LOWER(base_title)) FROM archive_catalog WHERE is_serial = 0") as cur:
            total_movie_groups = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(DISTINCT LOWER(base_title)) FROM archive_catalog WHERE is_serial = 0 AND is_imported = 0") as cur:
            rem_movie_groups = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM archive_catalog WHERE is_serial = 1") as cur:
            total_serial_eps = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(DISTINCT LOWER(base_title)) FROM archive_catalog WHERE is_serial = 1") as cur:
            total_serial_groups = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(DISTINCT LOWER(base_title)) FROM archive_catalog WHERE is_serial = 1 AND is_imported = 0") as cur:
            rem_serial_groups = (await cur.fetchone())[0]
        return {
            "total_movie_files": total_movie_files,
            "total_movie_groups": total_movie_groups,
            "rem_movie_groups": rem_movie_groups,
            "total_serial_eps": total_serial_eps,
            "total_serial_groups": total_serial_groups,
            "rem_serial_groups": rem_serial_groups,
        }
    finally:
        await db.close()


# ===================== BAZA EXPORT VA IMPORT =====================
async def export_full_json(filepath: str = "movieland_export.json") -> str:
    db = await get_db_conn()
    try:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies") as cur:
            movies = [dict(r) for r in await cur.fetchall()]
        async with db.execute("SELECT * FROM episodes") as cur:
            episodes = [dict(r) for r in await cur.fetchall()]
        async with db.execute("SELECT * FROM users") as cur:
            users = [dict(r) for r in await cur.fetchall()]
        async with db.execute("SELECT * FROM channels") as cur:
            channels = [dict(r) for r in await cur.fetchall()]

        payload = {
            "exported_at": datetime.utcnow().isoformat(),
            "movies": movies,
            "episodes": episodes,
            "users": users,
            "channels": channels
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return filepath
    finally:
        await db.close()

async def import_full_json(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    movies = data.get("movies", [])
    episodes = data.get("episodes", [])
    users = data.get("users", [])

    db = await get_db_conn()
    try:
        m_cnt, e_cnt, u_cnt = 0, 0, 0
        for m in movies:
            await db.execute("""
                INSERT OR REPLACE INTO movies
                (code, name, genre, year, country, language, quality, imdb, file_id, photo_id, caption, views, likes, dislikes, is_serial)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(m["code"]), m["name"], m.get("genre", "🎬 Boshqa"), m.get("year", "2025"),
                m.get("country", "AQSH"), m.get("language", "O'zbek tilida"), m.get("quality", "1080p"),
                m.get("imdb", "8.0"), m["file_id"], m.get("photo_id"), m.get("caption", ""),
                m.get("views", 0), m.get("likes", 0), m.get("dislikes", 0), m.get("is_serial", 0)
            ))
            m_cnt += 1

        for ep in episodes:
            await db.execute("""
                INSERT OR REPLACE INTO episodes (movie_code, episode_num, title, file_id)
                VALUES (?, ?, ?, ?)
            """, (str(ep["movie_code"]), ep["episode_num"], ep.get("title", ""), ep["file_id"]))
            e_cnt += 1

        for u in users:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username, full_name, role, permissions, is_premium, premium_until, ref_count, balance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                u["user_id"], u.get("username", ""), u.get("full_name", ""),
                u.get("role", "user"), u.get("permissions", "[]"),
                u.get("is_premium", 0), u.get("premium_until"), u.get("ref_count", 0), u.get("balance", 0)
            ))
            u_cnt += 1

        await db.commit()
        return {"movies": m_cnt, "episodes": e_cnt, "users": u_cnt}
    finally:
        await db.close()

async def export_movies_csv(filepath: str = "movies_export.csv") -> str:
    movies = await get_all_movies(10000)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Kod", "Nomi", "Janr", "Yili", "Davlat", "Sifat", "IMDb", "Ko'rishlar", "Like", "Serialmi", "Tavsif"])
        for m in movies:
            writer.writerow([
                m["code"], m["name"], m.get("genre", ""), m.get("year", ""),
                m.get("country", ""), m.get("quality", ""), m.get("imdb", ""),
                m.get("views", 0), m.get("likes", 0), "Ha" if m.get("is_serial") else "Yo'q",
                m.get("caption", "")
            ])
    return filepath
