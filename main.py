import asyncio
import atexit
import logging
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime

# Bot qaysi papkadan ishga tushirilmasin, ishchi papka doim loyiha papkasi bo'ladi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
PID_FILE = os.path.join(BASE_DIR, "bot.pid")
LOCK_PORT = 49512
_lock_socket = None

def is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                capture_output=True, text=True, timeout=3
            )
            return str(pid) in res.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def kill_pid(pid: int):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
        else:
            os.kill(pid, signal.SIGKILL)
    except Exception as e:
        logging.warning(f"Eski PID {pid} ni to'xtatishda xato: {e}")

def cleanup_pid():
    global _lock_socket
    try:
        if _lock_socket:
            _lock_socket.close()
            _lock_socket = None
    except Exception:
        pass
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass

def single_instance_guard():
    """
    Botning faqat 1 dona instansiyasi ishlashini 100% kafolatlaydi!
    Agar avvalgi nusxa osilib qolgan bo'lsa, uni avtomatik aniqlab to'xtatadi.
    """
    global _lock_socket
    my_pid = os.getpid()

    # 1. bot.pid orqali eski jarayonni tekshirish
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                old_pid_str = f.read().strip()
            if old_pid_str.isdigit():
                old_pid = int(old_pid_str)
                if old_pid != my_pid and is_pid_alive(old_pid):
                    logging.warning(f"Avvalgi bot jarayoni (PID: {old_pid}) aniqlandi. U to'xtatilmoqda...")
                    kill_pid(old_pid)
                    time.sleep(1)
        except Exception as e:
            logging.warning(f"PID fayl tekshirishda xato: {e}")

    # 2. Port orqali socket lock
    for attempt in range(3):
        try:
            _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            _lock_socket.bind(("127.0.0.1", LOCK_PORT))
            _lock_socket.listen(1)
            break
        except Exception:
            logging.warning(f"Port {LOCK_PORT} band. Eski jarayonlar tozalanyapti (Urinish {attempt+1}/3)...")
            if os.name == "nt":
                try:
                    out = subprocess.run(
                        ["wmic", "process", "where", "name='python.exe' and commandline like '%main.py%'", "get", "processid"],
                        capture_output=True, text=True, timeout=5
                    ).stdout
                    for line in out.splitlines():
                        line = line.strip()
                        if line.isdigit() and int(line) != my_pid:
                            kill_pid(int(line))
                except Exception:
                    pass
            else:
                try:
                    out = subprocess.run(["pgrep", "-f", "python.*main.py"], capture_output=True, text=True, timeout=5).stdout
                    for line in out.splitlines():
                        line = line.strip()
                        if line.isdigit() and int(line) != my_pid:
                            kill_pid(int(line))
                except Exception:
                    pass
            time.sleep(1)

    # 3. Joriy PID ni yozamiz
    try:
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(my_pid))
    except Exception as e:
        logging.warning(f"PID faylga yozishda xato: {e}")

    atexit.register(cleanup_pid)
import re
from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, ChatJoinRequest, ChatMemberUpdated,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaVideo
)
from aiogram.enums import ChatMemberStatus

import config
import database as db
import keyboards as kb
import ai_service
from i18n import b_vals, t
from ecosystem_handlers import (
    eco_router,
    apply_vip_tag_across_ecosystem,
    remove_vip_tag_across_ecosystem,
    log_to_activity_topic,
    render_economy_admin_panel
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Yuqori yuklama (100,000+ parallel so'rov) uchun AiohttpSession
session = AiohttpSession(limit=500)
bot = Bot(token=config.BOT_TOKEN, session=session)
dp = Dispatcher()
fallback_router = Router()

BOT_USERNAME = ""


# ===================== 1. GLOBAL PROTECT CONTENT MIDDLEWARE (100% FORWARD BLOKLASH) =====================
@bot.session.middleware
async def global_protect_content_middleware(make_request, bot_instance, method):
    """
    Agar protect_content == '1' bo'lsa, botdan foydalanuvchilar lichkasiga (chat_id > 0)
    yuborilayotgan BARCHA xabarlar, menyular, kinolar va seriallarda Forward/Save ni 100% bloklaydi!
    """
    if hasattr(method, "protect_content") and hasattr(method, "chat_id"):
        chat_id = getattr(method, "chat_id", None)
        if isinstance(chat_id, int) and chat_id > 0:
            prot = await db.get_setting("protect_content", "1")
            if str(prot) == "1":
                method = method.model_copy(update={"protect_content": True})
    return await make_request(bot_instance, method)


# ===================== FSM HOLATLARI =====================
class SuperAuthState(StatesGroup):
    waiting_password = State()
    change_password = State()

class ArchivePullState(StatesGroup):
    waiting_count = State()
    waiting_movies_count = State()
    waiting_serials_count = State()

class SuperViewsBoostState(StatesGroup):
    waiting_spec = State()

class StaffManageState(StatesGroup):
    waiting_chat_id = State()

class AIKeyState(StatesGroup):
    waiting_api_key = State()

class BackupImportState(StatesGroup):
    waiting_file = State()

class VIPManageState(StatesGroup):
    give_id = State()
    remove_id = State()

class ProMovieState(StatesGroup):
    code = State()
    name = State()
    genre = State()
    details = State()
    quality = State()
    video = State()
    caption = State()

class FastMovieState(StatesGroup):
    waiting_videos = State()

class EpisodeState(StatesGroup):
    movie_code = State()
    episode_num = State()
    video = State()

class DeleteMovieState(StatesGroup):
    code = State()

class SearchState(StatesGroup):
    query = State()

class OrderState(StatesGroup):
    movie_name = State()

class AnswerOrderState(StatesGroup):
    text = State()

class AddChannelState(StatesGroup):
    ch_type = State()
    info = State()

class DeleteChannelState(StatesGroup):
    ch_id = State()

class BroadcastState(StatesGroup):
    message = State()

class SetAutoPostState(StatesGroup):
    channel_id = State()

class UserManageState(StatesGroup):
    ban_id = State()

class EditMoviePhotoState(StatesGroup):
    waiting_photo = State()


# ===================== YORDAMCHI FUNKSIYALAR =====================
async def get_bot_username() -> str:
    global BOT_USERNAME
    if not BOT_USERNAME:
        BOT_USERNAME = (await bot.get_me()).username
    return BOT_USERNAME

_SUB_OK_CACHE = {}
_SUB_OK_TTL = 90  # soniya: obunasi tasdiqlangan foydalanuvchi qayta tekshirilmaydi (chiqib ketsa darhol bekor qilinadi)


def invalidate_sub_cache(user_id: int):
    _SUB_OK_CACHE.pop(user_id, None)


async def check_subscriptions(user_id: int) -> list:
    """
    1,000,000+ foydalanuvchili Ochiq, Yopiq va Zayavkali kanallarda obunani aniq tekshirish.
    Agar user kanaldan chiqib ketgan bo'lsa ('left' yoki 'kicked'), zayavkali kanal bo'lsa ham
    uning eski join_request yozuvi o'chirilgan bo'ladi va qayta obuna bo'lmaguncha o'tkazmaydi!
    """
    exp = _SUB_OK_CACHE.get(user_id)
    if exp and exp > time.monotonic():
        return []
    role = await db.get_user_role(user_id)
    if role in ("moderator", "admin", "superadmin"):
        return []
    channels = await db.get_channels()
    if not channels:
        return []

    unsubscribed = []
    for ch in channels:
        ch_type = ch.get("ch_type", "public")
        ch_id = ch["channel_id"]
        if ch_type == "url":
            continue

        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            st = member.status
            if st in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR) or (
                st == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", True)
            ):
                await db.set_channel_member_status(user_id, str(ch_id), "member")
                continue

            if ch_type == "request" and st == ChatMemberStatus.LEFT and await db.has_join_request(user_id, str(ch_id)):
                continue

            unsubscribed.append(ch)
        except Exception as e:
            if ch_type == "request" and await db.has_join_request(user_id, str(ch_id)):
                continue
            logging.warning(f"Kanal tekshirishda xato ({ch_id}): {e}")

    if unsubscribed:
        url_channels = [c for c in channels if c.get("ch_type") == "url"]
        return unsubscribed + url_channels
    _SUB_OK_CACHE[user_id] = time.monotonic() + _SUB_OK_TTL
    if len(_SUB_OK_CACHE) > 200000:
        _SUB_OK_CACHE.clear()
    return []


class MandatorySubMiddleware(BaseMiddleware):
    """
    Foydalanuvchi botdagi kanallardan chiqib ketsa, botning hech bir bo'limidan
    foydalana olmaydi va bot unga kanallardan chiqib ketmaslikni eslatadi!
    """
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user or user.is_bot:
            return await handler(event, data)

        # Faqat lichkadagi (private) xabar va tugmalarni tekshiramiz
        if isinstance(event, Message):
            if event.chat.type != "private":
                return await handler(event, data)
            txt = (event.text or "").strip()
            # Til tanlash, Super-Admin kirish va /start (til tanlanmagan bo'lsa) o'tkaziladi
            if txt.startswith(("/spanel", "/sadmin", "/panel", "/admin", "/lang", "/language")) or txt in b_vals("lang"):
                return await handler(event, data)
            if txt.startswith("/start") and not await db.has_chosen_lang(user.id):
                return await handler(event, data)
            state: FSMContext = data.get("state")
            if state:
                cur_st = await state.get_state()
                if cur_st == SuperAuthState.waiting_password.state:
                    return await handler(event, data)
            if txt.startswith("/start"):
                # /start o'z ichida til va obunani tekshiradi
                return await handler(event, data)

        elif isinstance(event, CallbackQuery):
            if event.message and event.message.chat.type != "private":
                return await handler(event, data)
            cb_data = event.data or ""
            if cb_data.startswith(("set_lang:", "check_sub")):
                return await handler(event, data)

        role = await db.get_user_role(user.id)
        if role in ("moderator", "admin", "superadmin"):
            return await handler(event, data)

        # Agar hali til tanlamagan bo'lsa, avval til tanlash oynasini chiqaramiz
        if not await db.has_chosen_lang(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer()
                await event.message.answer(t("choose_lang", "uz"), reply_markup=kb.language_select_inline(), parse_mode="HTML")
            elif isinstance(event, Message):
                await event.answer(t("choose_lang", "uz"), reply_markup=kb.language_select_inline(), parse_mode="HTML")
            return

        unsubscribed = await check_subscriptions(user.id)
        if unsubscribed:
            lang = await db.get_user_lang(user.id)
            left_before = await db.has_user_left_channel(user.id)
            warn_txt = t("sub_left_reminder", lang) if left_before else t("sub_first", lang)
            markup = kb.subscription_keyboard(unsubscribed, lang=lang)
            if isinstance(event, CallbackQuery):
                await event.answer(t("sub_not_all", lang), show_alert=True)
                await event.message.answer(warn_txt, reply_markup=markup, parse_mode="HTML")
            elif isinstance(event, Message):
                await event.answer(warn_txt, reply_markup=markup, parse_mode="HTML")
            return

        return await handler(event, data)


dp.message.middleware(MandatorySubMiddleware())
dp.callback_query.middleware(MandatorySubMiddleware())

def format_movie_caption(movie: dict, bot_username: str, current_ep: int = None, protect: bool = True, lang: str = "uz") -> str:
    rating = movie.get("imdb", "8.4")
    votes = movie.get("likes", 0)
    views = movie.get("views", 0)

    if lang == "ru":
        caption_extra = f"\n<blockquote>📖 <b>Описание:</b> <i>{movie['caption']}</i></blockquote>\n" if movie.get("caption") else ""
        ep_txt = f" <i>({current_ep}-серия)</i>" if current_ep else ""
        prot_badge = "🔒 <i>Контент защищен авторским правом (Пересылка закрыта)</i>\n" if protect else ""
        return (
            f"🎬 <b>«{movie['name']}»</b>{ep_txt}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"📅 <b>Год выпуска:</b> {movie.get('year', '2024')}\n"
            f"🌏 <b>Страна:</b> {movie.get('country', 'AQSH')}\n"
            f"🎞 <b>Жанр:</b> {movie.get('genre', '🔥 Jangari')}\n"
            f"📀 <b>Качество:</b> {movie.get('quality', '1080p Full HD')}\n"
            f"🇺🇿 <b>Озвучка:</b> {movie.get('language', 'O‘zbek tilida')}\n"
            f"⭐ <b>Рейтинг:</b> {rating} / 10 ({votes} оценок)\n"
            f"👁 <b>Просмотров:</b> {views:,} • 🔢 <b>Код:</b> <code>{movie['code']}</code>"
            f"</blockquote>"
            f"{caption_extra}"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{prot_badge}"
            f"📢 <b>Канал:</b> @movieee_land • 🤖 @{bot_username}"
        )

    caption_extra = f"\n<blockquote>📖 <b>Tavsif:</b> <i>{movie['caption']}</i></blockquote>\n" if movie.get("caption") else ""
    ep_txt = f" <i>({current_ep}-qism)</i>" if current_ep else ""
    prot_badge = "🔒 <i>Kontent mualliflik huquqi bilan himoyalangan (Forward yopiq)</i>\n" if protect else ""
    return (
        f"🎬 <b>«{movie['name']}»</b>{ep_txt}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"📅 <b>Chiqarilgan yili:</b> {movie.get('year', '2024')}\n"
        f"🌏 <b>Davlati:</b> {movie.get('country', 'AQSH')}\n"
        f"🎞 <b>Janri:</b> {movie.get('genre', '🔥 Jangari')}\n"
        f"📀 <b>Sifati:</b> {movie.get('quality', '1080p Full HD')}\n"
        f"🇺🇿 <b>Tili / Ovoz:</b> {movie.get('language', 'O‘zbek tilida')}\n"
        f"⭐ <b>Reytingi:</b> {rating} / 10 ({votes} baho)\n"
        f"👁 <b>Ko'rishlar:</b> {views:,} ta • 🔢 <b>Kodi:</b> <code>{movie['code']}</code>"
        f"</blockquote>"
        f"{caption_extra}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{prot_badge}"
        f"📢 <b>Kanal:</b> @movieee_land • 🤖 @{bot_username}"
    )

async def publish_movie_to_channel(movie: dict) -> bool:
    """
    Kinoni @movieee_land (yoki belgilangan Avto-Post kanaliga) chiqarish:
    1) Agar Admin kinoga rasm (photo_id) biriktirgan bo'lsa -> aynan o'sha rasm bilan chiqaradi!
    2) Aks holda (TMDB avto-rasm o'chirilgan bo'lsa) -> xato rasm qo'shmasdan, toza post chiqaradi!
    """
    b_uname = await get_bot_username()
    raw_ch = await db.get_setting("auto_post_channel", config.DEFAULT_POST_CHANNEL_ID)
    post_ch = db.normalize_channel_target(raw_ch)
    if not post_ch:
        return False

    code = movie["code"]
    serial_txt = " (Serial)" if movie.get("is_serial") else ""
    desc_line = f"\n📝 <i>{movie['caption']}</i>\n" if movie.get("caption") else ""

    post_text = (
        f"🎬 <b>Nomi:</b> {movie['name']}{serial_txt}\n\n"
        f"🌏 <b>Davlati:</b> {movie.get('country', 'AQSH')}\n"
        f"📅 <b>Yili:</b> {movie.get('year', '2024')}\n"
        f"📀 <b>Sifati:</b> {movie.get('quality', '1080p Full HD')}\n"
        f"🎞 <b>Janri:</b> {movie.get('genre', '🔥 Jangari')}\n"
        f"🇺🇿 <b>Tili:</b> {movie.get('language', 'O‘zbek tilida')}\n"
        f"🔢 <b>Kino kodi:</b> <code>{code}</code>\n"
        f"{desc_line}\n"
        f"📌 <b>Kanal:</b> @movieee_land"
    )
    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"▶️ Kinoni tomosha qilish (Kod: {code})", url=f"https://t.me/{b_uname}?start={code}")]
    ])

    # 1. Agar kinoda rasm (photo_id) bo'lmasa, TheMovieDB (1-rasm) dan avtomatik HD poster topib bazaga saqlaymiz
    if not movie.get("photo_id"):
        poster_url = await ai_service.find_movie_poster_tmdb(
            name=movie["name"],
            year=str(movie.get("year", "")),
            is_serial=bool(movie.get("is_serial")),
            force=True
        )
        if poster_url:
            await db.update_movie_photo(code, poster_url)
            movie["photo_id"] = poster_url

    # 2. Rasmli post chiqarish (Admin rasmi yoki TMDB rasmiy HD posteri bilan)
    if movie.get("photo_id"):
        try:
            await bot.send_photo(
                chat_id=post_ch,
                photo=movie["photo_id"],
                caption=post_text,
                reply_markup=btn,
                parse_mode="HTML"
            )
            return True
        except Exception as e:
            logging.warning(f"Rasm bilan post yuborishda xato ({movie.get('photo_id')}), TMDB orqali yangilanadi: {e}")
            fresh_poster = await ai_service.find_movie_poster_tmdb(
                name=movie["name"],
                year=str(movie.get("year", "")),
                is_serial=bool(movie.get("is_serial")),
                force=True
            )
            if fresh_poster and fresh_poster != movie.get("photo_id"):
                await db.update_movie_photo(code, fresh_poster)
                try:
                    await bot.send_photo(
                        chat_id=post_ch,
                        photo=fresh_poster,
                        caption=post_text,
                        reply_markup=btn,
                        parse_mode="HTML"
                    )
                    return True
                except Exception as e2:
                    logging.warning(f"Yangilangan TMDB rasm bilan post yuborishda xato: {e2}")

    try:
        await bot.send_message(chat_id=post_ch, text=post_text, reply_markup=btn, parse_mode="HTML")
        return True
    except Exception as e:
        logging.warning(f"Avto-post yuborishda xato ({post_ch}): {e}")
        return False

async def process_archive_item(
    file_id: str,
    raw_caption: str,
    msg_id: int = None,
    do_autopost: bool = True,
    file_name: str = "",
    video_height: int = 0,
    auto_edit_archive: bool = True
) -> dict:
    """
    Arxiv kanaldan (-1003124847141) kelgan video, file_name va captionni tahlil qilib:
    - Faqat nomi yoki fayl nomi yozilgan bo'lsa ham AI + Kino Ensiklopediyasi + TMDB orqali
      to'liq ma'lumotlarini (Davlati, Yili, Sifati, Janri, Tili, Tavsifi) to'ldiradi!
    - Agar Arxiv kanaldagi post chala bo'lsa -> Arxiv kanalning o'zida ham postni to'liq shablonga tahrirlab qo'yadi!
    - Agar serial bo'lsa va bazada mavjud bo'lsa -> keyingi qism sifatida ulaydi!
    - Agar yangi serial yoki kino bo'lsa -> bazaga qo'shadi va kanalga post chiqaradi!
    """
    parsed = await ai_service.enrich_movie_metadata_with_ai(
        raw_text=raw_caption,
        file_name=file_name,
        video_height=video_height,
        msg_id=msg_id
    )
    name = parsed["name"]
    is_serial = parsed["is_serial"]
    ep_num = parsed["episode_num"]

    # Agar Arxiv kanaldagi postda ma'lumotlar to'liq yozilmagan bo'lsa, Arxiv kanalning o'zida ham postni avtomatik to'ldirib qo'yamiz!
    if msg_id and auto_edit_archive and ai_service.is_archive_caption_incomplete(raw_caption):
        try:
            arch_ch_str = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
            std_cap = ai_service.format_standard_archive_caption(parsed)
            if std_cap.strip() != (raw_caption or "").strip():
                await bot.edit_message_caption(
                    chat_id=int(arch_ch_str),
                    message_id=msg_id,
                    caption=std_cap
                )
        except Exception as e:
            logging.debug(f"Arxiv post tahrirlash ({msg_id}): {e}")

    # 1. Agar bu SERIAL bo'lsa, avval shu nomli serial bazada bormi tekshiramiz
    if is_serial:
        existing_serial = await db.find_movie_by_exact_name(name)
        if existing_serial:
            code = existing_serial["code"]
            await db.add_episode(code, ep_num, file_id, f"{ep_num}-qism")
            if msg_id:
                await db.mark_archive_msg_imported(msg_id, code)
            return {
                "status": "episode_added",
                "code": code,
                "name": name,
                "ep_num": ep_num,
                "posted": False
            }

    # 2. Aynan shu file_id yoki aynan shu nomli kino avval yuklangan bo'lsa, ma'lumotlarini yangilab dublikat qilmaymiz
    existing_file = await db.find_movie_by_file_id(file_id)
    if not existing_file and not is_serial:
        existing_file = await db.find_movie_by_exact_name(name)
    if existing_file:
        code = existing_file["code"]
        await db.update_movie_full_metadata(
            code=code,
            name=name,
            genre=parsed["genre"],
            year=parsed["year"],
            country=parsed["country"],
            quality=parsed["quality"],
            language=parsed["language"],
            caption=parsed["caption"]
        )
        if not existing_file.get("photo_id"):
            poster_url = await ai_service.find_movie_poster_tmdb(
                name=name,
                year=str(parsed.get("year", "")),
                is_serial=bool(is_serial),
                force=True
            )
            if poster_url:
                await db.update_movie_photo(code, poster_url)
        if msg_id:
            await db.mark_archive_msg_imported(msg_id, code)
        return {
            "status": "already_exists",
            "code": code,
            "name": name,
            "ep_num": ep_num,
            "posted": False
        }

    # 3. Yangi kino yoki yangi serial sifatida qo'shamiz
    code = await db.get_next_auto_code()
    final_caption = parsed["caption"]

    # TheMovieDB (1-rasm) orqali rasmiy HD posterini avtomatik olish
    poster_url = await ai_service.find_movie_poster_tmdb(
        name=name,
        year=str(parsed.get("year", "")),
        is_serial=bool(is_serial),
        force=True
    )

    await db.add_movie(
        code=code,
        name=name,
        file_id=file_id,
        genre=parsed["genre"],
        year=parsed["year"],
        country=parsed["country"],
        language=parsed["language"],
        quality=parsed["quality"],
        imdb="8.4",
        photo_id=poster_url,
        caption=final_caption,
        is_serial=is_serial,
        first_ep_num=ep_num
    )

    if msg_id:
        await db.mark_archive_msg_imported(msg_id, code)

    posted = False
    if do_autopost:
        movie_obj = await db.get_movie(code, increment_view=False)
        if movie_obj:
            posted = await publish_movie_to_channel(movie_obj)

    return {
        "status": "new_serial" if is_serial else "new_movie",
        "code": code,
        "name": name,
        "ep_num": ep_num,
        "posted": posted
    }

async def send_movie_card(target, user_id: int, code: str, ep_num: int = 1, ep_page: int = 1):
    """
    Kino yoki serial tanlanganida avval Poster Card (rasm + tavsif + inline menyu) chiqadi!
    Reski video berilmaydi — foydalanuvchi:
    - 3 tagacha qismi bo'lsa: «▶️ Kino ko'rish» tugmasini bosadi;
    - 3 tadan ko'p qismi bo'lsa (yoki serial bo'lsa): «1, 2, 3, 4, 5...» qism tugmalaridan birini bosadi!
    """
    b_uname = await get_bot_username()
    lang = await db.get_user_lang(user_id)
    movie = await db.get_movie(code, increment_view=True)
    if not movie:
        txt = t("movie_not_found_code", lang, code=code)
        if isinstance(target, CallbackQuery):
            await target.message.answer(txt, parse_mode="HTML")
        else:
            await target.answer(txt, parse_mode="HTML")
        return

    await db.add_history(user_id, movie["code"])
    is_fav = await db.is_favorite(user_id, movie["code"])
    user_rating = await db.get_user_movie_rating(user_id, movie["code"])
    user_perms = await db.get_user_permissions(user_id)
    protect_val = await db.get_setting("protect_content", "1")
    protect = (str(protect_val) == "1")

    episodes = await db.get_episodes(movie["code"])

    # Agar kinoga hali poster biriktirilmagan bo'lsa, TheMovieDB dan avto-olamiz!
    if not movie.get("photo_id"):
        poster_url = await ai_service.find_movie_poster_tmdb(
            name=movie["name"],
            year=str(movie.get("year", "")),
            is_serial=bool(movie.get("is_serial")),
            force=True
        )
        if poster_url:
            await db.update_movie_photo(movie["code"], poster_url)
            movie["photo_id"] = poster_url

    caption = format_movie_caption(movie, b_uname, current_ep=None, protect=protect, lang=lang)
    markup = kb.movie_poster_card_keyboard(
        movie=movie,
        bot_username=b_uname,
        is_fav=is_fav,
        episodes=episodes,
        user_perms=user_perms,
        lang=lang,
        user_rating=user_rating,
        ep_page=ep_page
    )

    if movie.get("photo_id"):
        try:
            await bot.send_photo(
                chat_id=user_id,
                photo=movie["photo_id"],
                caption=caption,
                reply_markup=markup,
                protect_content=protect,
                parse_mode="HTML"
            )
            return
        except Exception as e:
            logging.warning(f"Poster card rasm yuborishda xato ({movie.get('photo_id')}): {e}")

    await bot.send_message(
        chat_id=user_id,
        text=caption,
        reply_markup=markup,
        protect_content=protect,
        parse_mode="HTML"
    )


async def send_movie_video(target, user_id: int, code: str, ep_num: int = 1):
    """
    Foydalanuvchi Poster Card ostidagi «▶️ Kino ko'rish» yoki «1, 2, 3...» qism tugmasini
    bosganida haqiqiy kino/qism videosini yuboradi!
    """
    b_uname = await get_bot_username()
    lang = await db.get_user_lang(user_id)
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        txt = t("movie_not_found_code", lang, code=code)
        if isinstance(target, CallbackQuery):
            await target.message.answer(txt, parse_mode="HTML")
        else:
            await target.answer(txt, parse_mode="HTML")
        return

    is_fav = await db.is_favorite(user_id, movie["code"])
    user_rating = await db.get_user_movie_rating(user_id, movie["code"])
    user_perms = await db.get_user_permissions(user_id)
    protect_val = await db.get_setting("protect_content", "1")
    protect = (str(protect_val) == "1")

    episodes = await db.get_episodes(movie["code"])
    file_to_send = movie["file_id"]
    current_ep = None

    if episodes:
        ep_obj = next((e for e in episodes if e["episode_num"] == ep_num), episodes[0])
        file_to_send = ep_obj["file_id"]
        current_ep = ep_obj["episode_num"]

    caption = format_movie_caption(movie, b_uname, current_ep=current_ep, protect=protect, lang=lang)
    markup = kb.movie_action_keyboard(
        movie=movie,
        bot_username=b_uname,
        is_fav=is_fav,
        episodes=episodes,
        current_ep=current_ep or 1,
        user_perms=user_perms,
        lang=lang,
        user_rating=user_rating
    )

    try:
        await bot.send_video(
            chat_id=user_id,
            video=file_to_send,
            caption=caption,
            reply_markup=markup,
            protect_content=protect,
            parse_mode="HTML"
        )
    except Exception:
        await bot.send_document(
            chat_id=user_id,
            document=file_to_send,
            caption=caption,
            reply_markup=markup,
            protect_content=protect,
            parse_mode="HTML"
        )


# ===================== ARXIV KANAL AVTO-QABUL (@dp.channel_post) =====================
@dp.channel_post(F.video | F.document)
async def handle_archive_channel_new_post(message: Message):
    """
    Movie Land ARXIV (-1003124847141) kanaliga yangi kino tashlanishi bilan
    bot uni avtomatik o'z bazasiga qo'shib oladi va asosiy kanalga post chiqaradi!
    """
    arch_id = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    if str(message.chat.id) != str(arch_id):
        return

    auto_grab = await db.get_setting("auto_grab_archive", "1")
    if auto_grab != "1":
        return

    v_obj = message.video or message.document
    file_id = v_obj.file_id
    file_name = getattr(v_obj, "file_name", "") or ""
    video_height = getattr(v_obj, "height", 0) or 0
    raw_caption = message.caption or ""
    auto_post = (await db.get_setting("archive_auto_post", "1")) == "1"

    res = await process_archive_item(
        file_id=file_id,
        raw_caption=raw_caption,
        msg_id=message.message_id,
        do_autopost=auto_post,
        file_name=file_name,
        video_height=video_height,
        auto_edit_archive=True
    )
    logging.info(f"Arxiv kanaldan avto-qabul qilindi: {res}")


# ===================== SUPER ADMIN, ADMIN & MODERATOR: BAZADAN (ARXIVDAN) KINO VA SERIAL YUKLASH =====================
async def _can_load_archive(user_id: int) -> bool:
    return (
        await db.has_permission(user_id, "archive_load")
        or await db.has_permission(user_id, "add_movie")
    )

async def _resolve_catalog_file_id(item: dict, arch_ch: int, probe_chat_id: int) -> str:
    """
    Agar archive_catalog da file_id allaqachon bor bo'lsa darhol qaytaradi.
    Agar bo'sh bo'lsa, Arxiv kanaldan admin lichkasiga (probe_chat_id) forward qilib
    file_id ni oladi, vaqtinchalik xabarni darhol o'chiradi va bazaga keshlaydi!
    """
    fid = (item.get("file_id") or "").strip()
    if fid:
        return fid
    mid = int(item["msg_id"])
    for target_cid in (probe_chat_id, arch_ch):
        try:
            fwd = await bot.forward_message(
                chat_id=target_cid,
                from_chat_id=arch_ch,
                message_id=mid,
                disable_notification=True
            )
            try:
                await bot.delete_message(chat_id=target_cid, message_id=fwd.message_id)
            except Exception:
                pass
            v_obj = fwd.video or fwd.document
            if v_obj and v_obj.file_id:
                await db.update_archive_catalog_file_id(mid, v_obj.file_id)
                return v_obj.file_id
        except Exception as e:
            logging.debug(f"file_id olish ({mid} -> {target_cid}): {e}")
            await asyncio.sleep(0.3)
    return ""


_YEAR_RE = re.compile(r"^(19\d{2}|20\d{2})$")

def _genre_is_valid(g: str) -> bool:
    letters = re.sub(r"[^A-Za-zА-Яа-яЁёʻ'‘`ʼ]", "", g or "")
    return len(letters) >= 5

async def _archive_clean_meta(first_it: dict, title: str, is_serial: bool) -> dict:
    """
    Arxiv katalogidagi yil / davlat / janr noto'g'ri yoki bo'sh bo'lsa (masalan janr 'D', 'Dah'),
    TMDB orqali aniq ma'lumotni oladi. Hech narsa topilmasa xavfsiz standart qiymat qo'yadi.
    """
    year = str(first_it.get("year") or "").strip()
    country = (first_it.get("country") or "").strip()
    genre = (first_it.get("genre") or "").strip()
    quality = (first_it.get("quality") or "").strip() or "1080p Full HD"

    if not _YEAR_RE.match(year) or not country or not _genre_is_valid(genre):
        try:
            tm = await asyncio.wait_for(
                ai_service._lookup_tmdb_metadata(title, year if _YEAR_RE.match(year) else "", is_serial=is_serial),
                timeout=25
            )
        except Exception:
            tm = {}
        tm = tm or {}
        if not _YEAR_RE.match(year) and tm.get("year"):
            year = tm["year"]
        if not country and tm.get("country"):
            country = tm["country"]
        if not _genre_is_valid(genre) and tm.get("genre"):
            genre = tm["genre"]

    if not _YEAR_RE.match(year):
        year = "2024"
    if not country:
        country = "AQSH"
    if not _genre_is_valid(genre):
        genre = "🚀 Fantastika" if is_serial else "🔥 Jangari"
    return {"year": year, "country": country, "genre": genre, "quality": quality}

async def _safe_desc(name: str, genre: str, year: str, country: str, is_serial: bool) -> str:
    try:
        return await asyncio.wait_for(
            ai_service.process_movie_description_with_ai(
                name=name, genre=genre, year=str(year), existing_caption="",
                country=country, is_serial=bool(is_serial)
            ),
            timeout=40
        ) or ""
    except Exception as e:
        logging.warning(f"Tavsif yaratish xatosi ({name}): {e}")
        try:
            return ai_service.generate_smart_uzbek_description(name, genre, str(year), country, is_serial=bool(is_serial))
        except Exception:
            return ""

async def _safe_poster(name: str, year: str, is_serial: bool) -> str:
    try:
        return await asyncio.wait_for(
            ai_service.find_movie_poster_tmdb(name=name, year=str(year), is_serial=bool(is_serial), force=True),
            timeout=40
        ) or None
    except Exception as e:
        logging.warning(f"TMDB poster xatosi ({name}): {e}")
        return None


@dp.message(F.text == "📥 Bazadan Kino yuklash")
async def cmd_load_movies_from_archive(message: Message, state: FSMContext):
    if not await _can_load_archive(message.from_user.id):
        await message.answer("⛔ Sizda Bazadan Kino yuklash huquqi yo'q!")
        return
    st = await db.get_archive_catalog_stats()
    next_code = await db.get_next_auto_code()
    await state.set_state(ArchivePullState.waiting_movies_count)
    await message.answer(
        f"📥 <b>BAZADAN (ARXIVDAN) KINO YUKLASH</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>Arxivdagi jami kinolar (guruhlangan):</b> {st['total_movie_groups']} ta ({st['total_movie_files']} qism)\n"
        f"⏳ <b>Yuklanmagan kinolar:</b> <b>{st['rem_movie_groups']} ta</b>\n"
        f"🔢 <b>Navbatdagi kino kodi:</b> <code>#{next_code}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ <b>Aqlli tizim qoidalari:</b>\n"
        f"• Eng boshidan tartib bilan yuklaydi va <b>seriallarni avtomatik skip qiladi</b>;\n"
        f"• Ko'p qismli kinolarni (hatto 3-qism 2-qismdan oldin tursa ham) <b>1, 2, 3...</b> qilib bitta kod ostiga jamlaydi;\n"
        f"• TheMovieDB dan rasmiy HD posterini olib, <b>@movieee_land</b> kanaliga kodi va tavsifi bilan chiqaradi!\n\n"
        f"👇 <b>Nechta kino yuklamoqchisiz? Sonini kiriting (masalan: <code>10</code>):</b>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "arch_load_movies")
async def cb_load_movies_from_archive(call: CallbackQuery, state: FSMContext):
    if not await _can_load_archive(call.from_user.id):
        await call.answer("⛔ Sizda bu funksiya uchun ruxsat yo'q!", show_alert=True)
        return
    st = await db.get_archive_catalog_stats()
    await state.set_state(ArchivePullState.waiting_movies_count)
    await call.message.answer(
        f"📥 <b>Arxiv bazadan nechta KINO yuklamoqchisiz?</b> (Qolgan kinolar: <b>{st['rem_movie_groups']} ta</b>)\n"
        f"Sonini yozib yuboring (masalan: <code>10</code>):",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.message(ArchivePullState.waiting_movies_count)
async def process_load_movies_count(message: Message, state: FSMContext):
    await state.clear()
    role = await db.get_user_role(message.from_user.id)
    perms = await db.get_user_permissions(message.from_user.id)
    panel_kb = kb.super_admin_keyboard() if role == "superadmin" else kb.staff_panel_keyboard(perms)
    if not (message.text or "").strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting (masalan: <code>10</code>)!", reply_markup=panel_kb, parse_mode="HTML")
        return
    target_count = max(1, min(int(message.text.strip()), 100))
    await execute_archive_grouped_movies_load(message, target_count, probe_chat_id=message.from_user.id)


async def execute_archive_grouped_movies_load(message: Message, target_count: int, probe_chat_id: int):
    """
    Bazadan (Arxivdan) N ta kinoni eng boshidan guruhlab yuklaydi:
    - Seriallarni (Merlin, Envel va b.) skip qiladi!
    - Ko'p qismli kinolarni 1, 2, 3... tartibda bitta kino kodiga jamlaydi!
    - Har bir kinoga TMDB poster oladi va @movieee_land kanaliga chiroyli post yuboradi!
    """
    arch_ch = int(await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID))
    groups = await db.get_unimported_archive_movies_grouped(limit_groups=target_count)
    if not groups:
        await message.answer(
            "ℹ️ <b>Arxivdagi barcha kinolar allaqachon yuklab bo'lingan!</b>\n"
            "<i>(Agar boshidan yuklamoqchi bo'lsangiz, kinolar bazasini tozalang).</i>",
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer(
        f"⏳ <b>Bazadan {len(groups)} ta kino yuklanmoqda...</b>\n"
        f"<i>(Qismlar 1, 2, 3 tartibda birlashtirilmoqda, TMDB poster olinmoqda va @movieee_land ga post chiqarilmoqda)</i>",
        parse_mode="HTML"
    )

    loaded_movies = 0
    total_parts_linked = 0
    posted_cnt = 0
    summary_lines = []
    failed_lines = []

    for idx, grp in enumerate(groups, 1):
        items = grp["items"]
        first_it = items[0]
        movie_title = grp["base_title"] if len(items) > 1 else (first_it.get("parsed_name") or grp["base_title"])
        try:
            await status_msg.edit_text(
                f"📥 <b>Bazadan kinolar yuklanmoqda: {idx} / {len(groups)}</b>\n"
                f"🎬 Hozir: <b>{movie_title}</b>\n"
                f"✅ Yuklandi: <b>{loaded_movies} ta</b> | 📢 Kanalga post: <b>{posted_cnt} ta</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

        # Har bir qismning file_id sini olamiz (1, 2, 3... tartibda)
        resolved_parts = []
        for ep_idx, it in enumerate(items, 1):
            fid = await _resolve_catalog_file_id(it, arch_ch, probe_chat_id)
            if fid:
                resolved_parts.append({
                    "ep_num": ep_idx,
                    "file_id": fid,
                    "title": it.get("parsed_name") or f"{ep_idx}-qism",
                    "msg_id": it["msg_id"]
                })

        if not resolved_parts:
            failed_lines.append(f"⚠️ {movie_title} — video file_id olinmadi")
            continue

        try:
            code = await db.get_next_auto_code()
            meta = await _archive_clean_meta(first_it, movie_title, is_serial=False)
            year, country, genre, quality = meta["year"], meta["country"], meta["genre"], meta["quality"]

            desc = await _safe_desc(movie_title, genre, year, country, is_serial=False)
            poster_url = await _safe_poster(movie_title, year, is_serial=False)
        except Exception as e:
            logging.exception(f"Bazadan kino yuklash (tayyorlash) xatosi: {movie_title}")
            failed_lines.append(f"⚠️ {movie_title} — {str(e)[:60]}")
            continue

        try:
            await db.add_movie(
                code=code,
                name=movie_title,
                file_id=resolved_parts[0]["file_id"],
                genre=genre,
                year=year,
                country=country,
                language="O'zbek tilida",
                quality=quality,
                imdb="8.4",
                photo_id=poster_url,
                caption=desc,
                is_serial=0,
                first_ep_num=1
            )

            # Agar kinoning 2 va undan ortiq qismi bo'lsa, barcha qismlarni 1, 2, 3... qilib episodes jadvaliga yozamiz
            if len(resolved_parts) > 1:
                for rp in resolved_parts:
                    await db.add_episode(code, rp["ep_num"], rp["file_id"], f"{rp['ep_num']}-qism")
                # is_serial ustunini 0 qilib qoldiramiz (chunki bu ko'p qismli kino, serial emas!)
                conn_db = await db.get_db_conn()
                try:
                    await conn_db.execute("UPDATE movies SET is_serial = 0 WHERE code = ?", (str(code),))
                    await conn_db.commit()
                finally:
                    await conn_db.close()
                total_parts_linked += len(resolved_parts)

            await db.mark_archive_catalog_imported(grp["all_msg_ids"], code)
            loaded_movies += 1
        except Exception as e:
            logging.exception(f"Bazadan kino yuklash (bazaga yozish) xatosi: {movie_title}")
            failed_lines.append(f"⚠️ {movie_title} — {str(e)[:60]}")
            continue

        movie_obj = await db.get_movie(code, increment_view=False)
        if movie_obj:
            try:
                ok_post = await publish_movie_to_channel(movie_obj)
            except Exception as e:
                logging.warning(f"Kanalga post xatosi (#{code}): {e}")
                ok_post = False
            if ok_post:
                posted_cnt += 1

        parts_badge = f" ({len(resolved_parts)} qism: 1..{len(resolved_parts)})" if len(resolved_parts) > 1 else ""
        summary_lines.append(f"🎬 <b>#{code}</b> — {movie_title} ({year}){parts_badge}")
        await asyncio.sleep(0.5)

    role = await db.get_user_role(probe_chat_id)
    perms = await db.get_user_permissions(probe_chat_id)
    panel_kb = kb.super_admin_keyboard() if role == "superadmin" else kb.staff_panel_keyboard(perms)

    lines_txt = "\n".join(summary_lines[:30]) or "—"
    fail_txt = ("\n\n❗ <b>Yuklanmaganlar:</b>\n" + "\n".join(failed_lines[:15])) if failed_lines else ""
    await status_msg.edit_text(
        f"✅ <b>BAZADAN KINO YUKLASH YAKUNLANDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>Yuklangan kinolar:</b> {loaded_movies} ta\n"
        f"🎞 <b>Birlashtirilgan kino qismlari:</b> {total_parts_linked} ta\n"
        f"📢 <b>Kanalga yuborilgan postlar:</b> {posted_cnt} ta\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Ro'yxat:</b>\n{lines_txt}{fail_txt}",
        parse_mode="HTML"
    )
    await message.answer("✅ Boshqaruv paneli:", reply_markup=panel_kb)


@dp.message(F.text == "📺 Bazadan Serial yuklash")
async def cmd_load_serials_from_archive(message: Message, state: FSMContext):
    if not await _can_load_archive(message.from_user.id):
        await message.answer("⛔ Sizda Bazadan Serial yuklash huquqi yo'q!")
        return
    st = await db.get_archive_catalog_stats()
    next_code = await db.get_next_auto_code()
    await state.set_state(ArchivePullState.waiting_serials_count)
    await message.answer(
        f"📺 <b>BAZADAN (ARXIVDAN) SERIAL YUKLASH</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎞 <b>Arxivdagi jami seriallar:</b> {st['total_serial_groups']} ta (Jami {st['total_serial_eps']} qism)\n"
        f"⏳ <b>Yuklanmagan seriallar:</b> <b>{st['rem_serial_groups']} ta</b>\n"
        f"🔢 <b>Navbatdagi kod:</b> <code>#{next_code}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ <b>Aqlli Serial Analizatori:</b>\n"
        f"• Arxivdagi barcha qismlarni (masalan: <b>Afsungar Merlin</b> 1..65-qism yoki <b>Envel Qahramonlari</b> 1..52-qism) bitta kod ostiga <b>1, 2, 3, 4, 5...</b> qilib jamlaydi;\n"
        f"• TheMovieDB dan rasmiy HD posterini olib, <b>@movieee_land</b> kanaliga post chiqaradi!\n\n"
        f"👇 <b>Nechta serial yuklamoqchisiz? Sonini kiriting (masalan: <code>1</code> yoki <code>2</code>):</b>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "arch_load_serials")
async def cb_load_serials_from_archive(call: CallbackQuery, state: FSMContext):
    if not await _can_load_archive(call.from_user.id):
        await call.answer("⛔ Sizda bu funksiya uchun ruxsat yo'q!", show_alert=True)
        return
    st = await db.get_archive_catalog_stats()
    await state.set_state(ArchivePullState.waiting_serials_count)
    await call.message.answer(
        f"📺 <b>Arxiv bazadan nechta SERIAL yuklamoqchisiz?</b> (Qolgan seriallar: <b>{st['rem_serial_groups']} ta</b>)\n"
        f"Sonini yozib yuboring (masalan: <code>1</code>):",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.message(ArchivePullState.waiting_serials_count)
async def process_load_serials_count(message: Message, state: FSMContext):
    await state.clear()
    role = await db.get_user_role(message.from_user.id)
    perms = await db.get_user_permissions(message.from_user.id)
    panel_kb = kb.super_admin_keyboard() if role == "superadmin" else kb.staff_panel_keyboard(perms)
    if not (message.text or "").strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting (masalan: <code>1</code>)!", reply_markup=panel_kb, parse_mode="HTML")
        return
    target_count = max(1, min(int(message.text.strip()), 20))
    await execute_archive_grouped_serials_load(message, target_count, probe_chat_id=message.from_user.id)


async def execute_archive_grouped_serials_load(message: Message, target_count: int, probe_chat_id: int):
    arch_ch = int(await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID))
    groups = await db.get_unimported_archive_serials_grouped(limit_groups=target_count)
    if not groups:
        await message.answer("ℹ️ <b>Arxivdagi barcha seriallar allaqachon yuklab bo'lingan!</b>", parse_mode="HTML")
        return

    status_msg = await message.answer(
        f"⏳ <b>Bazadan {len(groups)} ta serial va uning barcha qismlari tahlil qilinib yuklanmoqda...</b>",
        parse_mode="HTML"
    )

    loaded_serials = 0
    total_eps = 0
    posted_cnt = 0
    summary_lines = []

    for grp in groups:
        items = grp["items"]
        first_it = items[0]
        serial_title = grp["base_title"]

        resolved_eps = []
        for idx_ep, it in enumerate(items, 1):
            fid = await _resolve_catalog_file_id(it, arch_ch, probe_chat_id)
            if fid:
                ep_n = it.get("part_num") or idx_ep
                resolved_eps.append({
                    "ep_num": ep_n,
                    "file_id": fid,
                    "msg_id": it["msg_id"]
                })
            if idx_ep % 10 == 0:
                try:
                    await status_msg.edit_text(
                        f"📺 <b>«{serial_title}» seriali qismlari yig'ilmoqda: {idx_ep} / {len(items)} qism...</b>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

        if not resolved_eps:
            continue

        code = await db.get_next_auto_code()
        meta = await _archive_clean_meta(first_it, serial_title, is_serial=True)
        year, country, genre, quality = meta["year"], meta["country"], meta["genre"], meta["quality"]

        desc = await _safe_desc(serial_title, genre, year, country, is_serial=True)
        poster_url = await _safe_poster(serial_title, year, is_serial=True)

        await db.add_movie(
            code=code,
            name=serial_title,
            file_id=resolved_eps[0]["file_id"],
            genre=genre,
            year=year,
            country=country,
            language="O'zbek tilida",
            quality=quality,
            imdb="8.6",
            photo_id=poster_url,
            caption=desc,
            is_serial=1,
            first_ep_num=resolved_eps[0]["ep_num"]
        )

        for ep in resolved_eps:
            await db.add_episode(code, ep["ep_num"], ep["file_id"], f"{ep['ep_num']}-qism")

        await db.mark_archive_catalog_imported(grp["all_msg_ids"], code)
        loaded_serials += 1
        total_eps += len(resolved_eps)

        movie_obj = await db.get_movie(code, increment_view=False)
        if movie_obj:
            try:
                ok_post = await publish_movie_to_channel(movie_obj)
            except Exception as e:
                logging.warning(f"Kanalga serial post xatosi (#{code}): {e}")
                ok_post = False
            if ok_post:
                posted_cnt += 1

        summary_lines.append(f"📺 <b>#{code}</b> — {serial_title} ({len(resolved_eps)} qism jamlandi)")

    role = await db.get_user_role(probe_chat_id)
    perms = await db.get_user_permissions(probe_chat_id)
    panel_kb = kb.super_admin_keyboard() if role == "superadmin" else kb.staff_panel_keyboard(perms)

    await status_msg.edit_text(
        f"✅ <b>BAZADAN SERIAL YUKLASH YAKUNLANDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📺 <b>Yuklangan seriallar:</b> {loaded_serials} ta\n"
        f"🎞 <b>Birlashtirilgan jami qismlar:</b> {total_eps} ta\n"
        f"📢 <b>@movieee_land kanaliga yuborilgan postlar:</b> {posted_cnt} ta\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Ro'yxat:</b>\n" + "\n".join(summary_lines),
        parse_mode="HTML"
    )
    await message.answer("✅ Boshqaruv paneli:", reply_markup=panel_kb)


# ===================== SUPER ADMIN EKSKLYUZIV: KO'RISH QO'SHISH VA KINOLAR BAZASINI TOZALASH =====================
@dp.message(F.text == "👁 Kinolarga Ko'rish qo'shish")
async def sadmin_boost_views_start(message: Message, state: FSMContext):
    if await db.get_user_role(message.from_user.id) != "superadmin":
        await message.answer("⛔ Bu funksiya faqat Super Administrator uchun!")
        return
    await state.set_state(SuperViewsBoostState.waiting_spec)
    await message.answer(
        "👁 <b>KINOLARGA KO'RISHLAR SONINI QO'SHISH (SUPER ADMIN)</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Qaysi kinolarga nechta ko'rish (👁) qo'shmoqchi ekanligingizni quyidagi formatlardan birida yuboring:\n\n"
        "1️⃣ <b>Barcha kinolarga:</b> <code>all | 500</code>\n"
        "2️⃣ <b>Kod oralig'iga (masalan 1 dan 10 gacha):</b> <code>1-10 | 350</code>\n"
        "3️⃣ <b>Aniq bitta kinoga:</b> <code>1 | 1000</code>\n"
        "4️⃣ <b>Bir nechta tanlangan kinoga:</b> <code>1,3,5 | 400</code>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(SuperViewsBoostState.waiting_spec)
async def sadmin_boost_views_process(message: Message, state: FSMContext):
    await state.clear()
    raw = (message.text or "").strip()
    if "|" not in raw:
        await message.answer(
            "❌ Format xato! Misol: <code>1-10 | 500</code> yoki <code>all | 500</code>",
            reply_markup=kb.super_admin_keyboard(),
            parse_mode="HTML"
        )
        return
    spec_part, views_part = [p.strip() for p in raw.split("|", 1)]
    if not views_part.isdigit() or int(views_part) <= 0:
        await message.answer("❌ Ko'rishlar soni musbat raqam bo'lishi shart!", reply_markup=kb.super_admin_keyboard())
        return
    add_v = int(views_part)
    updated_cnt = await db.boost_movies_views(spec_part, add_v)
    await message.answer(
        f"✅ <b>Ko'rishlar soni muvaffaqiyatli qo'shildi!</b>\n"
        f"🎯 Tanlangan kinolar: <code>{spec_part}</code> (<b>{updated_cnt} ta</b> kino)\n"
        f"👁 Qo'shilgan ko'rishlar: <b>+{add_v:,} marta</b>",
        reply_markup=kb.super_admin_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "🗑 Faqat kinolar bazasini tozalash")
async def sadmin_clear_movies_prompt(message: Message):
    if await db.get_user_role(message.from_user.id) != "superadmin":
        await message.answer("⛔ Faqat Super Administrator uchun!")
        return
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, faqat kinolar bazasini top-toza qil (Kod #1 dan)", callback_data="sadm_confirm_clear_movies")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sadm_cancel_clear_movies")]
    ])
    await message.answer(
        "⚠️ <b>DIQQAT: FAQAT KINOLAR BAZASINI TOZALASH</b>\n\n"
        "Ushbu amal bajarilganda:\n"
        "• Barcha kinolar, serial qismlari, sevimlilar va reytinglar top-toza qilinadi;\n"
        "• Kino kodi qaytadan <b>#1</b> dan boshlanadi;\n"
        "• Foydalanuvchilar, balanslar, VIP obunalar va kanallar <b>100% saqlanib qoladi!</b>\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=confirm_kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "sadm_confirm_clear_movies")
async def cb_sadmin_confirm_clear_movies(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    res = await db.clear_all_movies_only()
    await call.message.edit_text(
        f"✅ <b>Kinolar bazasi butkul top-toza qilindi!</b>\n"
        f"🗑 O'chirilgan kinolar: <b>{res['deleted_movies']} ta</b>\n"
        f"🔢 Keyingi kino kodi: <b>#1</b> dan boshlanadi!",
        parse_mode="HTML"
    )
    await call.answer("✅ Kinolar bazasi tozalandi!")

@dp.callback_query(F.data == "sadm_cancel_clear_movies")
async def cb_sadmin_cancel_clear_movies(call: CallbackQuery):
    await call.message.delete()
    await call.answer("Bekor qilindi")


# ===================== SUPER ADMIN & ADMIN: ARXIV KANALDAN N TA KINONI AVTO-YUKLASH =====================
@dp.message(F.text.in_({"🗂 Arxiv sozlamalari", "📥 Arxiv Kanaldan Yuklash"}))
async def archive_center_menu(message: Message):
    if not await _can_load_archive(message.from_user.id):
        await message.answer("⛔ Sizda bu bo'limga ruxsat yo'q!")
        return

    auto_grab = await db.get_setting("auto_grab_archive", "1")
    auto_post = await db.get_setting("archive_auto_post", "1")
    arch_ch = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    post_ch = await db.get_setting("auto_post_channel", config.DEFAULT_POST_CHANNEL_ID)
    st = await db.get_archive_catalog_stats()

    await message.answer(
        f"🗂 <b>ARXIV SOZLAMALARI</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🗄 <b>Arxiv kanal:</b> <code>{arch_ch}</code>\n"
        f"📢 <b>Post kanali:</b> <code>{post_ch}</code>\n"
        f"🎬 <b>Kinolar:</b> {st['total_movie_groups']} ta (qolgan: <b>{st['rem_movie_groups']}</b>)\n"
        f"📺 <b>Seriallar:</b> {st['total_serial_groups']} ta (qolgan: <b>{st['rem_serial_groups']}</b>)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 Yuklash uchun paneldagi <b>«📥 Bazadan Kino yuklash»</b> yoki <b>«📺 Bazadan Serial yuklash»</b> tugmasini bosing.",
        reply_markup=kb.archive_center_inline(auto_grab, auto_post, arch_ch, post_ch),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "arch_toggle_grab")
async def cb_arch_toggle_grab(call: CallbackQuery):
    if not await db.has_permission(call.from_user.id, "add_movie"):
        return
    cur = await db.get_setting("auto_grab_archive", "1")
    nxt = "0" if cur == "1" else "1"
    await db.set_setting("auto_grab_archive", nxt)
    auto_post = await db.get_setting("archive_auto_post", "1")
    arch_ch = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    post_ch = await db.get_setting("auto_post_channel", config.DEFAULT_POST_CHANNEL_ID)
    await call.message.edit_reply_markup(reply_markup=kb.archive_center_inline(nxt, auto_post, arch_ch, post_ch))
    await call.answer("🤖 Yangi kinolarni avto-olish yangilandi!")

@dp.callback_query(F.data == "arch_toggle_post")
async def cb_arch_toggle_post(call: CallbackQuery):
    if not await db.has_permission(call.from_user.id, "add_movie"):
        return
    cur = await db.get_setting("archive_auto_post", "1")
    nxt = "0" if cur == "1" else "1"
    await db.set_setting("archive_auto_post", nxt)
    auto_grab = await db.get_setting("auto_grab_archive", "1")
    arch_ch = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    post_ch = await db.get_setting("auto_post_channel", config.DEFAULT_POST_CHANNEL_ID)
    await call.message.edit_reply_markup(reply_markup=kb.archive_center_inline(auto_grab, nxt, arch_ch, post_ch))
    await call.answer("📢 Kanalga avto-post rejimi yangilandi!")

@dp.callback_query(F.data == "arch_reset_history")
async def cb_arch_reset_history(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        await call.answer("Faqat Super-Admin tozalay oladi!", show_alert=True)
        return
    await db.clear_archive_imported_history()
    await call.answer("🔄 Arxiv skaner tarixi tozalandi! Endi barcha postlarni boshidan tekshiradi.", show_alert=True)

@dp.callback_query(F.data == "arch_pull_custom")
async def cb_arch_pull_custom(call: CallbackQuery, state: FSMContext):
    if not await db.has_permission(call.from_user.id, "add_movie"):
        return
    await state.set_state(ArchivePullState.waiting_count)
    await call.message.answer(
        "🔢 <b>Arxiv kanaldan nechta kinoni yuklab olmoqchisiz?</b>\n"
        "Sonini yozib yuboring (masalan: <code>30</code>):",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.message(ArchivePullState.waiting_count)
async def arch_pull_custom_process(message: Message, state: FSMContext):
    await state.clear()
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting (masalan: 30)!", reply_markup=kb.super_admin_keyboard())
        return
    target_count = min(int(message.text.strip()), 200)
    await execute_archive_batch_pull(message, target_count)

@dp.callback_query(F.data.startswith("arch_pull:"))
async def cb_arch_pull_preset(call: CallbackQuery):
    if not await db.has_permission(call.from_user.id, "add_movie"):
        return
    target_count = int(call.data.split(":")[1])
    await call.answer(f"📥 Arxivdan {target_count} ta kino qidirilmoqda...")
    await execute_archive_batch_pull(call.message, target_count)

async def execute_archive_batch_pull(message: Message, target_count: int):
    """
    Arxiv kanaldan (-1003124847141) target_count ta kinoni avtomatik skanerlab,
    serial qismlarini birlashtirib, AI tavsifi bilan bazaga yuklaydi va kanalga post chiqaradi!
    """
    arch_ch_str = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    arch_ch = int(arch_ch_str)
    auto_post = (await db.get_setting("archive_auto_post", "1")) == "1"

    status_msg = await message.answer(
        f"🔄 <b>Arxiv kanal ({arch_ch}) skanerlanmoqda...</b>\n"
        f"🎯 Maqsad: <b>{target_count} ta</b> kino/qism yuklash.",
        parse_mode="HTML"
    )

    # 1. Kanaldagi eng oxirgi message_id ni aniqlaymiz
    try:
        probe = await bot.send_message(chat_id=arch_ch, text="🔄", disable_notification=True)
        max_msg_id = probe.message_id - 1
        await bot.delete_message(chat_id=arch_ch, message_id=probe.message_id)
    except Exception as e:
        await status_msg.edit_text(f"❌ Arxiv kanalga ulanishda xatolik: {e}\nBot kanalda Admin ekanligini tekshiring!")
        return

    collected_items = []
    checked_empty = 0

    # Oxirgi postdan pastga qarab hali yuklanmagan target_count ta videoni topamiz
    for mid in range(max_msg_id, 0, -1):
        if len(collected_items) >= target_count:
            break
        if checked_empty > 450:
            break
        if await db.is_archive_msg_imported(mid):
            continue

        try:
            fwd = await bot.forward_message(
                chat_id=arch_ch,
                from_chat_id=arch_ch,
                message_id=mid,
                disable_notification=True
            )
            try:
                await bot.delete_message(chat_id=arch_ch, message_id=fwd.message_id)
            except Exception:
                pass

            v_obj = fwd.video or fwd.document
            file_id = v_obj.file_id if v_obj else None

            if file_id:
                collected_items.append({
                    "msg_id": mid,
                    "file_id": file_id,
                    "file_name": getattr(v_obj, "file_name", "") or "",
                    "video_height": getattr(v_obj, "height", 0) or 0,
                    "caption": fwd.caption or ""
                })
                checked_empty = 0
            else:
                await db.mark_archive_msg_imported(mid, "non_video")
        except Exception:
            checked_empty += 1

        await asyncio.sleep(0.08)

    if not collected_items:
        await status_msg.edit_text(
            "ℹ️ <b>Arxiv kanalda yuklanmagan yangi kinolar topilmadi!</b>\n"
            "<i>(Agar barcha kinolarni boshidan qayta yuklamoqchi bo'lsangiz, «🔄 Arxiv skaner tarixini tozalash» tugmasini bosing).</i>",
            parse_mode="HTML"
        )
        return

    # MUHIM: Serialning 1-qismi 2-qismidan oldin yuklanishi uchun kichik msg_id dan katta msg_id ga qarab tartiblaymiz
    collected_items.reverse()

    new_movies = 0
    new_serials = 0
    added_episodes = 0
    posted_cnt = 0
    codes_summary = []

    for idx, item in enumerate(collected_items, 1):
        res = await process_archive_item(
            file_id=item["file_id"],
            raw_caption=item["caption"],
            msg_id=item["msg_id"],
            do_autopost=auto_post,
            file_name=item.get("file_name", ""),
            video_height=item.get("video_height", 0),
            auto_edit_archive=True
        )
        st = res["status"]
        if st == "new_movie":
            new_movies += 1
            codes_summary.append(f"🎬 <b>#{res['code']}</b> — {res['name']}")
        elif st == "new_serial":
            new_serials += 1
            codes_summary.append(f"🎞 <b>#{res['code']}</b> — {res['name']} ({res['ep_num']}-qism)")
        elif st == "episode_added":
            added_episodes += 1
            codes_summary.append(f"➕ <b>#{res['code']}</b> — {res['name']} ({res['ep_num']}-qism ulandi)")

        if res.get("posted"):
            posted_cnt += 1

        if idx % 5 == 0 or idx == len(collected_items):
            try:
                await status_msg.edit_text(
                    f"📥 <b>Arxivdan kinolar yuklanmoqda: {idx} / {len(collected_items)}</b>\n"
                    f"🎬 Yangi kinolar: {new_movies} | 🎞 Seriallar: {new_serials} | ➕ Qismlar: {added_episodes}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await asyncio.sleep(0.15)

    summary_lines = "\n".join(codes_summary[:25])
    if len(codes_summary) > 25:
        summary_lines += f"\n... va yana {len(codes_summary) - 25} ta kino!"

    await status_msg.edit_text(
        f"✅ <b>ARXIVDAN YUKLASH MUVAFFAQIYATLI YAKUNLANDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>Yangi kinolar:</b> {new_movies} ta\n"
        f"🎞 <b>Yangi seriallar:</b> {new_serials} ta\n"
        f"➕ <b>Birlashtirilgan serial qismlari:</b> {added_episodes} ta\n"
        f"📢 <b>Kanalga (@movieee_land) chiqarilgan postlar:</b> {posted_cnt} ta\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Yuklangan kinolar ro'yxati:</b>\n{summary_lines or 'Barchasi avval yuklangan'}",
        parse_mode="HTML"
    )


# ===================== /CHATID BUYRUG'I (FAQAT SUPER ADMIN VA RUXSAT ETILGAN ADMINLAR UCHUN) =====================
@dp.message(Command("chatid", "id"))
async def cmd_chatid_message(message: Message):
    chat = message.chat
    user = message.from_user
    if not user:
        return

    has_perm = await db.has_permission(user.id, "chatid")
    if not has_perm:
        # Guruhda oddiy foydalanuvchilar /chatid ishlata olmaydi!
        if chat.type != "private":
            try:
                await message.delete()
            except Exception:
                pass
            return
        # Lichkada esa oddiy foydalanuvchiga o'z Chat ID si Shaxsiy Kabinetda ekanligini eslatamiz
        lang = await db.get_user_lang(user.id)
        msg = (
            "ℹ️ Ваш личный <b>Chat ID</b> отображается в разделе <b>«👤 Личный кабинет»</b>."
            if lang == "ru" else
            "ℹ️ Sizning shaxsiy <b>Chat ID</b> raqamingiz <b>«👤 Shaxsiy Kabinet»</b> bo'limida ko'rsatilgan."
        )
        await message.reply(msg, parse_mode="HTML")
        return

    if chat.type == "private":
        await message.reply(
            f"🆔 <b>Sizning Telegram ID (Chat ID) raqamingiz:</b>\n"
            f"<code>{user.id}</code>\n\n"
            f"👤 <b>Ism:</b> {user.full_name}",
            parse_mode="HTML"
        )
    else:
        thread_line = f"\n📌 <b>Topic (Bo'lim) ID:</b> <code>{message.message_thread_id}</code>" if message.message_thread_id else ""
        await message.reply(
            f"📢 <b>Guruh / Chat ma'lumotlari:</b>\n"
            f"🏷 <b>Nomi:</b> {chat.title}\n"
            f"🆔 <b>Chat ID:</b> <code>{chat.id}</code>{thread_line}\n"
            f"👤 <b>Sizning ID:</b> <code>{user.id}</code>",
            parse_mode="HTML"
        )

@dp.channel_post(Command("chatid", "id"))
async def cmd_chatid_channel(message: Message):
    chat = message.chat
    await message.reply(
        f"📢 <b>Kanal ma'lumotlari:</b>\n"
        f"🏷 <b>Kanal nomi:</b> {chat.title}\n"
        f"🆔 <b>Kanal Chat ID:</b> <code>{chat.id}</code>",
        parse_mode="HTML"
    )


# ===================== ZAYAVKA VA KANAL KIRISH-CHIQISH NAZORATI (1,000,000+ USER UCHUN) =====================
@dp.chat_join_request()
async def handle_join_request(update: ChatJoinRequest):
    await db.save_join_request(update.from_user.id, str(update.chat.id))

@dp.chat_member()
async def handle_channel_and_group_member_updates(update: ChatMemberUpdated):
    """
    1. Mavzuli Guruhga (-1002748514315) kirgan Premium foydalanuvchiga darhol [PREMIUM] tegini beradi!
    2. Majburiy obuna kanallarida (hatto 1 mln a'zoli bo'lsa ham) kirish va chiqishni real-time kuzatadi.
       Agar foydalanuvchi kanaldan chiqib ketsa, darhol zayavkasini bekor qiladi va unga lichkada
       «Iltimos, botdan to'g'ri foydalanish uchun kanallardan chiqib ketishga urinmang!» deb eslatma yuboradi!
    """
    user = update.new_chat_member.user
    if not user or user.is_bot:
        return

    user_id = user.id
    chat_id_str = str(update.chat.id)
    chat_username = f"@{update.chat.username}" if getattr(update.chat, "username", None) else ""
    old_st = update.old_chat_member.status
    new_st = update.new_chat_member.status

    # 1. Mavzuli Guruh (-1002748514315) uchun avto PREMIUM teg nazorati
    if chat_id_str == str(config.MAIN_TOPIC_GROUP_ID):
        if new_st in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR):
            if await db.is_user_premium(user_id):
                await apply_vip_tag_across_ecosystem(bot, user_id)
        return

    # 2. Majburiy obuna kanallari uchun real-time kirish-chiqish nazorati
    channels = await db.get_channels()
    matched_ch = None
    for ch in channels:
        c_id = str(ch["channel_id"]).strip()
        if c_id == chat_id_str or (chat_username and c_id.lower() == chat_username.lower()):
            matched_ch = ch
            break

    if not matched_ch:
        return

    target_ch_key = str(matched_ch["channel_id"])
    is_now_member = new_st in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR) or (
        new_st == ChatMemberStatus.RESTRICTED and getattr(update.new_chat_member, "is_member", True)
    )
    was_member = old_st in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR) or (
        old_st == ChatMemberStatus.RESTRICTED and getattr(update.old_chat_member, "is_member", True)
    )

    if is_now_member:
        await db.set_channel_member_status(user_id, target_ch_key, "member")
    elif was_member and new_st in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED):
        # Foydalanuvchi kanaldan chiqib ketdi!
        invalidate_sub_cache(user_id)
        await db.set_channel_member_status(user_id, target_ch_key, "left")
        role = await db.get_user_role(user_id)
        if role == "user":
            lang = await db.get_user_lang(user_id)
            unsubscribed = await check_subscriptions(user_id)
            if not unsubscribed:
                unsubscribed = [matched_ch]
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=t("left_channel_warn", lang, title=matched_ch.get("title", update.chat.title or "Kanal")),
                    reply_markup=kb.subscription_keyboard(unsubscribed, lang=lang),
                    parse_mode="HTML"
                )
            except Exception:
                pass


# ===================== /SPANEL VA /SADMIN — SUPER ADMINISTRATOR KIRISH =====================
@dp.message(Command("spanel", "sadmin"))
@dp.message(F.text == "👑 SUPER ADMIN PANEL")
async def cmd_super_admin_entry(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    await db.add_user(user_id, message.from_user.username or "", message.from_user.full_name or "")

    if await db.is_sadmin_session_valid(user_id):
        await message.answer(
            "👑 <b>SUPER ADMINISTRATOR PANELI</b>\n"
            "🔓 <i>24 soatlik xavfsiz sessiyangiz faol:</i>",
            reply_markup=kb.super_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    parts = (message.text or "").split()
    real_pass = await db.get_setting("super_admin_password", config.DEFAULT_SUPER_ADMIN_PASSWORD)
    if len(parts) > 1 and parts[1].strip() == real_pass:
        try:
            await message.delete()
        except Exception:
            pass
        await db.grant_sadmin_session(user_id)
        await message.answer(
            "👑 <b>Xush kelibsiz, Super Administrator!</b>\n"
            "✅ Sessiyangiz <b>24 soatga</b> faollashtirildi (1 sutka davomida qayta parol so'ralmaydi).",
            reply_markup=kb.super_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    await state.set_state(SuperAuthState.waiting_password)
    await message.answer(
        "🔐 <b>SUPER ADMINISTRATOR AVTORIZATSIYASI</b>\n\n"
        "Kirish uchun <b>Super-Admin maxfiy parolini</b> yuboring:\n"
        "<i>(Parol 1 sutkada 1 marta so'raladi)</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(SuperAuthState.waiting_password)
async def process_super_admin_password(message: Message, state: FSMContext):
    user_id = message.from_user.id
    entered = (message.text or "").strip()
    real_pass = await db.get_setting("super_admin_password", config.DEFAULT_SUPER_ADMIN_PASSWORD)

    if entered == real_pass:
        await state.clear()
        try:
            await message.delete()
        except Exception:
            pass
        await db.grant_sadmin_session(user_id)
        await message.answer(
            "👑 <b>Muvaffaqiyatli tasdiqlandi! Siz Super Administrator panelidasiz!</b>\n"
            "🕒 <i>Keyingi 24 soat davomida /spanel va /sadmin buyruqlari parolsiz ochiladi.</i>",
            reply_markup=kb.super_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        role = await db.get_user_role(user_id)
        await state.clear()
        await message.answer(
            "❌ <b>Xato parol! Kirish rad etildi.</b>",
            reply_markup=kb.user_main_keyboard(role),
            parse_mode="HTML"
        )


# ===================== /PANEL VA /ADMIN — MODERATOR VA ADMINISTRATOR PANELI =====================
@dp.message(Command("panel", "admin"))
@dp.message(F.text == "👮 Admin Panel")
async def cmd_staff_panel(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    role = await db.get_user_role(user_id)

    if role not in ("moderator", "admin", "superadmin"):
        await message.answer(
            "⛔ <b>Sizda Moderator yoki Administrator huquqi yo'q!</b>\n"
            "<i>Agar Super-Admin bo'lsangiz:</i> <code>/spanel</code> yoki <code>/sadmin</code> buyrug'ini yozing.",
            parse_mode="HTML"
        )
        return

    perms = await db.get_user_permissions(user_id)
    role_title = config.ROLES.get(role, "Xodim")
    await message.answer(
        f"👮 <b>BOSHQARUV PANELI ({role_title})</b>\n"
        f"✅ Siz uchun ruxsat etilgan funksiyalar: <b>{len(perms)} ta</b>",
        reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")),
        parse_mode="HTML"
    )


# ===================== SUPER ADMIN: PAROLNI O'ZGARTIRISH =====================
@dp.message(F.text == "🔐 Super-Parolni o'zgartirish")
async def sadmin_change_pass_start(message: Message, state: FSMContext):
    if await db.get_user_role(message.from_user.id) != "superadmin":
        return
    cur_pass = await db.get_setting("super_admin_password", config.DEFAULT_SUPER_ADMIN_PASSWORD)
    await state.set_state(SuperAuthState.change_password)
    await message.answer(
        f"🔐 <b>Super-Admin parolini yangilash:</b>\n\n"
        f"Hozirgi parol: <code>{cur_pass}</code>\n"
        f"Yangi parolni yozib yuboring:",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(SuperAuthState.change_password)
async def sadmin_change_pass_save(message: Message, state: FSMContext):
    new_pass = message.text.strip()
    if len(new_pass) < 4:
        await message.answer("⚠️ Parol kamida 4 ta belgidan iborat bo'lishi kerak! Qayta yozing:")
        return
    await db.set_setting("super_admin_password", new_pass)
    await state.clear()
    await message.answer(
        f"✅ <b>Super-Admin paroli muvaffaqiyatli o'zgartirildi!</b>\n"
        f"🔑 Yangi parol: <code>{new_pass}</code>",
        reply_markup=kb.super_admin_keyboard(),
        parse_mode="HTML"
    )


# ===================== SUPER ADMIN: 3 BOSQICHLI LAVOZIM VA GRANULAR RUXSATLAR =====================
@dp.message(F.text == "👮 Lavozim va Ruxsatlar")
async def sadmin_staff_menu(message: Message):
    if await db.get_user_role(message.from_user.id) != "superadmin":
        return
    staff = await db.get_all_staff()
    await message.answer(
        "👮 <b>LAVOZIMLAR VA GRANULAR RUXSATLAR BOSHQARUVI</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "• <b>🛡 Moderator</b> — Boshlang'ich yordamchi\n"
        "• <b>👮 Administrator</b> — Kengaytirilgan boshqaruvchi\n"
        "• <b>👑 Super Administrator</b> — To'liq huquqli egasi\n\n"
        "👇 <i>Yangi odamga lavozim berish yoki mavjud xodimning har bir funksiyasini yoqish/o'chirish uchun quyidan tanlang:</i>",
        reply_markup=kb.staff_control_menu_inline(staff),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "sadm_back_staff")
async def cb_sadm_back_staff(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    staff = await db.get_all_staff()
    await call.message.edit_text(
        "👮 <b>LAVOZIMLAR VA RUXSATLAR BOSHQARUVI:</b>",
        reply_markup=kb.staff_control_menu_inline(staff),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "sadm_add_staff")
async def cb_sadm_add_staff(call: CallbackQuery, state: FSMContext):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    await state.set_state(StaffManageState.waiting_chat_id)
    await call.message.answer(
        "🆔 Lavozim va huquq bermoqchi bo'lgan foydalanuvchining <b>Chat ID</b> raqamini yuboring:\n"
        "<i>(Foydalanuvchi botda /chatid yozib o'z ID sini bilishi mumkin)</i>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.message(StaffManageState.waiting_chat_id)
async def sadmin_open_user_permissions(message: Message, state: FSMContext):
    await state.clear()
    raw_id = message.text.strip()
    if not raw_id.isdigit():
        await message.answer("❌ Chat ID faqat raqamlardan iborat bo'lishi shart!", reply_markup=kb.super_admin_keyboard())
        return

    target_id = int(raw_id)
    u = await db.get_user(target_id)
    if not u:
        await db.set_user_role(target_id, "moderator")
        u = await db.get_user(target_id)

    role = await db.get_user_role(target_id)
    perms = await db.get_user_permissions(target_id)
    await message.answer("👑 Boshqaruv oynasi:", reply_markup=kb.super_admin_keyboard())
    await message.answer(
        f"👤 <b>Xodim sozlamalari:</b> {u.get('full_name', 'User')} (<code>{target_id}</code>)\n"
        f"🎖 <b>Joriy lavozimi:</b> {config.ROLES.get(role, role)}\n\n"
        f"👇 <i>Lavozimni tanlang va u ishlata oladigan funksiyalarni yoqing (✅) yoki olib tashlang (❌):</i>",
        reply_markup=kb.staff_permissions_inline(target_id, role, perms),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("sadm_edit_staff:"))
async def cb_sadm_edit_staff(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    target_id = int(call.data.split(":")[1])
    u = await db.get_user(target_id) or {"full_name": "User"}
    role = await db.get_user_role(target_id)
    perms = await db.get_user_permissions(target_id)

    await call.message.edit_text(
        f"👤 <b>Xodim:</b> {u.get('full_name', 'User')} (<code>{target_id}</code>)\n"
        f"🎖 <b>Joriy lavozimi:</b> {config.ROLES.get(role, role)}\n\n"
        f"👇 <i>Lavozimni o'zgartiring yoki funksiyalarni bittalab yoqib/o'chiring:</i>",
        reply_markup=kb.staff_permissions_inline(target_id, role, perms),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("setrole:"))
async def cb_set_user_role(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    _, tid_str, new_role = call.data.split(":")
    target_id = int(tid_str)

    await db.set_user_role(target_id, new_role)
    u = await db.get_user(target_id) or {"full_name": "User"}
    perms = await db.get_user_permissions(target_id)

    await call.message.edit_text(
        f"👤 <b>Xodim:</b> {u.get('full_name', 'User')} (<code>{target_id}</code>)\n"
        f"🎖 <b>Yangi lavozimi:</b> {config.ROLES.get(new_role, new_role)}\n\n"
        f"👇 <i>Endi unga tegishli funksiyalarni xohlagancha yoqib/o'chirishingiz mumkin:</i>",
        reply_markup=kb.staff_permissions_inline(target_id, new_role, perms),
        parse_mode="HTML"
    )
    await call.answer(f"✅ Lavozim: {config.ROLES.get(new_role, new_role)}")

    try:
        if new_role == "user":
            await bot.send_message(target_id, "ℹ️ Sizning moderator/admin lavozimingiz bekor qilindi.")
        else:
            await bot.send_message(
                target_id,
                f"🎉 <b>Tabriklaymiz!</b>\nSuper-Admin tomonidan sizga <b>{config.ROLES.get(new_role)}</b> lavozimi berildi!\n"
                f"Panelga kirish uchun <code>/panel</code> yoki <code>/admin</code> buyrug'ini yozing.",
                parse_mode="HTML"
            )
    except Exception:
        pass

@dp.callback_query(F.data.startswith("togperm:"))
async def cb_toggle_permission(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    _, tid_str, perm_key = call.data.split(":")
    target_id = int(tid_str)

    role = await db.get_user_role(target_id)
    if role == "user":
        await db.set_user_role(target_id, "moderator")
        role = "moderator"
    elif role == "superadmin":
        await call.answer("👑 Super Admindan funksiyani olib tashlash uchun avval uni Admin yoki Moderator darajasiga tushiring!", show_alert=True)
        return

    added = await db.toggle_user_permission(target_id, perm_key)
    perms = await db.get_user_permissions(target_id)
    await call.message.edit_reply_markup(reply_markup=kb.staff_permissions_inline(target_id, role, perms))
    p_name = config.PERMISSIONS.get(perm_key, perm_key)
    await call.answer(f"{'✅ Yoqildi' if added else '❌ Olib tashlandi'}: {p_name}")


# ===================== SUPER ADMIN: TOP-15 AI TIZIMI BOSHQARUVI =====================
async def get_ai_keys_status() -> dict:
    res = {}
    for p_key in config.TOP_15_AI_PROVIDERS:
        val = await db.get_setting(f"ai_key_{p_key}", "")
        res[p_key] = bool(val)
    return res

@dp.message(F.text == "🧠 Top-15 AI Tizimi")
async def sadmin_ai_menu(message: Message):
    if await db.get_user_role(message.from_user.id) != "superadmin":
        return
    ai_en = await db.get_setting("ai_enabled", "1")
    act_prov = await db.get_setting("ai_active_provider", "gemini")
    keys_st = await get_ai_keys_status()

    await message.answer(
        "🧠 <b>TOP-15 SUN'IY INTELLEKT (AI) AVTO-TAVSIF TIZIMI</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "• AI yoqilgan bo'lsa, kinolar qo'shilayotganda tavsifi yo'qlariga <b>avtomatik tavsif (description)</b> yozadi!\n"
        "• Tavsifi bor kinolarning esa <b>imlo xatolarini tekshirib, to'g'rilab</b> qo'yadi!\n"
        "• Hatto API Token kiritilmagan taqdirda ham botning <b>Ichki Aqlli AI Dvigateli</b> 100% bexato ishlaydi!\n\n"
        "👇 <i>Quyidagi Top-15 kuchli AI lardan xohlaganingizni tanlab API Token kiriting:</i>",
        reply_markup=kb.ai_dashboard_inline(ai_en, act_prov, keys_st),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "ai_back_main")
async def cb_ai_back_main(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    ai_en = await db.get_setting("ai_enabled", "1")
    act_prov = await db.get_setting("ai_active_provider", "gemini")
    keys_st = await get_ai_keys_status()
    await call.message.edit_text(
        "🧠 <b>TOP-15 SUN'IY INTELLEKT (AI) BOSHQARUVI:</b>",
        reply_markup=kb.ai_dashboard_inline(ai_en, act_prov, keys_st),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "ai_toggle_status")
async def cb_ai_toggle_status(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    cur = await db.get_setting("ai_enabled", "1")
    new_val = "0" if cur == "1" else "1"
    await db.set_setting("ai_enabled", new_val)
    act_prov = await db.get_setting("ai_active_provider", "gemini")
    keys_st = await get_ai_keys_status()
    await call.message.edit_reply_markup(reply_markup=kb.ai_dashboard_inline(new_val, act_prov, keys_st))
    await call.answer("🟢 AI Tizimi yoqildi!" if new_val == "1" else "🔴 AI Tizimi o'chirildi!")

@dp.callback_query(F.data.startswith("ai_select:"))
async def cb_ai_select_provider(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    p_key = call.data.split(":")[1]
    p_info = config.TOP_15_AI_PROVIDERS.get(p_key, {})
    cur_key = await db.get_setting(f"ai_key_{p_key}", "")
    masked = f"{cur_key[:6]}...{cur_key[-4:]}" if len(cur_key) > 10 else ("Kiritilgan" if cur_key else "Ichki AI Dvigateli faol ⚙️")

    await call.message.edit_text(
        f"🤖 <b>AI Provayder:</b> {p_info.get('name')}\n"
        f"⚙️ <b>Model:</b> <code>{p_info.get('model')}</code>\n"
        f"🔑 <b>API Token holati:</b> <code>{masked}</code>\n\n"
        f"👇 <i>Quyidagi amallardan birini tanlang:</i>",
        reply_markup=kb.ai_provider_detail_inline(p_key, bool(cur_key)),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("ai_setkey:"))
async def cb_ai_setkey_start(call: CallbackQuery, state: FSMContext):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    p_key = call.data.split(":")[1]
    p_name = config.TOP_15_AI_PROVIDERS.get(p_key, {}).get("name", p_key)
    await state.update_data(ai_provider=p_key)
    await state.set_state(AIKeyState.waiting_api_key)
    await call.message.answer(
        f"🔑 <b>{p_name}</b> uchun API Tokenni (API Key) yuboring:",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.message(AIKeyState.waiting_api_key)
async def ai_save_api_key(message: Message, state: FSMContext):
    data = await state.get_data()
    p_key = data["ai_provider"]
    token = message.text.strip()
    await db.set_setting(f"ai_key_{p_key}", token)
    await db.set_setting("ai_active_provider", p_key)
    await db.set_setting("ai_enabled", "1")
    await state.clear()

    try:
        await message.delete()
    except Exception:
        pass

    p_name = config.TOP_15_AI_PROVIDERS.get(p_key, {}).get("name", p_key)
    await message.answer(
        f"✅ <b>{p_name}</b> API Tokeni saqlandi va asosiy AI sifatida <b>🟢 Yoqildi!</b>",
        reply_markup=kb.super_admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("ai_activate:"))
async def cb_ai_activate_prov(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    p_key = call.data.split(":")[1]
    await db.set_setting("ai_active_provider", p_key)
    await db.set_setting("ai_enabled", "1")
    await call.answer("✅ Asosiy AI sifatida tanlandi va yoqildi!", show_alert=True)
    await cb_ai_back_main(call)

@dp.callback_query(F.data.startswith("ai_test:"))
async def cb_ai_test_prov(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    p_key = call.data.split(":")[1]
    await call.answer(f"🧪 AI ({p_key}) tekshirilmoqda...")
    res = await ai_service.process_movie_description_with_ai(
        name="Qasoskorlar: Intiho",
        genre="🔥 Jangari, 🚀 Fantastika",
        year="2019",
        country="AQSH"
    )
    await call.message.answer(f"✅ <b>AI ({p_key}) Test Natijasi:</b>\n\n<i>{res}</i>", parse_mode="HTML")

@dp.callback_query(F.data == "ai_run_batch")
async def cb_ai_run_batch_movies(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    await call.answer("🪄 AI barcha kinolar ma'lumoti va tavsifini to'ldirishni boshladi!")
    movies = await db.get_all_movies(500)
    status_msg = await call.message.answer(
        f"🪄 <b>{len(movies)} ta kino AI + Kino Ensiklopediyasi orqali to'liq to'ldirilmoqda...</b>",
        parse_mode="HTML"
    )

    updated = 0
    for m in movies:
        raw_blob = f"🎬 Nomi: {m['name']}"
        arch_mid = await db.get_archive_msg_id_for_code(m["code"])
        meta = await ai_service.enrich_movie_metadata_with_ai(
            raw_text=raw_blob,
            msg_id=arch_mid,
            existing_movie=m
        )
        new_name = meta["name"]
        new_genre = meta["genre"] if meta["has_genre"] else m.get("genre", "🔥 Jangari")
        new_year = meta["year"] if meta["has_year"] else m.get("year", "2024")
        new_country = meta["country"] if meta["has_country"] else m.get("country", "AQSH")
        new_qual = meta["quality"] if meta["has_quality"] else m.get("quality", "1080p Full HD")
        new_lang = "O'zbek tilida"
        new_cap = meta["caption"]

        if (
            new_name != m.get("name")
            or new_genre != m.get("genre")
            or new_year != m.get("year")
            or new_country != m.get("country")
            or new_cap != m.get("caption")
        ):
            await db.update_movie_full_metadata(
                code=m["code"],
                name=new_name,
                genre=new_genre,
                year=new_year,
                country=new_country,
                quality=new_qual,
                language=new_lang,
                caption=new_cap
            )
            updated += 1
        if not m.get("photo_id"):
            poster_url = await ai_service.find_movie_poster_tmdb(
                name=new_name,
                year=str(new_year),
                is_serial=bool(m.get("is_serial")),
                force=True
            )
            if poster_url:
                await db.update_movie_photo(m["code"], poster_url)
                updated += 1
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>AI to'liq tekshiruvi yakunlandi!</b>\n"
        f"🎬 Nomi, yili, davlati, janri va tavsifi to'ldirilgan/to'g'rilangan kinolar: <b>{updated} ta</b>",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "arch_ai_fix_posts")
async def cb_arch_ai_fix_posts(call: CallbackQuery):
    """
    Arxivdagi chala yoki tartiblanmagan postlarni (masalan: Javobsiz sevgi, Jodugar, Flesh va b.):
    1) AI + Kino Ensiklopediyasi yordamida aniq Nomi, Davlati, Yili, Sifati, Janri, Tilini aniqlaydi;
    2) Arxiv guruh/kanalga (-1003124847141) standart shablon bilan qayta yuboradi (re-post);
    3) Kim yuborgan bo'lishidan qat'i nazar eski chala postni Arxiv kanaldan avtomatik o'chirib yuboradi!
    """
    if not await _can_load_archive(call.from_user.id):
        await call.answer("⛔ Sizda bu amal uchun ruxsat yo'q!", show_alert=True)
        return
    await call.answer("✨ Arxivdagi chala postlar qayta yuborilib, eskisi o'chirilmoqda...")
    arch_ch_str = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    arch_ch = int(arch_ch_str)

    messy_items = await db.get_messy_archive_catalog_items()
    status_msg = await call.message.answer(
        f"✨ <b>Arxiv kanaldagi ({arch_ch}) {len(messy_items)} ta chala/tartiblanmagan postlar qayta yuborilib, tavsifi standart shablonga to'g'rilanmoqda va eskisi o'chirilmoqda...</b>",
        parse_mode="HTML"
    )

    fixed_cnt = 0
    deleted_old_cnt = 0

    for idx, item in enumerate(messy_items, 1):
        old_mid = int(item["msg_id"])
        fid = await _resolve_catalog_file_id(item, arch_ch, call.from_user.id)
        if not fid:
            continue

        meta = {
            "name": item.get("parsed_name") or item.get("base_title") or "Kino",
            "country": item.get("country") or "AQSH",
            "year": item.get("year") or "2024",
            "quality": item.get("quality") or "1080p Full HD",
            "genre": item.get("genre") or "🔥 Jangari",
            "language": "O'zbek tilida"
        }
        std_cap = ai_service.format_standard_archive_caption(meta)

        try:
            # 1. Аввал tahrirlab ko'ramiz; agar bot o'zi qayta post qilishi kerak bo'lsa yangi post yuborib eskisini o'chiramiz!
            new_msg = None
            try:
                new_msg = await bot.send_video(
                    chat_id=arch_ch,
                    video=fid,
                    caption=std_cap,
                    disable_notification=True
                )
            except Exception:
                try:
                    new_msg = await bot.send_document(
                        chat_id=arch_ch,
                        document=fid,
                        caption=std_cap,
                        disable_notification=True
                    )
                except Exception:
                    pass

            if new_msg:
                fixed_cnt += 1
                try:
                    await bot.delete_message(chat_id=arch_ch, message_id=old_mid)
                    deleted_old_cnt += 1
                except Exception as del_err:
                    logging.debug(f"Eski postni o'chirish ({old_mid}): {del_err}")
                await db.replace_archive_catalog_msg_id(old_mid, new_msg.message_id, std_cap, fid)
            else:
                await bot.edit_message_caption(chat_id=arch_ch, message_id=old_mid, caption=std_cap)
                fixed_cnt += 1
                await db.replace_archive_catalog_msg_id(old_mid, old_mid, std_cap, fid)
        except Exception as e:
            logging.debug(f"Arxiv post yangilash ({old_mid}): {e}")

        if idx % 5 == 0 or idx == len(messy_items):
            try:
                await status_msg.edit_text(
                    f"✨ <b>Arxivdagi chala postlar yangilanmoqda: {idx} / {len(messy_items)}</b>\n"
                    f"✅ Standart shablonga to'g'rilandi: <b>{fixed_cnt} ta</b> | 🗑 Eskisi o'chirildi: <b>{deleted_old_cnt} ta</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await asyncio.sleep(3.1)  # Guruh rate-limitdan o'tish uchun xavfsiz pauza

    await status_msg.edit_text(
        f"✅ <b>ARXIV KANAL CHALA POSTLARINI TO'LDIRISH YAKUNLANDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ <b>Standart shablonga keltirilib qayta yuborilgan kinolar:</b> {fixed_cnt} ta\n"
        f"🗑 <b>O'chirilgan eski chala postlar:</b> {deleted_old_cnt} ta",
        parse_mode="HTML"
    )


# ===================== SUPER ADMIN: BACKUP / EXPORT / IMPORT MARKAZI =====================
async def send_full_backup_to_target(target_chat_id: int, title_note: str = "AVTOMATIK HAFTALIK BACKUP") -> bool:
    """
    To'liq baza (.db) va JSON eksportni Arxiv Guruhga (-1003124847141) yoki Super Adminga yuboradi.
    """
    try:
        st = await db.get_full_stats()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        snap = await db.make_db_snapshot("archive_backup.db")
        json_path = await db.export_full_json("movieland_backup.json")
        await bot.send_document(
            chat_id=target_chat_id,
            document=FSInputFile(snap, filename=f"movieland_{datetime.now().strftime('%Y%m%d_%H%M')}.db"),
            caption=(
                f"💾 <b>{title_note} (database.db)</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🕒 <b>Vaqt:</b> <code>{now_str}</code>\n"
                f"👥 <b>Foydalanuvchilar:</b> {st['total_users']} ta\n"
                f"🎬 <b>Kinolar:</b> {st['total_movies']} ta | 📺 <b>Seriallar:</b> {st['total_serials']} ta ({st['total_episodes']} qism)\n"
                f"🗄 <b>Manzil:</b> Movie Land ARXIV (<code>{target_chat_id}</code>)"
            ),
            parse_mode="HTML"
        )
        await bot.send_document(
            chat_id=target_chat_id,
            document=FSInputFile(json_path, filename=f"movieland_json_{datetime.now().strftime('%Y%m%d_%H%M')}.json"),
            caption=f"📦 <b>{title_note} — JSON Format (Kinolar + Qismlar + Foydalanuvchilar)</b>",
            parse_mode="HTML"
        )
        return True
    except Exception as e:
        logging.warning(f"Backup yuborishda xato ({target_chat_id}): {e}")
        return False

@dp.message(F.text == "💾 Backup va Export/Import")
async def sadmin_backup_menu(message: Message):
    if await db.get_user_role(message.from_user.id) != "superadmin":
        return
    auto_h = await db.get_setting("auto_backup_hours", "168")
    arch_ch = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    await message.answer(
        f"💾 <b>MA'LUMOTLAR BAZASI BACKUP VA EXPORT/IMPORT MARKAZI</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🗄 <b>Avto-Backup manzili:</b> Arxiv Guruh (<code>{arch_ch}</code>)\n"
        f"• Har haftada (168 soatda) va siz xohlagan paytda tugmani bosganingizda to'liq Backup avtomatik ravishda <b>Arxiv Guruhga</b> yuboriladi!\n"
        f"• Shuningdek, bazani (`.db`, `.json`, `.csv`) shu yerga yuklab olishingiz yoki qayta Import qilishingiz mumkin.",
        reply_markup=kb.backup_center_inline(auto_h),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "bkp_send_archive_now")
async def cb_bkp_send_archive_now(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    await call.answer("📤 Arxiv guruhga to'liq backup yuborilmoqda...")
    arch_ch = int(await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID))
    ok = await send_full_backup_to_target(arch_ch, title_note="MAXSUS BAZA BACKUP")
    if ok:
        await call.message.answer(
            f"✅ <b>To'liq baza (.db va .json) Arxiv Guruhga (<code>{arch_ch}</code>) muvaffaqiyatli yuborildi!</b>",
            parse_mode="HTML"
        )
    else:
        await call.message.answer(
            f"❌ Arxiv guruhga (<code>{arch_ch}</code>) yuborishda xatolik yuz berdi.",
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "bkp_download_db")
async def cb_bkp_download_db(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    await call.answer("📥 Baza yuborilmoqda...")
    st = await db.get_full_stats()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    snap = await db.make_db_snapshot("manual_backup.db")
    await call.message.answer_document(
        document=FSInputFile(snap, filename=f"movieland_{datetime.now().strftime('%Y%m%d_%H%M')}.db"),
        caption=(
            f"💾 <b>TO'LIQ BAZA BACKUP (database.db)</b>\n"
            f"🕒 Vaqti: <code>{now_str}</code>\n"
            f"👥 Foydalanuvchilar: <b>{st['total_users']} ta</b>\n"
            f"🎬 Kinolar: <b>{st['total_movies'] + st['total_serials']} ta</b>"
        ),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "bkp_export_json")
async def cb_bkp_export_json(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    await call.answer("📦 JSON tayyorlanmoqda...")
    path = await db.export_full_json("movieland_backup.json")
    await call.message.answer_document(
        document=FSInputFile(path),
        caption="📦 <b>Kinolar, Qismlar va Userlar JSON Exporti</b>",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "bkp_export_csv")
async def cb_bkp_export_csv(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    await call.answer("📊 Excel/CSV tayyorlanmoqda...")
    path = await db.export_movies_csv("movies_catalog.csv")
    await call.message.answer_document(
        document=FSInputFile(path),
        caption="📊 <b>Barcha kinolar jadvali (Excel / CSV)</b>",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "bkp_toggle_auto")
async def cb_bkp_toggle_auto(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    cur = await db.get_setting("auto_backup_hours", "168")
    cycle = {"168": "24", "24": "12", "12": "0", "0": "168"}
    nxt = cycle.get(cur, "168")
    arch_ch = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    await db.set_setting("auto_backup_hours", nxt)
    await db.set_setting("auto_backup_target", str(arch_ch))
    await call.message.edit_reply_markup(reply_markup=kb.backup_center_inline(nxt))
    if nxt == "168":
        msg = "⏰ Avto-Backup har haftada (168 soatda) Arxiv guruhga yuboriladigan qilib sozlandi!"
    elif nxt != "0":
        msg = f"⏰ Avto-Backup har {nxt} soatda Arxiv guruhga yuboriladigan qilib sozlandi!"
    else:
        msg = "🔴 Avto-Backup o'chirildi."
    await call.answer(msg, show_alert=True)

@dp.callback_query(F.data == "bkp_import_start")
async def cb_bkp_import_start(call: CallbackQuery, state: FSMContext):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    await state.set_state(BackupImportState.waiting_file)
    await call.message.answer(
        "📤 <b>BAZA IMPORT QILISH:</b>\n\n"
        "Yangilangan <code>.json</code> yoki <code>.db</code> faylni shu yerga yuboring:",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.message(BackupImportState.waiting_file, F.document)
async def bkp_import_process(message: Message, state: FSMContext):
    await state.clear()
    fname = message.document.file_name or ""
    file_info = await bot.get_file(message.document.file_id)

    if fname.endswith(".json"):
        temp_path = "imported_data.json"
        await bot.download_file(file_info.file_path, temp_path)
        res = await db.import_full_json(temp_path)
        await message.answer(
            f"✅ <b>JSON Baza muvaffaqiyatli birlashtirildi (Import)!</b>\n\n"
            f"🎬 Kinolar: <b>{res['movies']} ta</b> | 🎞 Qismlar: <b>{res['episodes']} ta</b> | 👥 Userlar: <b>{res['users']} ta</b>",
            reply_markup=kb.super_admin_keyboard(),
            parse_mode="HTML"
        )
    elif fname.endswith(".db"):
        shutil.copyfile(db.DB_NAME, "database_before_import.db.bak")
        await bot.download_file(file_info.file_path, db.DB_NAME)
        await db.init_db()
        await message.answer(
            "✅ <b>To'liq .db baza muvaffaqiyatli yangilandi!</b>",
            reply_markup=kb.super_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Faqat `.json` yoki `.db` formatdagi faylni yuboring!", reply_markup=kb.super_admin_keyboard())


# ===================== PREMIUM (VIP) VA LIMITLAR =====================
@dp.message(F.text.in_(["💎 VIP va Limitlar", "💎 VIP berish / olish"]))
async def vip_manage_menu(message: Message):
    if not await db.has_permission(message.from_user.id, "vip_manage"):
        await message.answer("⛔ Sizda VIP boshqaruvi huquqi yo'q!")
        return
    await render_economy_admin_panel(message)

@dp.callback_query(F.data == "vip_chg_free")
async def cb_vip_chg_free(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        await call.answer("Faqat Super Admin limitni o'zgartira oladi!", show_alert=True)
        return
    cur = await db.get_setting("free_order_limit", "1")
    nxt = "2" if cur == "1" else "1"
    await db.set_setting("free_order_limit", nxt)
    await render_economy_admin_panel(call)
    await call.answer(f"Oddiy limit: kuniga {nxt} ta")

@dp.callback_query(F.data == "vip_chg_vip")
async def cb_vip_chg_vip(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        await call.answer("Faqat Super Admin limitni o'zgartira oladi!", show_alert=True)
        return
    cur = await db.get_setting("premium_order_limit", "5")
    cycle = {"3": "4", "4": "5", "5": "3"}
    nxt = cycle.get(cur, "5")
    await db.set_setting("premium_order_limit", nxt)
    await render_economy_admin_panel(call)
    await call.answer(f"💎 VIP limit: kuniga {nxt} ta")

@dp.callback_query(F.data == "vip_list")
async def cb_vip_list(call: CallbackQuery):
    vips = await db.get_all_premium_users()
    if not vips:
        await call.answer("Hozircha VIP foydalanuvchilar yo'q.", show_alert=True)
        return
    txt = "💎 <b>Premium (VIP) foydalanuvchilar ro'yxati:</b>\n\n"
    for i, v in enumerate(vips, 1):
        until = (v.get("premium_until") or "")[:10]
        tag = v.get("vip_tag") or "PREMIUM"
        txt += f"{i}. <b>{v.get('full_name')}</b> [<code>{tag}</code>] (<code>{v['user_id']}</code>) — gacha: {until}\n"
    await call.message.answer(txt, parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "vip_give")
async def cb_vip_give_start(call: CallbackQuery, state: FSMContext):
    if not await db.has_permission(call.from_user.id, "vip_manage"):
        return
    await state.set_state(VIPManageState.give_id)
    await call.message.answer(
        "💎 Premium bermoqchi bo'lgan foydalanuvchining <b>Chat ID</b> raqamini va necha kunga berilishini yuboring:\n"
        "Masalan: <code>123456789 | 30</code>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.message(VIPManageState.give_id)
async def vip_give_process(message: Message, state: FSMContext):
    await state.clear()
    parts = [p.strip() for p in message.text.split("|")]
    if not parts[0].isdigit():
        await message.answer("❌ Noto'g'ri ID!")
        return
    uid = int(parts[0])
    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 30
    await db.extend_user_premium(uid, days)
    await apply_vip_tag_across_ecosystem(bot, uid)
    role = await db.get_user_role(message.from_user.id)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    await log_to_activity_topic(
        bot,
        f"💎 <b>ADMIN TOMONIDAN PREMIUM BERILDI!</b>\n"
        f"👤 Qabul qiluvchi ID: <code>{uid}</code>\n"
        f"📦 Muddat: <b>{days} kun</b>\n"
        f"👑 Berdi: <b>{message.from_user.full_name}</b>\n"
        f"🕒 Vaqt: <code>{now_str}</code>"
    )

    await message.answer(
        f"✅ <code>{uid}</code> foydalanuvchiga <b>{days} kunlik 💎 Premium (VIP)</b> va Movie Land Group da <b>[PREMIUM]</b> tegi berildi!",
        reply_markup=kb.super_admin_keyboard() if role == "superadmin" else kb.staff_panel_keyboard(await db.get_user_permissions(message.from_user.id)),
        parse_mode="HTML"
    )
    u_lang = await db.get_user_lang(uid)
    rev_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Оставить отзыв в 💸 Premium" if u_lang == "ru" else "💬 💸 Premium bo'limiga Otziv yozish",
            callback_data="vip_leave_review"
        )]
    ])
    try:
        txt = (
            f"🎉 <b>ПОЗДРАВЛЯЕМ!</b>\nВам выдан статус <b>💎 PREMIUM (VIP) на {days} дней</b> и тег <b>[PREMIUM]</b> в группе Movie Land Group!"
            if u_lang == "ru" else
            f"🎉 <b>TABRIKLAYMIZ!</b>\nSizga <b>{days} kun muddatga 💎 PREMIUM (VIP)</b> maqomi va Movie Land Group da <b>[PREMIUM]</b> tegi berildi!"
        )
        await bot.send_message(uid, txt, reply_markup=rev_btn, parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data == "vip_remove")
async def cb_vip_remove_start(call: CallbackQuery, state: FSMContext):
    if not await db.has_permission(call.from_user.id, "vip_manage"):
        return
    await state.set_state(VIPManageState.remove_id)
    await call.message.answer("❌ Premiumdan chiqarmoqchi bo'lgan foydalanuvchi <b>Chat ID</b> sini yuboring:", reply_markup=kb.cancel_keyboard(), parse_mode="HTML")
    await call.answer()

@dp.message(VIPManageState.remove_id)
async def vip_remove_process(message: Message, state: FSMContext):
    await state.clear()
    if not message.text.strip().isdigit():
        await message.answer("❌ Noto'g'ri ID!")
        return
    uid = int(message.text.strip())
    await db.set_user_premium(uid, 0)
    await remove_vip_tag_across_ecosystem(bot, uid)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await log_to_activity_topic(
        bot,
        f"🚫 <b>PREMIUM BEKOR QILINDI (TEG O'CHIRILDI)</b>\n"
        f"👤 User ID: <code>{uid}</code> | 🕒 Vaqt: <code>{now_str}</code>"
    )
    await message.answer(f"✅ <code>{uid}</code> dan Premium va guruhdagi [PREMIUM] tegi olib tashlandi.", parse_mode="HTML")


# ===================== /START VA FOYDALANUVCHI MENYUSI (2 TILLI: UZ / RU) =====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await get_bot_username()
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or "Foydalanuvchi"
    lang = await db.get_user_lang(user_id)

    if await db.is_user_banned(user_id):
        await message.answer(t("banned", lang), parse_mode="HTML")
        return

    bot_active = await db.get_setting("bot_active", "1")
    role = await db.get_user_role(user_id)
    if bot_active == "0" and role == "user":
        await message.answer(t("maintenance", lang), parse_mode="HTML")
        return

    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    param = args[0] if args else None

    ref_by, movie_code = None, None
    if param:
        if param.startswith("ref_"):
            ref_str = param.replace("ref_", "")
            if ref_str.isdigit():
                ref_by = int(ref_str)
        else:
            movie_code = param.lstrip("#")

    add_res = await db.add_user(user_id, username, full_name, ref_by=ref_by)
    if isinstance(add_res, dict) and add_res.get("is_new"):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ref_info = f"Taklif qildi: <code>{ref_by}</code> (+{add_res.get('ref_reward', 0):,} so'm)" if ref_by else "O'zi kirdi (/start)"
        await log_to_activity_topic(
            bot,
            f"👤 <b>YANGI FOYDALANUVCHI QO'SHILDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏷 <b>Ism:</b> {full_name} (@{username or 'yoq'})\n"
            f"🆔 <b>Chat ID:</b> <code>{user_id}</code>\n"
            f"🔗 <b>Manba:</b> {ref_info}\n"
            f"🕒 <b>Vaqt:</b> <code>{now_str}</code>"
        )
        if ref_by and add_res.get("ref_reward", 0) > 0:
            rew_sum = add_res["ref_reward"]
            try:
                ref_u = await db.get_user(ref_by) or {}
                ref_lang = await db.get_user_lang(ref_by)
                if ref_lang == "ru":
                    ref_msg = (
                        f"🎉 <b>Новый реферал и Денежный бонус!</b>\n"
                        f"👤 Ваш друг <b>{full_name}</b> присоединился к боту по вашей ссылке!\n"
                        f"💵 Начислено: <b>+{rew_sum:,} сум</b>\n"
                        f"💰 Ваш баланс: <b>{ref_u.get('balance', 0):,} сум</b>"
                    )
                else:
                    ref_msg = (
                        f"🎉 <b>Yangi referal va Pul mukofoti!</b>\n"
                        f"👤 Do'stingiz <b>{full_name}</b> sizning taklif havolangiz orqali botga qo'shildi!\n"
                        f"💵 Balansingizga: <b>+{rew_sum:,} so'm</b> qo'shildi!\n"
                        f"💰 Joriy balansingiz: <b>{ref_u.get('balance', 0):,} so'm</b>"
                    )
                await bot.send_message(ref_by, ref_msg, parse_mode="HTML")
            except Exception:
                pass

    # 1-QADAM: Agar foydalanuvchi hali til tanlamagan bo'lsa, /start bosilganda BIRINCHI navbatda til so'raladi!
    # Til tanlangandan so'nggina majburiy obuna kanallari chiqadi!
    if not await db.has_chosen_lang(user_id):
        await message.answer(
            t("choose_lang", "uz"),
            reply_markup=kb.language_select_inline(movie_code=movie_code),
            parse_mode="HTML"
        )
        return

    # 2-QADAM: Til tanlangan bo'lsa, majburiy obuna kanallarini tekshiramiz
    unsubscribed = await check_subscriptions(user_id)
    if unsubscribed:
        left_before = await db.has_user_left_channel(user_id)
        prompt_txt = t("sub_left_reminder", lang) if left_before else t("sub_prompt", lang, name=full_name)
        markup = kb.subscription_keyboard(unsubscribed, movie_code=movie_code, lang=lang)
        await message.answer(
            prompt_txt,
            reply_markup=markup,
            parse_mode="HTML"
        )
        return

    # 3-QADAM: Obuna tasdiqlangan bo'lsa, kino yoki asosiy menyuni ochamiz
    if movie_code:
        await message.answer(t("loading_movie", lang), reply_markup=kb.user_main_keyboard(role, lang=lang), parse_mode="HTML")
        await send_movie_card(message, user_id, movie_code)
        return

    is_vip = await db.is_user_premium(user_id)
    u = await db.get_user(user_id) or {}
    tag = u.get("vip_tag") or "PREMIUM"
    vip_badge = t("vip_badge_active", lang, tag=tag) if is_vip else t("vip_badge_free", lang)

    welcome = t("welcome", lang, name=full_name, vip_badge=vip_badge)
    await message.answer(
        "🏠 <b>Asosiy panel:</b>" if lang != "ru" else "🏠 <b>Главная панель:</b>",
        reply_markup=kb.user_main_keyboard(role, lang=lang),
        parse_mode="HTML"
    )
    await message.answer(
        welcome,
        reply_markup=kb.user_inline_dashboard(lang=lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("set_lang:"))
async def cb_set_language(call: CallbackQuery):
    """
    Foydalanuvchi tilni tanlagan zahoti:
    1) Til saqlanadi;
    2) Majburiy obuna kanallari tekshiriladi — agar a'zo bo'lmagan bo'lsa, tanlangan tilda kanallar chiqadi!
    3) Agar barcha kanallarga a'zo bo'lsa, asosiy menyu (yoki kino) ochiladi!
    """
    user_id = call.from_user.id
    parts = call.data.split(":")
    new_lang = parts[1] if len(parts) > 1 else "uz"
    movie_code = parts[2] if len(parts) > 2 and parts[2] else None

    await db.set_user_lang(user_id, new_lang)
    role = await db.get_user_role(user_id)

    try:
        await call.message.delete()
    except Exception:
        pass

    await call.message.answer(
        t("lang_saved", new_lang),
        reply_markup=kb.user_main_keyboard(role, lang=new_lang),
        parse_mode="HTML"
    )

    # Til tanlangandan so'ng majburiy obuna kanallarini tekshiramiz!
    unsubscribed = await check_subscriptions(user_id)
    if unsubscribed:
        left_before = await db.has_user_left_channel(user_id)
        prompt_txt = t("sub_left_reminder", new_lang) if left_before else t("sub_prompt", new_lang, name=call.from_user.full_name)
        await call.message.answer(
            prompt_txt,
            reply_markup=kb.subscription_keyboard(unsubscribed, movie_code=movie_code, lang=new_lang),
            parse_mode="HTML"
        )
        await call.answer()
        return

    if movie_code:
        await send_movie_card(call, user_id, movie_code)

    is_vip = await db.is_user_premium(user_id)
    u = await db.get_user(user_id) or {}
    tag = u.get("vip_tag") or "PREMIUM"
    vip_badge = t("vip_badge_active", new_lang, tag=tag) if is_vip else t("vip_badge_free", new_lang)

    await call.message.answer(
        t("welcome", new_lang, name=call.from_user.full_name, vip_badge=vip_badge),
        reply_markup=kb.user_inline_dashboard(lang=new_lang),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data == "back_main_menu")
async def cb_back_main_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    is_vip = await db.is_user_premium(user_id)
    u = await db.get_user(user_id) or {}
    tag = u.get("vip_tag") or "PREMIUM"
    vip_badge = t("vip_badge_active", lang, tag=tag) if is_vip else t("vip_badge_free", lang)
    welcome = t("welcome", lang, name=call.from_user.full_name, vip_badge=vip_badge)
    try:
        await call.message.edit_text(
            welcome,
            reply_markup=kb.user_inline_dashboard(lang=lang),
            parse_mode="HTML"
        )
    except Exception:
        await call.message.answer(
            welcome,
            reply_markup=kb.user_inline_dashboard(lang=lang),
            parse_mode="HTML"
        )
    await call.answer()

@dp.callback_query(F.data.startswith("check_sub"))
async def cb_check_sub(call: CallbackQuery):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    parts = call.data.split(":")
    movie_code = parts[1] if len(parts) > 1 and parts[1] else None

    unsubscribed = await check_subscriptions(user_id)
    if unsubscribed:
        await call.answer(t("sub_not_all", lang), show_alert=True)
        return

    await call.message.delete()
    role = await db.get_user_role(user_id)
    await call.message.answer(
        t("sub_ok", lang),
        reply_markup=kb.user_main_keyboard(role, lang=lang),
        parse_mode="HTML"
    )
    if movie_code:
        await send_movie_card(call, user_id, movie_code)
    elif not await db.has_chosen_lang(user_id):
        await call.message.answer(t("choose_lang", lang), reply_markup=kb.language_select_inline(), parse_mode="HTML")
    else:
        is_vip = await db.is_user_premium(user_id)
        u = await db.get_user(user_id) or {}
        tag = u.get("vip_tag") or "PREMIUM"
        vip_badge = t("vip_badge_active", lang, tag=tag) if is_vip else t("vip_badge_free", lang)
        welcome = t("welcome", lang, name=call.from_user.full_name, vip_badge=vip_badge)
        await call.message.answer(welcome, reply_markup=kb.user_inline_dashboard(lang=lang), parse_mode="HTML")

@dp.message(F.text.in_(b_vals("cancel")))
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    role = await db.get_user_role(user_id)
    if role == "superadmin":
        await message.answer(t("cancelled", lang), reply_markup=kb.super_admin_keyboard())
    elif role in ("moderator", "admin"):
        perms = await db.get_user_permissions(user_id)
        await message.answer(t("cancelled", lang), reply_markup=kb.staff_panel_keyboard(perms))
    else:
        await message.answer(t("cancelled", lang), reply_markup=kb.user_main_keyboard(role, lang=lang))
        is_vip = await db.is_user_premium(user_id)
        u = await db.get_user(user_id) or {}
        tag = u.get("vip_tag") or "PREMIUM"
        vip_badge = t("vip_badge_active", lang, tag=tag) if is_vip else t("vip_badge_free", lang)
        welcome = t("welcome", lang, name=message.from_user.full_name, vip_badge=vip_badge)
        await message.answer(welcome, reply_markup=kb.user_inline_dashboard(lang=lang), parse_mode="HTML")

@dp.message(F.text.in_(b_vals("user_menu")))
async def switch_to_user_menu(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    role = await db.get_user_role(user_id)
    msg = "🏠 <b>Главное меню пользователя:</b>" if lang == "ru" else "🏠 <b>Foydalanuvchi bosh menyusi:</b>"
    await message.answer(msg, reply_markup=kb.user_main_keyboard(role, lang=lang), parse_mode="HTML")
    is_vip = await db.is_user_premium(user_id)
    u = await db.get_user(user_id) or {}
    tag = u.get("vip_tag") or "PREMIUM"
    vip_badge = t("vip_badge_active", lang, tag=tag) if is_vip else t("vip_badge_free", lang)
    welcome = t("welcome", lang, name=message.from_user.full_name, vip_badge=vip_badge)
    await message.answer(welcome, reply_markup=kb.user_inline_dashboard(lang=lang), parse_mode="HTML")


# ===================== POLZOVATEL BO'LIMLARI (INLINE DASHBOARD + REPLY, UZ / RU) =====================
async def send_movies_search_catalog(target, user_id: int, state: FSMContext, page: int = 1):
    """
    «🔍 Kino qidirish» bosilganda:
    2-chi rasmdagi menyuli kino ro'yxati (menulik kino poisk) BUTKUL olib tashlangan!
    Faqat 3-chi rasmdagidek «🔍 Inline rejimda (Rasmli Ro'yxat) qidirish» tugmasi chiqadi
    va bosilganda (yoki @movieeland_bot kiritilganda) TMDB posterlari va ma'lumotlari bilan avto-qidiruv ochiladi!
    """
    lang = await db.get_user_lang(user_id)
    await state.clear()
    _, total = await db.get_movies_paginated(offset=0, limit=1)

    if lang == "ru":
        header = (
            f"🔍 <b>ПОИСК ФИЛЬМОВ (Всего: {total} шт.)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>🔢 Напишите <b>код фильма</b> (например: <code>1</code>)\n"
            f"🔤 Или <b>название фильма / ключевое слово</b></blockquote>\n\n"
            f"👇 <i>Или откройте галерею постеров кнопкой ниже:</i>"
        )
    else:
        header = (
            f"🔍 <b>KINO QIDIRISH (Jami: {total} ta)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>🔢 Kino <b>kodini</b> yozing (masalan: <code>1</code>)\n"
            f"🔤 Yoki kino <b>nomi / kalit so'zini</b> yozing</blockquote>\n\n"
            f"👇 <i>Yoki quyidagi tugma orqali rasmli ro'yxatdan qidiring:</i>"
        )

    markup = kb.movies_catalog_paginated_inline(lang=lang)
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(header, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await target.message.answer(header, reply_markup=markup, parse_mode="HTML")
    else:
        await target.answer(header, reply_markup=markup, parse_mode="HTML")

@dp.message(F.text.in_(b_vals("search")))
async def user_search_start(message: Message, state: FSMContext):
    await send_movies_search_catalog(message, message.from_user.id, state, page=1)

@dp.callback_query(F.data == "nav:search")
async def cb_nav_search(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await send_movies_search_catalog(call, call.from_user.id, state, page=1)

@dp.callback_query(F.data.startswith("catpage:"))
async def cb_catalog_page(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await send_movies_search_catalog(call, call.from_user.id, state, page=1)

@dp.callback_query(F.data == "cat_noop")
async def cb_cat_noop(call: CallbackQuery):
    await call.answer()

@dp.callback_query(F.data.startswith("cat_filter:"))
async def cb_cat_filter(call: CallbackQuery, state: FSMContext):
    filter_type = call.data.split(":")[1]
    lang = await db.get_user_lang(call.from_user.id)
    await call.answer()

    if filter_type == "top":
        movies = await db.get_top_movies(12)
        title = "🔥 <b>ENG KO'P KO'RILGAN TOP KINOLAR:</b>" if lang != "ru" else "🔥 <b>САМЫЕ ПОПУЛЯРНЫЕ ТОП ФИЛЬМЫ:</b>"
        markup = kb.movies_list_inline(movies, "🔥", lang=lang, query="top")
        try:
            await call.message.edit_text(title, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await call.message.answer(title, reply_markup=markup, parse_mode="HTML")
    elif filter_type == "latest":
        movies = await db.get_latest_movies(12)
        title = "⚡ <b>ENG SO'NGGI QO'SHILGAN YANGI KINOLAR:</b>" if lang != "ru" else "⚡ <b>САМЫЕ НОВЫЕ ДОБАВЛЕННЫЕ ФИЛЬМЫ:</b>"
        markup = kb.movies_list_inline(movies, "⚡", lang=lang, query="new")
        try:
            await call.message.edit_text(title, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await call.message.answer(title, reply_markup=markup, parse_mode="HTML")
    elif filter_type == "genres":
        title = t("genres_title", lang)
        markup = kb.genres_inline_keyboard(for_admin=False, lang=lang)
        try:
            await call.message.edit_text(title, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await call.message.answer(title, reply_markup=markup, parse_mode="HTML")
    elif filter_type == "random":
        m = await db.get_random_movie()
        if m:
            await send_movie_card(call, call.from_user.id, m["code"])
        else:
            await call.message.answer(t("db_empty", lang))

@dp.message(StateFilter("*"), F.chat.type == "private", F.text.regexp(r"^(?:🎬|📺)\s*#(\d+)\b"))
async def handle_inline_chosen_movie_message(message: Message, state: FSMContext):
    """
    Foydalanuvchi @movieeland_bot rasmli inline ro'yxatidan kinoni bosganda,
    oraliq matnni o'chirib, darhol kinoning videosini yuboradi!
    """
    await state.clear()
    user_id = message.from_user.id
    if await db.is_user_banned(user_id):
        return
    m_match = re.match(r"^(?:🎬|📺)\s*#(\d+)\b", message.text or "")
    if not m_match:
        return
    code = m_match.group(1)
    try:
        await message.delete()
    except Exception:
        pass
    await send_movie_card(message, user_id, code)

@dp.message(SearchState.query)
async def user_search_process(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    role = await db.get_user_role(user_id)
    q = message.text.strip()

    if q.lstrip("#").isdigit():
        await send_movie_card(message, user_id, q.lstrip("#"))
        return

    results = await db.search_movies_by_name(q)
    if not results:
        await message.answer(
            t("movie_not_found_text", lang, q=q),
            reply_markup=kb.user_main_keyboard(role, lang=lang),
            parse_mode="HTML"
        )
        return

    if len(results) == 1:
        await send_movie_card(message, user_id, results[0]["code"])
        return

    await message.answer(
        t("search_results", lang, q=q, cnt=len(results)),
        reply_markup=kb.movies_list_inline(results, "🎬", lang=lang, query=q),
        parse_mode="HTML"
    )

@dp.message(F.text.in_(b_vals("genres")))
async def show_genres(message: Message):
    lang = await db.get_user_lang(message.from_user.id)
    await message.answer(
        t("genres_title", lang),
        reply_markup=kb.genres_inline_keyboard(for_admin=False, lang=lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "nav:genres")
async def cb_nav_genres(call: CallbackQuery):
    lang = await db.get_user_lang(call.from_user.id)
    try:
        await call.message.edit_text(
            t("genres_title", lang),
            reply_markup=kb.genres_inline_keyboard(for_admin=False, lang=lang),
            parse_mode="HTML"
        )
    except Exception:
        await call.message.answer(
            t("genres_title", lang),
            reply_markup=kb.genres_inline_keyboard(for_admin=False, lang=lang),
            parse_mode="HTML"
        )
    await call.answer()

@dp.callback_query(F.data.startswith("genre:"))
async def cb_genre_movies(call: CallbackQuery):
    lang = await db.get_user_lang(call.from_user.id)
    genre = call.data.split(":", 1)[1]
    movies = await db.get_movies_by_genre(genre)
    if not movies:
        await call.answer(t("genre_empty", lang, genre=genre), show_alert=True)
        return
    await call.message.edit_text(
        t("genre_list", lang, genre=genre, cnt=len(movies)),
        reply_markup=kb.movies_list_inline(movies, "🎬", lang=lang, query=genre),
        parse_mode="HTML"
    )

@dp.message(F.text.in_(b_vals("top")))
async def show_top_movies(message: Message):
    lang = await db.get_user_lang(message.from_user.id)
    movies = await db.get_top_movies(10)
    if not movies:
        await message.answer(t("db_empty", lang))
        return
    await message.answer(
        t("top_title", lang),
        reply_markup=kb.movies_list_inline(movies, "🔥", lang=lang, query="top"),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "nav:top")
async def cb_nav_top(call: CallbackQuery):
    lang = await db.get_user_lang(call.from_user.id)
    movies = await db.get_top_movies(10)
    if not movies:
        await call.answer(t("db_empty", lang), show_alert=True)
        return
    try:
        await call.message.edit_text(
            t("top_title", lang),
            reply_markup=kb.movies_list_inline(movies, "🔥", lang=lang, query="top"),
            parse_mode="HTML"
        )
    except Exception:
        await call.message.answer(
            t("top_title", lang),
            reply_markup=kb.movies_list_inline(movies, "🔥", lang=lang, query="top"),
            parse_mode="HTML"
        )
    await call.answer()

@dp.message(F.text.in_(b_vals("new")))
async def show_latest_movies(message: Message):
    lang = await db.get_user_lang(message.from_user.id)
    movies = await db.get_latest_movies(10)
    if not movies:
        await message.answer(t("db_empty", lang))
        return
    await message.answer(
        t("new_title", lang),
        reply_markup=kb.movies_list_inline(movies, "🆕", lang=lang, query="new"),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "nav:new")
async def cb_nav_new(call: CallbackQuery):
    lang = await db.get_user_lang(call.from_user.id)
    movies = await db.get_latest_movies(10)
    if not movies:
        await call.answer(t("db_empty", lang), show_alert=True)
        return
    try:
        await call.message.edit_text(
            t("new_title", lang),
            reply_markup=kb.movies_list_inline(movies, "🆕", lang=lang, query="new"),
            parse_mode="HTML"
        )
    except Exception:
        await call.message.answer(
            t("new_title", lang),
            reply_markup=kb.movies_list_inline(movies, "🆕", lang=lang, query="new"),
            parse_mode="HTML"
        )
    await call.answer()

@dp.message(F.text.in_(b_vals("serials")))
async def show_serials_catalog(message: Message):
    lang = await db.get_user_lang(message.from_user.id)
    serials = await db.get_serials_list(20)
    if not serials:
        await message.answer(t("serials_empty", lang))
        return
    await message.answer(
        t("serials_title", lang, cnt=len(serials)),
        reply_markup=kb.movies_list_inline(serials, "🎞", lang=lang, query="serial"),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "nav:serials")
async def cb_nav_serials(call: CallbackQuery):
    lang = await db.get_user_lang(call.from_user.id)
    serials = await db.get_serials_list(20)
    if not serials:
        await call.answer(t("serials_empty", lang), show_alert=True)
        return
    try:
        await call.message.edit_text(
            t("serials_title", lang, cnt=len(serials)),
            reply_markup=kb.movies_list_inline(serials, "🎞", lang=lang, query="serial"),
            parse_mode="HTML"
        )
    except Exception:
        await call.message.answer(
            t("serials_title", lang, cnt=len(serials)),
            reply_markup=kb.movies_list_inline(serials, "🎞", lang=lang, query="serial"),
            parse_mode="HTML"
        )
    await call.answer()

@dp.message(F.text.in_(b_vals("random")))
async def random_movie_cmd(message: Message):
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    unsubscribed = await check_subscriptions(user_id)
    if unsubscribed:
        await message.answer(t("sub_first", lang), reply_markup=kb.subscription_keyboard(unsubscribed, lang=lang), parse_mode="HTML")
        return
    movie = await db.get_random_movie()
    if not movie:
        await message.answer(t("db_empty", lang))
        return
    await send_movie_card(message, user_id, movie["code"])

@dp.callback_query(F.data == "nav:random")
async def cb_nav_random(call: CallbackQuery):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    unsubscribed = await check_subscriptions(user_id)
    if unsubscribed:
        await call.message.answer(t("sub_first", lang), reply_markup=kb.subscription_keyboard(unsubscribed, lang=lang), parse_mode="HTML")
        await call.answer()
        return
    movie = await db.get_random_movie()
    if not movie:
        await call.answer(t("db_empty", lang), show_alert=True)
        return
    await call.answer("🎲 Tasodifiy kino!" if lang != "ru" else "🎲 Случайный фильм!")
    await send_movie_card(call, user_id, movie["code"])

@dp.message(F.text.in_(b_vals("favs")))
async def show_favorites(message: Message):
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    favs = await db.get_user_favorites(user_id)
    history = await db.get_user_history(user_id, 5)

    if not favs and not history:
        await message.answer(t("favs_empty", lang), parse_mode="HTML")
        return

    if favs:
        await message.answer(
            t("favs_title", lang, cnt=len(favs)),
            reply_markup=kb.movies_list_inline(favs, "⭐", lang=lang),
            parse_mode="HTML"
        )
    if history:
        await message.answer(
            t("history_title", lang),
            reply_markup=kb.movies_list_inline(history, "🕓", lang=lang),
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "nav:favs")
async def cb_nav_favs(call: CallbackQuery):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    favs = await db.get_user_favorites(user_id)
    history = await db.get_user_history(user_id, 5)

    if not favs and not history:
        await call.answer("⭐ Sevimlilar bo'sh!" if lang != "ru" else "⭐ Избранное пусто!", show_alert=True)
        return

    await call.answer()
    if favs:
        await call.message.answer(
            t("favs_title", lang, cnt=len(favs)),
            reply_markup=kb.movies_list_inline(favs, "⭐", lang=lang),
            parse_mode="HTML"
        )
    if history:
        await call.message.answer(
            t("history_title", lang),
            reply_markup=kb.movies_list_inline(history, "🕓", lang=lang),
            parse_mode="HTML"
        )


# ===================== KINO BUYURTMA (LIMIT BILAN + GURUHNING BUYURTMALAR BO'LIMIGA YUBORISH) =====================
async def start_movie_order_flow(target, user_id: int, state: FSMContext):
    lang = await db.get_user_lang(user_id)
    is_vip = await db.is_user_premium(user_id)
    free_lim = int(await db.get_setting("free_order_limit", "1"))
    vip_lim = int(await db.get_setting("premium_order_limit", "5"))

    allowed_limit = vip_lim if is_vip else free_lim
    used_today = await db.get_user_today_orders_count(user_id)
    msg_obj = target.message if isinstance(target, CallbackQuery) else target

    if used_today >= allowed_limit:
        if lang == "ru":
            if is_vip:
                await msg_obj.answer(
                    f"⚠️ <b>Вы полностью использовали свой дневной лимит заказов ({used_today}/{vip_lim} шт.)!</b>\n"
                    f"Завтра вы снова сможете заказывать фильмы.",
                    parse_mode="HTML"
                )
            else:
                await msg_obj.answer(
                    f"⚠️ <b>Дневной лимит исчерпан ({used_today}/{free_lim} шт.)!</b>\n\n"
                    f"👤 Обычные пользователи могут заказывать <b>{free_lim} фильм в день</b>.\n"
                    f"💎 Пользователи <b>Premium (VIP)</b> могут заказывать до <b>{vip_lim} фильмов в день</b>!\n\n"
                    f"👉 <i>Для увеличения лимита перейдите в «💎 Магазин Premium (VIP)».</i>",
                    parse_mode="HTML"
                )
        else:
            if is_vip:
                await msg_obj.answer(
                    f"⚠️ <b>Siz bugungi kunlik buyurtma limitingizdan ({used_today}/{vip_lim} ta) to'liq foydalandingiz!</b>\n"
                    f"Ertaga yana yangi kinolar buyurtma qilishingiz mumkin.",
                    parse_mode="HTML"
                )
            else:
                await msg_obj.answer(
                    f"⚠️ <b>Kunlik limit tugadi ({used_today}/{free_lim} ta)!</b>\n\n"
                    f"👤 Oddiy foydalanuvchilar kuniga faqat <b>{free_lim} dona</b> kino buyurtma qila oladi.\n"
                    f"💎 <b>Premium (VIP)</b> foydalanuvchilar esa kuniga <b>{vip_lim} tagacha</b> kino buyurtma qila oladi!\n\n"
                    f"👉 <i>Limitni oshirish uchun «💎 Premium (VIP) Do'kon» bo'limiga o'ting.</i>",
                    parse_mode="HTML"
                )
        return

    await state.set_state(OrderState.movie_name)
    if lang == "ru":
        status_str = f"💎 Лимит VIP: {used_today + 1}/{vip_lim}" if is_vip else f"👤 Обычный лимит: {used_today + 1}/{free_lim}"
        prompt = (
            f"🎬 <b>Заказ фильма ({status_str}):</b>\n\n"
            f"Напишите название (и год) фильма или сериала, который вы ищете:"
        )
    else:
        status_str = f"💎 VIP Limit: {used_today + 1}/{vip_lim}" if is_vip else f"👤 Oddiy Limit: {used_today + 1}/{free_lim}"
        prompt = (
            f"🎬 <b>Kino buyurtma qilish ({status_str}):</b>\n\n"
            f"Qidirayotgan kino yoki serialingiz nomini (va yilini) yozib yuboring:"
        )
    await msg_obj.answer(prompt, reply_markup=kb.cancel_keyboard(lang), parse_mode="HTML")

@dp.message(F.text.in_(b_vals("order")))
async def order_movie_start(message: Message, state: FSMContext):
    await start_movie_order_flow(message, message.from_user.id, state)

@dp.callback_query(F.data == "nav:order")
async def cb_nav_order(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await start_movie_order_flow(call, call.from_user.id, state)

@dp.message(OrderState.movie_name)
async def order_movie_process(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    role = await db.get_user_role(user_id)
    is_vip = await db.is_user_premium(user_id)
    movie_name = message.text.strip()

    prefix = "💎 [VIP] " if is_vip else ""
    order_id = await db.create_order(
        user_id=user_id,
        full_name=f"{prefix}{message.from_user.full_name or 'User'}",
        username=message.from_user.username or "",
        movie_name=movie_name
    )

    # Mavzuli guruhning «⭐ Задавленный Buyurtmalar» (thread_id=193) bo'limiga ham yuboramiz!
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        await bot.send_message(
            chat_id=int(config.MAIN_TOPIC_GROUP_ID),
            message_thread_id=config.TOPIC_ORDERS_ID,
            text=(
                f"⭐ <b>YANGI KINO BUYURTMA #{order_id}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Buyurtmachi:</b> {prefix}{message.from_user.full_name} (<code>{user_id}</code>)\n"
                f"🎬 <b>Kino nomi:</b> <b>{movie_name}</b>\n"
                f"🕒 <b>Vaqt:</b> <code>{now_str}</code>"
            ),
            reply_markup=kb.order_admin_keyboard(order_id, user_id),
            parse_mode="HTML"
        )
    except Exception:
        pass

    if lang == "ru":
        msg = (
            f"✅ <b>Ваш заказ (#{order_id}) принят!</b>\n\n"
            f"🎬 Фильм: <b>{movie_name}</b>\n"
            f"Заказ также опубликован в разделе <b>⭐ Buyurtmalar</b> нашей группы. Администраторы скоро добавят фильм!"
        )
    else:
        msg = (
            f"✅ <b>Buyurtmangiz (#{order_id}) qabul qilindi!</b>\n\n"
            f"🎬 Kino: <b>{movie_name}</b>\n"
            f"Buyurtmangiz guruhning <b>⭐ Buyurtmalar</b> bo'limiga ham joylandi. Adminlarimiz kinoni bazaga joylab javob yuborishadi!"
        )
    await message.answer(msg, reply_markup=kb.user_main_keyboard(role, lang=lang), parse_mode="HTML")

@dp.message(F.text.in_(b_vals("cabinet")))
async def user_cabinet(message: Message):
    b_uname = await get_bot_username()
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    user = await db.get_user(user_id) or {}
    is_vip = await db.is_user_premium(user_id)
    favs = await db.get_user_favorites(user_id)
    hist = await db.get_user_history(user_id, 100)
    top_refs = await db.get_top_referrers(5)

    ref_link = f"https://t.me/{b_uname}?start=ref_{user_id}"
    ref_count = user.get("ref_count", 0)
    bal = user.get("balance", 0)
    earned = user.get("total_earned", 0)
    streak = user.get("daily_streak", 0)
    vip_tag = user.get("vip_tag", "PREMIUM")
    until = (user.get("premium_until") or "")[:10]

    if lang == "ru":
        top_txt = ""
        if top_refs:
            top_txt = "\n<blockquote>🏆 <b>Топ-5 лидеров по приглашениям:</b>\n"
            for i, r in enumerate(top_refs, 1):
                t_b = f" [{r.get('vip_tag', 'PREMIUM')}]" if r.get("is_premium") else ""
                top_txt += f"{i}. {r['full_name']}{t_b} — <b>{r['ref_count']} чел.</b> ({r.get('balance', 0):,} сум)\n"
            top_txt += "</blockquote>\n"

        vip_line = f"💎 VIP Активен [{vip_tag}] (до {until})" if is_vip else "👤 Обычный пользователь"
        text = (
            f"👤 <b>ВАШ ЛИЧНЫЙ ПРОФИЛЬ</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>Chat ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Имя:</b> {message.from_user.full_name}\n"
            f"🌐 <b>Язык интерфейса:</b> 🇷🇺 Русский\n"
            f"🎖 <b>Статус:</b> {vip_line}\n\n"
            f"<blockquote>"
            f"💰 <b>Баланс:</b> <code>{bal:,}</code> сум (Всего: {earned:,} сум)\n"
            f"🔥 <b>Серия посещений:</b> {streak} / 7 дней\n"
            f"⭐ <b>В избранном:</b> {len(favs)} шт. • 👁 <b>Просмотрено:</b> {len(hist)} шт.\n"
            f"👥 <b>Приглашено друзей:</b> {ref_count} чел."
            f"</blockquote>\n"
            f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{ref_link}</code>\n"
            f"{top_txt}"
        )
        share_btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📲 Поделиться с друзьями",
                url=f"https://t.me/share/url?url={ref_link}&text=🎬 Лучший бот фильмов и сериалов! Присоединяйтесь!"
            )],
            [
                InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="claim_daily"),
                InlineKeyboardButton(text="💎 Магазин VIP", callback_data="open_vip_shop")
            ],
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek tiliga o'tish", callback_data="set_lang:uz")
            ],
            [
                InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_main_menu")
            ]
        ])
    else:
        top_txt = ""
        if top_refs:
            top_txt = "\n<blockquote>🏆 <b>Top-5 faol taklifchilar:</b>\n"
            for i, r in enumerate(top_refs, 1):
                t_b = f" [{r.get('vip_tag', 'PREMIUM')}]" if r.get("is_premium") else ""
                top_txt += f"{i}. {r['full_name']}{t_b} — <b>{r['ref_count']} ta</b> ({r.get('balance', 0):,} so'm)\n"
            top_txt += "</blockquote>\n"

        vip_line = f"💎 VIP Faol [{vip_tag}] ({until} gacha)" if is_vip else "👤 Oddiy foydalanuvchi"
        text = (
            f"👤 <b>SHAXSIY PROFILINGIZ</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>Chat ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Ismingiz:</b> {message.from_user.full_name}\n"
            f"🌐 <b>Tanlangan til:</b> 🇺🇿 O'zbek tili\n"
            f"🎖 <b>Maqomingiz:</b> {vip_line}\n\n"
            f"<blockquote>"
            f"💰 <b>Joriy balans:</b> <code>{bal:,}</code> so'm (Jami: {earned:,} so'm)\n"
            f"🔥 <b>Kunlik Streak:</b> {streak} / 7 kun\n"
            f"⭐ <b>Saqlangan kinolar:</b> {len(favs)} ta • 👁 <b>Ko'rilgan:</b> {len(hist)} ta\n"
            f"👥 <b>Taklif etilgan do'stlar:</b> {ref_count} nafar"
            f"</blockquote>\n"
            f"🔗 <b>Shaxsiy taklif havolangiz:</b>\n<code>{ref_link}</code>\n"
            f"{top_txt}"
        )
        share_btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📲 Do'stlarga ulashish",
                url=f"https://t.me/share/url?url={ref_link}&text=🎬 Eng zo'r kinolar va seriallar botiga qo'shiling!"
            )],
            [
                InlineKeyboardButton(text="🎁 Kunlik Bonus olish", callback_data="claim_daily"),
                InlineKeyboardButton(text="💎 VIP Do'kon", callback_data="open_vip_shop")
            ],
            [
                InlineKeyboardButton(text="🇷🇺 Перейти на Русский язык", callback_data="set_lang:ru")
            ],
            [
                InlineKeyboardButton(text="🔙 Asosiy menyuga qaytish", callback_data="back_main_menu")
            ]
        ])
    await message.answer(text, reply_markup=share_btn, parse_mode="HTML")


# ===================== KINO INTERAKTIV CALLBACKLARI =====================
@dp.callback_query(F.data.startswith("open:"))
async def cb_open_movie(call: CallbackQuery):
    code = call.data.split(":", 1)[1]
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    unsubscribed = await check_subscriptions(user_id)
    if unsubscribed:
        await call.message.answer(t("sub_first", lang), reply_markup=kb.subscription_keyboard(unsubscribed, code, lang=lang), parse_mode="HTML")
        await call.answer()
        return
    await call.answer("🎬 Загрузка..." if lang == "ru" else "🎬 Kino kartasi ochilmoqda...")
    await send_movie_card(call, user_id, code)

@dp.callback_query(F.data.startswith("watch:"))
async def cb_watch_movie_or_episode(call: CallbackQuery):
    """
    Poster Card ostidagi «▶️ Kino ko'rish» yoki «1, 2, 3, 4, 5...» qism tugmasi bosilganda
    haqiqiy videoni yuboradi!
    """
    parts = call.data.split(":")
    code = parts[1]
    ep_num = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    unsubscribed = await check_subscriptions(user_id)
    if unsubscribed:
        await call.message.answer(t("sub_first", lang), reply_markup=kb.subscription_keyboard(unsubscribed, code, lang=lang), parse_mode="HTML")
        await call.answer()
        return
    await call.answer("▶️ Видео отправляется..." if lang == "ru" else "▶️ Kino videosi yuborilmoqda...")
    await send_movie_video(call, user_id, code, ep_num=ep_num)

@dp.callback_query(F.data.startswith("eppage:"))
async def cb_poster_episode_page(call: CallbackQuery):
    """Ko'p qismli serial/kinoda qismlar sahifasini (1..30, 31..60...) almashtirish."""
    b_uname = await get_bot_username()
    _, code, page_str = call.data.split(":")
    page = int(page_str) if page_str.isdigit() else 1
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        await call.answer("Kino topilmadi!")
        return
    is_fav = await db.is_favorite(user_id, code)
    user_rating = await db.get_user_movie_rating(user_id, code)
    user_perms = await db.get_user_permissions(user_id)
    episodes = await db.get_episodes(code)
    markup = kb.movie_poster_card_keyboard(
        movie=movie,
        bot_username=b_uname,
        is_fav=is_fav,
        episodes=episodes,
        user_perms=user_perms,
        lang=lang,
        user_rating=user_rating,
        ep_page=page
    )
    try:
        await call.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        pass
    await call.answer(f"📄 Sahifa {page}")

@dp.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()

@dp.callback_query(F.data.startswith("ep:"))
async def cb_switch_episode(call: CallbackQuery):
    b_uname = await get_bot_username()
    _, code, ep_str = call.data.split(":")
    ep_num = int(ep_str)
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)

    movie = await db.get_movie(code, increment_view=False)
    ep_obj = await db.get_episode(code, ep_num)
    if not movie or not ep_obj:
        await call.answer("❌ Серия не найдена!" if lang == "ru" else "❌ Qism topilmadi!", show_alert=True)
        return

    protect_val = await db.get_setting("protect_content", "1")
    protect = (str(protect_val) == "1")

    if protect:
        await call.answer(f"🎞 {ep_num}-серия..." if lang == "ru" else f"🎞 {ep_num}-qism yuklanmoqda...")
        try:
            await call.message.delete()
        except Exception:
            pass
        await send_movie_card(call, user_id, code, ep_num=ep_num)
        return

    episodes = await db.get_episodes(code)
    is_fav = await db.is_favorite(user_id, code)
    user_rating = await db.get_user_movie_rating(user_id, code)
    user_perms = await db.get_user_permissions(user_id)

    caption = format_movie_caption(movie, b_uname, current_ep=ep_num, protect=protect, lang=lang)
    markup = kb.movie_action_keyboard(movie, b_uname, is_fav, episodes, ep_num, user_perms, lang=lang, user_rating=user_rating)

    try:
        await call.message.edit_media(
            media=InputMediaVideo(media=ep_obj["file_id"], caption=caption, parse_mode="HTML"),
            reply_markup=markup
        )
        await call.answer(f"🎞 {ep_num}")
    except Exception:
        await call.answer(f"🎞 {ep_num}")
        await send_movie_card(call, user_id, code, ep_num=ep_num)

@dp.callback_query(F.data.startswith("rate:"))
async def cb_rate_movie_stars(call: CallbackQuery):
    """5 talik yulduzcha (⭐ 1 .. ⭐ 5) bilan kinoni baholash."""
    b_uname = await get_bot_username()
    _, code, stars_str = call.data.split(":")
    stars = int(stars_str)
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)

    res = await db.rate_movie_stars(user_id, code, stars)
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        await call.answer("Kino topilmadi")
        return

    is_fav = await db.is_favorite(user_id, code)
    episodes = await db.get_episodes(code)
    user_perms = await db.get_user_permissions(user_id)
    protect_val = await db.get_setting("protect_content", "1")
    protect = (str(protect_val) == "1")

    caption = format_movie_caption(movie, b_uname, current_ep=None, protect=protect, lang=lang)
    markup = kb.movie_action_keyboard(movie, b_uname, is_fav, episodes, 1, user_perms, lang=lang, user_rating=stars)
    try:
        await call.message.edit_caption(caption=caption, reply_markup=markup, parse_mode="HTML")
    except Exception:
        try:
            await call.message.edit_reply_markup(reply_markup=markup)
        except Exception:
            pass

    if lang == "ru":
        msg = f"🌟 Вы оценили на {stars}/5! Средний рейтинг: ⭐ {res['avg']}/5 ({res['count']} гол.)"
    else:
        msg = f"🌟 Siz {stars}/5 yulduz bilan baholadingiz! O'rtacha reyting: ⭐ {res['avg']}/5 ({res['count']} ovoz)"
    await call.answer(msg, show_alert=True)

@dp.callback_query(F.data.startswith("react:"))
async def cb_react_movie(call: CallbackQuery):
    b_uname = await get_bot_username()
    _, r_type, code = call.data.split(":")
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)

    await db.react_movie(user_id, code, r_type)
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        await call.answer("Kino topilmadi")
        return

    is_fav = await db.is_favorite(user_id, code)
    user_rating = await db.get_user_movie_rating(user_id, code)
    episodes = await db.get_episodes(code)
    user_perms = await db.get_user_permissions(user_id)

    markup = kb.movie_action_keyboard(movie, b_uname, is_fav, episodes, 1, user_perms, lang=lang, user_rating=user_rating)
    try:
        await call.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        pass
    await call.answer()

@dp.callback_query(F.data.startswith("fav:"))
async def cb_toggle_fav(call: CallbackQuery):
    b_uname = await get_bot_username()
    code = call.data.split(":", 1)[1]
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    added = await db.toggle_favorite(user_id, code)

    movie = await db.get_movie(code, increment_view=False)
    user_rating = await db.get_user_movie_rating(user_id, code)
    episodes = await db.get_episodes(code)
    user_perms = await db.get_user_permissions(user_id)

    if movie:
        markup = kb.movie_action_keyboard(movie, b_uname, added, episodes, 1, user_perms, lang=lang, user_rating=user_rating)
        try:
            await call.message.edit_reply_markup(reply_markup=markup)
        except Exception:
            pass

    if lang == "ru":
        await call.answer("⭐ Добавлено в избранное!" if added else "🗑 Удалено из избранного!")
    else:
        await call.answer("⭐ Sevimlilarga saqlandi!" if added else "🗑 Sevimlilardan o'chirildi!")


# ===================== INLINE AVTO-QIDIRUV (1-RASMDAGI TMDB POSTERLAR VA TO'LIQ MA'LUMOTLAR BILAN) =====================
DEFAULT_INLINE_POSTER_THUMB = "https://img.icons8.com/fluency/240/cinema---v1.png"

@dp.inline_query()
async def inline_movie_search(inline_query: InlineQuery):
    """
    @movieeland_bot kiritilganda yoki 3-rasmdagi «🔍 Inline rejimda (Rasmli Ro'yxat) qidirish»
    tugmasi bosilganda:
    Har bir kinoning 1-rasmdagi TheMovieDB (themoviedb.org) posteri, nomi, yili, davlati,
    sifati, janri va reytingi bilan avtomatik chiqaradi!
    """
    b_uname = await get_bot_username()
    q = (inline_query.query or "").strip()
    offset = int(inline_query.offset) if (inline_query.offset or "").isdigit() else 0
    page_size = 25

    q_low = q.lower()
    if not q:
        all_items, _ = await db.get_movies_paginated(offset=offset, limit=page_size)
        movies = all_items
        has_more = len(all_items) == page_size
    elif q_low in ("top", "🔥", "🔥 top"):
        movies = await db.get_top_movies(30)
        has_more = False
    elif q_low in ("new", "yangi", "🆕"):
        movies = await db.get_latest_movies(30)
        has_more = False
    elif q_low in ("serial", "seriallar", "🎞"):
        movies = await db.get_serials_list(30)
        has_more = False
    elif q_low in ("fav", "⭐"):
        movies = await db.get_user_favorites(inline_query.from_user.id)
        has_more = False
    elif any(q_low == g.lower() for g in config.GENRES):
        movies = await db.get_movies_by_genre(q, limit=30)
        has_more = False
    elif q.lstrip("#").isdigit():
        exact_m = await db.get_movie(q.lstrip("#"), increment_view=False)
        searched = await db.search_movies_by_name(q, limit=25)
        movies = ([exact_m] if exact_m else []) + [m for m in searched if not exact_m or m["code"] != exact_m["code"]]
        has_more = False
    else:
        movies = await db.search_movies_by_name(q, limit=30)
        has_more = False

    results = []
    for m in movies[:page_size]:
        code = str(m["code"])
        rating = m.get("imdb", "8.4")
        year = m.get("year", "2024")
        country = m.get("country", "AQSH")
        quality = m.get("quality", "1080p Full HD")
        genre = m.get("genre", "🔥 Jangari")
        views = m.get("views", 0)
        badge = "📺" if m.get("is_serial") else "🎬"

        raw_photo = (m.get("photo_id") or "").strip()
        if raw_photo.startswith("https://image.tmdb.org/t/p/w780/"):
            thumb_url = raw_photo.replace("/w780/", "/w342/")
        elif raw_photo.startswith("http://") or raw_photo.startswith("https://"):
            thumb_url = raw_photo
        else:
            thumb_url = DEFAULT_INLINE_POSTER_THUMB

        title = f"{badge} #{code} — {m['name']} ({year})"
        desc = f"⭐ {rating} | 🌏 {country} | 📀 {quality}\n{genre} | 👁 {views}"
        deep_link = f"https://t.me/{b_uname}?start={code}"

        poster_hidden_link = f"<a href='{raw_photo}'>&#8205;</a>" if raw_photo.startswith("http") else ""
        text_content = (
            f"{badge} <b>#{code} — {m['name']} ({year})</b>{poster_hidden_link}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌏 <b>Davlati:</b> {country}\n"
            f"📅 <b>Yili:</b> {year}\n"
            f"📀 <b>Sifati:</b> {quality}\n"
            f"🎞 <b>Janri:</b> {genre}\n"
            f"🇺🇿 <b>Tili:</b> {m.get('language', 'O‘zbek tilida')}\n"
            f"⭐ <b>Reyting:</b> {rating} / 10\n"
            f"🔢 <b>Kino kodi:</b> <code>{code}</code>\n\n"
            f"📢 <b>Kanal:</b> @movieee_land | 🤖 @{b_uname}"
        )
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"▶️ Kinoni tomosha qilish (Kod: {code})", url=deep_link)]
        ])
        results.append(
            InlineQueryResultArticle(
                id=f"mov_{code}",
                title=title,
                description=desc,
                thumbnail_url=thumb_url,
                thumbnail_width=342,
                thumbnail_height=513,
                input_message_content=InputTextMessageContent(message_text=text_content, parse_mode="HTML"),
                reply_markup=btn
            )
        )

    next_off = str(offset + page_size) if has_more else ""
    await inline_query.answer(results, cache_time=1, is_personal=True, next_offset=next_off)


# ===================== KINO VA SERIAL QO'SHISH =====================
@dp.message(F.text == "➕ Kino qo'shish (Pro)")
async def pro_movie_start(message: Message, state: FSMContext):
    if not await db.has_permission(message.from_user.id, "add_movie"):
        await message.answer("⛔ Sizda kino qo'shish huquqi yo'q!")
        return
    next_code = await db.get_next_auto_code()
    await state.set_state(ProMovieState.code)
    await message.answer(
        f"🎬 <b>Pro Kino Qo'shish:</b>\n\n"
        f"Kino uchun <b>kod</b> kiriting (yoki avtomatik <code>{next_code}</code> kodini berish uchun «⏭ O'tkazib yuborish» ni bosing):",
        reply_markup=kb.skip_or_cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(ProMovieState.code)
async def pro_movie_code(message: Message, state: FSMContext):
    if message.text == "⏭ O'tkazib yuborish":
        code = await db.get_next_auto_code()
    else:
        code = message.text.strip().lstrip("#")
        if await db.get_movie(code, increment_view=False):
            await message.answer("⚠️ Bu kodli kino mavjud! Boshqa kod yozing:")
            return
    await state.update_data(code=code)
    await state.set_state(ProMovieState.name)
    await message.answer(f"✅ Kino kodi: <b>#{code}</b>\n\nEndi kino <b>nomini</b> yozing:", reply_markup=kb.cancel_keyboard(), parse_mode="HTML")

@dp.message(ProMovieState.name)
async def pro_movie_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ProMovieState.genre)
    await message.answer("🎭 Kino <b>janrini</b> tanlang:", reply_markup=kb.genres_inline_keyboard(for_admin=True), parse_mode="HTML")

@dp.callback_query(ProMovieState.genre, F.data.startswith("adm_genre:"))
async def pro_movie_genre_cb(call: CallbackQuery, state: FSMContext):
    genre = call.data.split(":", 1)[1]
    await state.update_data(genre=genre)
    await state.set_state(ProMovieState.details)
    g_lbl = "🤖 AI avtomatik aniqlaydi" if genre == "auto" else genre
    await call.message.edit_text(f"✅ Tanlangan janr: <b>{g_lbl}</b>", parse_mode="HTML")
    await call.message.answer(
        "📅 Kino <b>Yili | Davlati | Tili | IMDb</b> ma'lumotlarini yuboring:\n"
        "<code>2024 | AQSH | O'zbek tilida | 8.5</code>\n\n"
        "<i>Yoki AI o'zi kino nomidan topib to'ldirishi uchun «⏭ O'tkazib yuborish» ni bosing:</i>",
        reply_markup=kb.skip_or_cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(ProMovieState.genre)
async def pro_movie_genre_txt(message: Message, state: FSMContext):
    g_val = "auto" if message.text == "⏭ O'tkazib yuborish" else message.text.strip()
    await state.update_data(genre=g_val)
    await state.set_state(ProMovieState.details)
    await message.answer(
        "📅 Kino <b>Yili | Davlati | Tili | IMDb</b> ma'lumotlarini yuboring (yoki AI o'zi topishi uchun «⏭ O'tkazib yuborish»):",
        reply_markup=kb.skip_or_cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(ProMovieState.details)
async def pro_movie_details(message: Message, state: FSMContext):
    year, country, lang, imdb = "", "", "O'zbek tilida", "8.2"
    if message.text != "⏭ O'tkazib yuborish":
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) >= 1 and parts[0]: year = parts[0]
        if len(parts) >= 2 and parts[1]: country = parts[1]
        if len(parts) >= 3 and parts[2]: lang = parts[2]
        if len(parts) >= 4 and parts[3]: imdb = parts[3]

    await state.update_data(year=year, country=country, language=lang, imdb=imdb)
    await state.set_state(ProMovieState.quality)
    await message.answer("💿 Kino <b>sifatini</b> tanlang:", reply_markup=kb.quality_inline_keyboard(), parse_mode="HTML")

@dp.callback_query(ProMovieState.quality, F.data.startswith("adm_qual:"))
async def pro_movie_quality_cb(call: CallbackQuery, state: FSMContext):
    qual = call.data.split(":", 1)[1]
    await state.update_data(quality=qual)
    await state.set_state(ProMovieState.video)
    q_lbl = "🤖 AI avtomatik aniqlaydi" if qual == "auto" else qual
    await call.message.edit_text(f"✅ Sifat: <b>{q_lbl}</b>", parse_mode="HTML")
    await call.message.answer(
        "🎥 Endi kinoni <b>Arxiv kanaldan (-1003124847141) Forward</b> qiling yoki video faylni yuboring:",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(ProMovieState.video, F.video | F.document)
async def pro_movie_video(message: Message, state: FSMContext):
    v_obj = message.video or message.document
    file_id = v_obj.file_id
    file_name = getattr(v_obj, "file_name", "") or ""
    video_height = getattr(v_obj, "height", 0) or 0
    await state.update_data(file_id=file_id, file_name=file_name, video_height=video_height)
    await state.set_state(ProMovieState.caption)
    await message.answer(
        "📝 Kino uchun <b>tavsif (description)</b> yozing (yoki AI o'zi yozishi uchun «⏭ O'tkazib yuborish» ni bosing):",
        reply_markup=kb.skip_or_cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(ProMovieState.caption)
async def pro_movie_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    raw_caption = "" if message.text == "⏭ O'tkazib yuborish" else message.text.strip()

    # AI yordamida faqat kino nomi yozilgan bo'lsa ham yili, davlati, janri, sifati va tavsifini avtomatik to'ldiramiz!
    ai_meta = await ai_service.enrich_movie_metadata_with_ai(
        raw_text=f"🎬 Nomi: {data['name']}\n{raw_caption}",
        file_name=data.get("file_name", ""),
        video_height=data.get("video_height", 0)
    )

    final_name = ai_meta["name"] if ai_meta.get("name") and ai_meta["name"] != "Yangi Kino" else data["name"]
    final_genre = ai_meta["genre"] if data.get("genre") in (None, "", "auto") else data["genre"]
    final_year = data.get("year") or ai_meta.get("year", "2024")
    final_country = data.get("country") or ai_meta.get("country", "AQSH")
    final_quality = ai_meta["quality"] if data.get("quality") in (None, "", "auto") else data["quality"]
    final_caption = raw_caption if raw_caption else ai_meta["caption"]

    poster_url = await ai_service.find_movie_poster_tmdb(
        name=final_name,
        year=str(final_year),
        is_serial=False,
        force=True
    )

    await db.add_movie(
        code=data["code"],
        name=final_name,
        file_id=data["file_id"],
        genre=final_genre,
        year=final_year,
        country=final_country,
        language=data.get("language", "O'zbek tilida"),
        quality=final_quality,
        imdb=data.get("imdb", "8.2"),
        photo_id=poster_url,
        caption=final_caption
    )
    await state.clear()
    perms = await db.get_user_permissions(message.from_user.id)
    role = await db.get_user_role(message.from_user.id)
    await message.answer(
        f"🎉 <b>Kino AI yordamida to'liq ma'lumotlari bilan saqlandi!</b>\n"
        f"🎬 Nomi: <b>{final_name}</b> ({final_year}, {final_country})\n"
        f"🎞 Janri: <b>{final_genre}</b> | 📀 Sifati: <b>{final_quality}</b>\n"
        f"🔢 Kodi: <code>{data['code']}</code>",
        reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")),
        parse_mode="HTML"
    )
    await send_movie_card(message, message.from_user.id, data["code"])


# ===================== FAQAT ARXIV KANALDAN (-1003124847141) FORWARD QILINGANDA QO'SHISH =====================
def get_forward_channel_id(message: Message) -> str:
    """Xabar qaysi kanaldan forward qilinganini aniqlaydi."""
    if message.forward_from_chat:
        return str(message.forward_from_chat.id)
    if hasattr(message, "forward_origin") and message.forward_origin:
        origin = message.forward_origin
        if hasattr(origin, "chat") and origin.chat:
            return str(origin.chat.id)
    return ""

@dp.message(FastMovieState.waiting_videos, F.video | F.document)
@fallback_router.message(F.video | F.document)
async def handle_forwarded_archive_video(message: Message):
    """
    1. Agar Movie Land ARXIV (-1003124847141) supergroup/kanalning o'ziga yangi video tashlansa (hatto faqat nomi yozilgan bo'lsa ham) ->
       avtomatik ravishda AI yordamida to'ldirib bazaga qo'shadi!
    2. Agar Admin Arxiv kanaldan (-1003124847141) botga kino forward qilsa ->
       AI yordamida to'ldirib bazaga qo'shadi!
    """
    arch_ch = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    if str(message.chat.id) == str(arch_ch):
        await handle_archive_channel_new_post(message)
        return

    if message.chat.type != "private":
        return
    if not await db.has_permission(message.from_user.id, "add_movie"):
        return

    fwd_ch_id = get_forward_channel_id(message)

    if fwd_ch_id != str(arch_ch):
        await message.reply(
            f"⛔ <b>Rad etildi!</b>\n\n"
            f"Kinolar faqatgina rasmiy <b>Movie Land ARXIV</b> (<code>{arch_ch}</code>) kanalidan <b>Forward</b> qilingandagina bazaga qo'shiladi!",
            parse_mode="HTML"
        )
        return

    v_obj = message.video or message.document
    file_id = v_obj.file_id
    file_name = getattr(v_obj, "file_name", "") or ""
    video_height = getattr(v_obj, "height", 0) or 0
    raw_caption = message.caption or ""
    auto_post = (await db.get_setting("archive_auto_post", "1")) == "1"

    fwd_msg_id = message.forward_from_message_id
    if not fwd_msg_id and hasattr(message, "forward_origin") and hasattr(message.forward_origin, "message_id"):
        fwd_msg_id = message.forward_origin.message_id

    res = await process_archive_item(
        file_id=file_id,
        raw_caption=raw_caption,
        msg_id=fwd_msg_id,
        do_autopost=auto_post,
        file_name=file_name,
        video_height=video_height,
        auto_edit_archive=True
    )

    st = res["status"]
    post_txt = "📢 @movieee_land kanaliga post chiqarildi!" if res.get("posted") else ""

    if st == "episode_added":
        await message.reply(
            f"✅ <b>Serialning yangi qismi ulandi!</b>\n"
            f"🎞 Serial: <b>{res['name']}</b>\n"
            f"🔢 Kodi: <code>{res['code']}</code> | ➕ <b>{res['ep_num']}-qism</b>",
            parse_mode="HTML"
        )
    elif st == "already_exists":
        await message.reply(
            f"ℹ️ <b>Bu kino allaqachon bazada mavjud!</b>\n"
            f"🎬 Nomi: <b>{res['name']}</b> | 🔢 Kodi: <code>{res['code']}</code>",
            parse_mode="HTML"
        )
    else:
        kind = "Serial" if st == "new_serial" else "Kino"
        await message.reply(
            f"✅ <b>Arxivdan {kind} muvaffaqiyatli qo'shildi!</b>\n"
            f"🎬 Nomi: <b>{res['name']}</b>\n"
            f"🔢 Kodi: <code>{res['code']}</code>\n"
            f"{post_txt}",
            parse_mode="HTML"
        )

@dp.message(F.text == "⚡ Tezkor kino qo'shish")
async def fast_movie_start(message: Message, state: FSMContext):
    if not await db.has_permission(message.from_user.id, "add_movie"):
        await message.answer("⛔ Sizda kino qo'shish huquqi yo'q!")
        return
    arch_ch = await db.get_setting("archive_channel_id", config.DEFAULT_ARCHIVE_CHANNEL_ID)
    await state.set_state(FastMovieState.waiting_videos)
    await message.answer(
        f"⚡ <b>Arxiv Forward Rejimi!</b>\n\n"
        f"Rasmiy Arxiv kanaldan (<code>{arch_ch}</code>) kinolarni shu yerga ketma-ket <b>Forward</b> qiling!\n"
        f"Bot avtomatik ravishda:\n"
        f"• 🎬 Nomi, 🌏 Davlati, 📅 Yili, 📀 Sifati, 🎞 Janri, 🇺🇿 Tilini ajratib oladi;\n"
        f"• Serial bo'lsa barcha qismlarni bitta kodga jamlaydi;\n"
        f"• Kino bo'lsa kod berib, @movieee_land kanaliga postini ham chiqaradi!",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "🎞 Serial qismi qo'shish")
async def add_episode_start(message: Message, state: FSMContext):
    if not await db.has_permission(message.from_user.id, "add_movie"):
        await message.answer("⛔ Sizda bu funksiya uchun huquq yo'q!")
        return
    await state.set_state(EpisodeState.movie_code)
    await message.answer("🎞 Qism qo'shmoqchi bo'lgan <b>serial kodini</b> yozing:", reply_markup=kb.cancel_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("addep:"))
async def cb_add_episode_direct(call: CallbackQuery, state: FSMContext):
    if not await db.has_permission(call.from_user.id, "add_movie"):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    code = call.data.split(":", 1)[1]
    episodes = await db.get_episodes(code)
    next_ep = len(episodes) + 1 if episodes else 2
    await state.update_data(movie_code=code, episode_num=next_ep)
    await state.set_state(EpisodeState.video)
    await call.message.answer(
        f"🎞 <b>#{code}</b> serialining <b>{next_ep}-qism</b> videosini yuboring:",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.message(EpisodeState.movie_code)
async def add_episode_code(message: Message, state: FSMContext):
    code = message.text.strip().lstrip("#")
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        await message.answer("❌ Bunday kodli kino topilmadi!")
        return
    episodes = await db.get_episodes(code)
    if not episodes and movie.get("file_id"):
        await db.add_episode(code, 1, movie["file_id"], "1-qism")
        episodes = await db.get_episodes(code)

    next_ep = len(episodes) + 1
    await state.update_data(movie_code=code, episode_num=next_ep)
    await state.set_state(EpisodeState.video)
    await message.answer(f"✅ Serial: <b>{movie['name']}</b>\nEndi <b>{next_ep}-qism</b> videosini yuboring:", parse_mode="HTML")

@dp.message(EpisodeState.video, F.video | F.document)
async def add_episode_video(message: Message, state: FSMContext):
    data = await state.get_data()
    code, ep_num = data["movie_code"], data["episode_num"]
    file_id = message.video.file_id if message.video else message.document.file_id

    await db.add_episode(code, ep_num, file_id)
    await state.clear()
    perms = await db.get_user_permissions(message.from_user.id)
    role = await db.get_user_role(message.from_user.id)
    await message.answer(
        f"✅ <b>#{code}</b> serialiga <b>{ep_num}-qism</b> ulandi!",
        reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")),
        parse_mode="HTML"
    )
    await send_movie_card(message, message.from_user.id, code, ep_num=ep_num)


# ===================== KINO O'CHIRISH VA AVTO-POST =====================
@dp.message(F.text == "🗑 Kino o'chirish")
async def delete_movie_cmd(message: Message, state: FSMContext):
    if not await db.has_permission(message.from_user.id, "del_movie"):
        await message.answer("⛔ Sizda kino o'chirish huquqi yo'q!")
        return
    await state.set_state(DeleteMovieState.code)
    await message.answer("🗑 O'chirmoqchi bo'lgan kino <b>kodini</b> kiriting:", reply_markup=kb.cancel_keyboard(), parse_mode="HTML")

@dp.message(DeleteMovieState.code)
async def delete_movie_proc(message: Message, state: FSMContext):
    code = message.text.strip().lstrip("#")
    ok = await db.delete_movie(code)
    await state.clear()
    perms = await db.get_user_permissions(message.from_user.id)
    role = await db.get_user_role(message.from_user.id)
    await message.answer(
        f"✅ <b>#{code}</b> o'chirildi!" if ok else f"❌ <b>#{code}</b> topilmadi.",
        reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("delmov:"))
async def cb_del_movie_direct(call: CallbackQuery):
    if not await db.has_permission(call.from_user.id, "del_movie"):
        await call.answer("⛔ Sizda kino o'chirish huquqi yo'q!", show_alert=True)
        return
    code = call.data.split(":", 1)[1]
    await db.delete_movie(code)
    await call.message.delete()
    await call.answer(f"🗑 #{code} o'chirildi!", show_alert=True)

@dp.callback_query(F.data.startswith("editpic:"))
async def cb_edit_movie_photo_start(call: CallbackQuery, state: FSMContext):
    if not (await db.has_permission(call.from_user.id, "add_movie") or await db.has_permission(call.from_user.id, "autopost")):
        await call.answer("⛔ Sizda rasm tahrirlash huquqi yo'q!", show_alert=True)
        return
    code = call.data.split(":", 1)[1]
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        await call.answer("Kino topilmadi!", show_alert=True)
        return

    await state.update_data(edit_photo_code=code)
    await state.set_state(EditMoviePhotoState.waiting_photo)
    tmdb_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 TheMovieDB dan avto-poster olish", callback_data=f"tmdb_pic:{code}")]
    ])
    await call.message.answer(
        f"🖼 <b>#{code} — {movie['name']}</b> kinosi uchun yangi rasm (poster) yuboring\n"
        f"yoki quyidagi tugma orqali <b>TheMovieDB</b> dan rasmiy HD posterni 1 klikda oling:",
        reply_markup=tmdb_kb,
        parse_mode="HTML"
    )
    await call.message.answer(
        "👇 Rasmni yuboring (bekor qilish uchun «❌ Bekor qilish»):",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@dp.callback_query(F.data.startswith("tmdb_pic:"))
async def cb_fetch_tmdb_movie_photo(call: CallbackQuery, state: FSMContext):
    if not (await db.has_permission(call.from_user.id, "add_movie") or await db.has_permission(call.from_user.id, "autopost")):
        await call.answer("⛔ Sizda rasm tahrirlash huquqi yo'q!", show_alert=True)
        return
    code = call.data.split(":", 1)[1]
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        await call.answer("Kino topilmadi!", show_alert=True)
        return
    await state.clear()
    poster_url = await ai_service.find_movie_poster_tmdb(
        name=movie["name"],
        year=str(movie.get("year", "")),
        is_serial=bool(movie.get("is_serial")),
        force=True
    )
    if not poster_url:
        await call.answer("⚠️ TheMovieDB dan ushbu nom bo'yicha rasm topilmadi. O'zingiz rasm yuboring.", show_alert=True)
        return

    await db.update_movie_photo(code, poster_url)
    post_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Shu rasm bilan @movieee_land ga Post chiqarish", callback_data=f"autopost_now:{code}")],
        [InlineKeyboardButton(text="🖼 Boshqa rasm yuklash", callback_data=f"editpic:{code}")]
    ])
    await call.message.answer_photo(
        photo=poster_url,
        caption=f"✅ <b>#{code} — {movie['name']}</b> uchun TheMovieDB rasmiy HD posteri saqlandi!",
        reply_markup=post_btn,
        parse_mode="HTML"
    )
    await call.answer("✅ TMDB HD poster saqlandi!")

@dp.message(EditMoviePhotoState.waiting_photo, F.photo)
async def save_edited_movie_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data.get("edit_photo_code")
    await state.clear()

    photo_id = message.photo[-1].file_id
    await db.update_movie_photo(code, photo_id)
    movie = await db.get_movie(code, increment_view=False)
    perms = await db.get_user_permissions(message.from_user.id)
    role = await db.get_user_role(message.from_user.id)

    post_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Shu rasm bilan @movieee_land ga Post chiqarish", callback_data=f"autopost_now:{code}")],
        [InlineKeyboardButton(text="🖼 Rasmni qayta almashtirish", callback_data=f"editpic:{code}")]
    ])
    await message.answer_photo(
        photo=photo_id,
        caption=(
            f"✅ <b>#{code} — {movie['name'] if movie else code}</b> uchun rasm muvaffaqiyatli saqlandi!\n\n"
            f"👇 Endi quyidagi tugmani bosib shu rasm bilan kanalga post chiqarishingiz mumkin:"
        ),
        reply_markup=post_btn,
        parse_mode="HTML"
    )
    await message.answer(
        "Boshqaruv paneli:",
        reply_markup=kb.super_admin_keyboard() if role == "superadmin" else kb.staff_panel_keyboard(perms)
    )

@dp.callback_query(F.data.startswith("autopost:"))
async def cb_autopost_channel(call: CallbackQuery):
    if not await db.has_permission(call.from_user.id, "autopost"):
        await call.answer("⛔ Sizda Avto-Post huquqi yo'q!", show_alert=True)
        return
    code = call.data.split(":", 1)[1]
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        await call.answer("Kino topilmadi!", show_alert=True)
        return

    # Agar kinoga hali rasm biriktirilmagan bo'lsa, avval TheMovieDB dan avtomatik topib biriktiramiz!
    if not movie.get("photo_id"):
        auto_poster = await ai_service.find_movie_poster_tmdb(
            name=movie["name"],
            year=str(movie.get("year", "")),
            is_serial=bool(movie.get("is_serial")),
            force=True
        )
        if auto_poster:
            await db.update_movie_photo(code, auto_poster)
            movie["photo_id"] = auto_poster

    if not movie.get("photo_id"):
        choice_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Avval rasm (poster) qo'shib post chiqarish", callback_data=f"editpic:{code}")],
            [InlineKeyboardButton(text="📢 Rasmsiz hozir kanalga post chiqarish", callback_data=f"autopost_now:{code}")]
        ])
        await call.message.answer(
            f"📢 <b>#{code} — {movie['name']}</b> kinosini kanalga chiqarish:\n\n"
            f"ℹ️ Ushbu kinoga hali rasm (poster) biriktirilmagan. Avval rasm yuklab keyin post chiqarasizmi yoki rasmsiz chiqarilsinmi?",
            reply_markup=choice_kb,
            parse_mode="HTML"
        )
        await call.answer()
        return

    ok = await publish_movie_to_channel(movie)
    if ok:
        await call.answer("✅ @movieee_land kanaliga rasm bilan post muvaffaqiyatli chiqarildi!", show_alert=True)
    else:
        await call.answer("❌ Kanalga post chiqarishda xatolik! Bot kanalda admin ekanligini tekshiring.", show_alert=True)

@dp.callback_query(F.data.startswith("autopost_now:"))
async def cb_autopost_now(call: CallbackQuery):
    if not await db.has_permission(call.from_user.id, "autopost"):
        await call.answer("⛔ Sizda Avto-Post huquqi yo'q!", show_alert=True)
        return
    code = call.data.split(":", 1)[1]
    movie = await db.get_movie(code, increment_view=False)
    if not movie:
        await call.answer("Kino topilmadi!", show_alert=True)
        return

    ok = await publish_movie_to_channel(movie)
    if ok:
        await call.answer("✅ @movieee_land kanaliga post muvaffaqiyatli chiqarildi!", show_alert=True)
    else:
        await call.answer("❌ Kanalga post chiqarishda xatolik! Bot kanalda admin ekanligini tekshiring.", show_alert=True)


# ===================== KANALLAR, BUYURTMALAR, STATISTIKA, BAN, BROADCAST =====================
@dp.message(F.text == "📢 Kanallarni boshqarish")
async def manage_channels_menu(message: Message):
    if not await db.has_permission(message.from_user.id, "channels"):
        await message.answer("⛔ Sizda kanallarni boshqarish huquqi yo'q!")
        return
    await message.answer("📢 <b>Majburiy Obuna Kanallari:</b>", reply_markup=kb.channels_manage_keyboard(), parse_mode="HTML")

@dp.message(F.text == "📋 Kanallar ro'yxati")
async def show_channels_list(message: Message):
    if not await db.has_permission(message.from_user.id, "channels"):
        return
    channels = await db.get_channels()
    if not channels:
        await message.answer("📭 Ulangan kanallar yo'q.")
        return
    txt = "📋 <b>Ulangan kanallar:</b>\n\n"
    for i, c in enumerate(channels, 1):
        txt += f"{i}. <b>{c['title']}</b> (<code>{c['channel_id']}</code>) — {c['invite_link']}\n"
    await message.answer(txt, parse_mode="HTML")

@dp.message(F.text.in_(["📢 Ochiq kanal qo'shish", "🔒 Zayavkali kanal qo'shish", "🌐 Ijtimoiy tarmoq havolasi"]))
async def add_channel_type_start(message: Message, state: FSMContext):
    if not await db.has_permission(message.from_user.id, "channels"):
        return
    ch_type = "request" if "Zayavkali" in message.text else ("url" if "Ijtimoiy" in message.text else "public")
    await state.update_data(ch_type=ch_type)
    await state.set_state(AddChannelState.info)
    if ch_type == "url":
        await message.answer("Format: <code>NOMI | HAVOLA</code>", reply_markup=kb.cancel_keyboard(), parse_mode="HTML")
    else:
        await message.answer(
            "Format: <code>KANAL_ID | KANAL_NOMI | KANAL_HAVOLASI</code>\n"
            "<i>(Kanal ID sini bilish uchun kanalda /chatid@movieeland_bot deb yozing)</i>",
            reply_markup=kb.cancel_keyboard(),
            parse_mode="HTML"
        )

@dp.message(AddChannelState.info)
async def add_channel_save(message: Message, state: FSMContext):
    data = await state.get_data()
    ch_type = data.get("ch_type", "public")
    parts = [p.strip() for p in message.text.split("|")]
    if ch_type == "url":
        if len(parts) < 2:
            await message.answer("❌ Format: <code>NOMI | HAVOLA</code>", parse_mode="HTML")
            return
        title, link = parts[0], parts[1]
        ch_id = f"url_{abs(hash(link)) % 100000}"
    else:
        if len(parts) < 2:
            await message.answer(
                "❌ Format: <code>KANAL_ID | KANAL_NOMI | KANAL_HAVOLASI</code>\n"
                "<i>(Yoki havolani bot o'zi yaratishi uchun: <code>KANAL_ID | KANAL_NOMI | auto</code>)</i>",
                parse_mode="HTML"
            )
            return
        ch_id = parts[0]
        title = parts[1]
        link = parts[2] if len(parts) >= 3 else "auto"

        # Bot o'sha kanalda haqiqatdan Admin ekanligini tekshiramiz!
        try:
            me = await bot.get_me()
            bot_mem = await bot.get_chat_member(chat_id=ch_id, user_id=me.id)
            if bot_mem.status != ChatMemberStatus.ADMINISTRATOR:
                await message.answer(
                    f"⚠️ <b>Diqqat! Bot ushbu kanalda (<code>{ch_id}</code>) Admin emas!</b>\n"
                    f"1 mln obunachida ham kirish-chiqishni va zayavkalarni xatosiz nazorat qilish uchun avval botni kanalga <b>Admin</b> qiling va qayta yuboring!",
                    parse_mode="HTML"
                )
                return
            if link.lower() == "auto" or not link.startswith("http"):
                inv = await bot.create_chat_invite_link(
                    chat_id=ch_id,
                    creates_join_request=(ch_type == "request")
                )
                link = inv.invite_link
        except Exception as e:
            await message.answer(
                f"❌ <b>Kanalga ulanishda xatolik:</b> <code>{e}</code>\n\n"
                f"Botni kanalga (<code>{ch_id}</code>) <b>Admin</b> qilganingizga va Kanal ID to'g'riligiga ishonch hosil qiling!",
                parse_mode="HTML"
            )
            return

    await db.add_channel(ch_id, title, link, ch_type)
    await state.clear()
    await message.answer(
        f"✅ <b>Kanal muvaffaqiyatli ulandi va kirish-chiqish nazorati yoqildi!</b>\n"
        f"🏷 <b>Nomi:</b> {title}\n"
        f"🆔 <b>ID:</b> <code>{ch_id}</code>\n"
        f"🔗 <b>Havola:</b> {link}",
        reply_markup=kb.channels_manage_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.message(F.text == "➖ Kanal o'chirish")
async def del_channel_start(message: Message, state: FSMContext):
    if not await db.has_permission(message.from_user.id, "channels"):
        return
    await state.set_state(DeleteChannelState.ch_id)
    await message.answer("🗑 O'chirmoqchi bo'lgan kanal <b>ID</b> sini kiriting:", reply_markup=kb.cancel_keyboard(), parse_mode="HTML")

@dp.message(DeleteChannelState.ch_id)
async def del_channel_proc(message: Message, state: FSMContext):
    ok = await db.delete_channel(message.text.strip())
    await state.clear()
    await message.answer("✅ O'chirildi!" if ok else "❌ Topilmadi.", reply_markup=kb.channels_manage_keyboard())

@dp.message(F.text == "📩 Kino buyurtmalar")
async def show_pending_orders(message: Message):
    if not await db.has_permission(message.from_user.id, "orders"):
        await message.answer("⛔ Sizda buyurtmalarni ko'rish va qabul qilish huquqi yo'q!")
        return
    orders = await db.get_pending_orders(15)
    if not orders:
        await message.answer("✅ Hozircha yangi buyurtmalar yo'q!")
        return
    for o in orders:
        uname = f"@{o['username']}" if o.get("username") else "yo'q"
        st_lbl = "⏳ Moderator qabul qilgan (Tayyorlanmoqda)" if o.get("status") == "accepted" else "🆕 Yangi buyurtma"
        txt = (
            f"📩 <b>Buyurtma #{o['id']}</b> ({st_lbl})\n"
            f"👤 User: <b>{o['full_name']}</b> ({uname} | <code>{o['user_id']}</code>)\n"
            f"🎬 Kino: <b>{o['movie_name']}</b>\n"
            f"🕒 Vaqti: {o['created_at']}"
        )
        await message.answer(txt, reply_markup=kb.order_admin_keyboard(o["id"], o["user_id"], status=o.get("status", "pending")), parse_mode="HTML")

@dp.callback_query(F.data.startswith("accept_order:"))
async def cb_accept_order(call: CallbackQuery):
    """
    Moderator yoki Admin buyurtmani qabul qilganda:
    Foydalanuvchiga «Qabul qilindi, siz kanal va botni kuzatib turing, tez orada ushbu kino qo'shiladi!»
    deb avtomatik xabar yuboriladi!
    """
    if not await db.has_permission(call.from_user.id, "orders"):
        await call.answer("⛔ Faqatgina Super-Admin ruxsat bergan Admin/Moderator buyurtmani qabul qila oladi!", show_alert=True)
        return
    _, order_id_str, user_id_str = call.data.split(":")
    order_id = int(order_id_str)
    target_uid = int(user_id_str)

    order_obj = await db.get_order(order_id)
    movie_name = order_obj.get("movie_name", "Kino") if order_obj else "Kino"
    await db.accept_order(order_id)

    try:
        await call.message.edit_text(
            f"{call.message.text}\n\n⏳ <b>Qabul qilindi!</b> (Moderator: <b>{call.from_user.full_name}</b>)",
            reply_markup=kb.order_admin_keyboard(order_id, target_uid, status="accepted"),
            parse_mode="HTML"
        )
    except Exception:
        pass

    u_lang = await db.get_user_lang(target_uid)
    if u_lang == "ru":
        notify_txt = (
            f"✅ <b>Ваш заказ (#{order_id}) принят модератором!</b>\n\n"
            f"🎬 Фильм: <b>{movie_name}</b>\n"
            f"📢 Пожалуйста, следите за нашим каналом @movieee_land и ботом — в ближайшее время этот фильм будет добавлен!"
        )
    else:
        notify_txt = (
            f"✅ <b>Buyurtmangiz (#{order_id}) moderator tomonidan qabul qilindi!</b>\n\n"
            f"🎬 Kino: <b>{movie_name}</b>\n"
            f"📢 Siz @movieee_land kanalimiz va botni kuzatib turing, tez orada ushbu kino qo'shiladi!"
        )
    try:
        await bot.send_message(chat_id=target_uid, text=notify_txt, parse_mode="HTML")
    except Exception:
        pass
    await call.answer("✅ Buyurtma qabul qilindi va foydalanuvchiga xabar yuborildi!", show_alert=True)

@dp.callback_query(F.data.startswith("done_order:"))
async def cb_done_order(call: CallbackQuery):
    if not await db.has_permission(call.from_user.id, "orders"):
        await call.answer("⛔ Sizda buyurtmalarni boshqarish huquqi yo'q!", show_alert=True)
        return
    order_id = int(call.data.split(":")[1])
    await db.close_order(order_id)
    await call.message.edit_text(f"{call.message.text}\n\n✅ <b>Bajarildi!</b>", parse_mode="HTML")
    await call.answer("✅ Buyurtma bajarildi deb belgilandi!")

@dp.callback_query(F.data.startswith("ans_order:"))
async def cb_ans_order_start(call: CallbackQuery, state: FSMContext):
    if not await db.has_permission(call.from_user.id, "orders"):
        await call.answer("⛔ Sizda buyurtmalarga javob berish huquqi yo'q!", show_alert=True)
        return
    _, order_id, user_id = call.data.split(":")
    await state.update_data(order_id=int(order_id), target_user_id=int(user_id))
    await state.set_state(AnswerOrderState.text)
    await call.message.answer("✉️ Foydalanuvchiga javob yoki kino kodini yozing:", reply_markup=kb.cancel_keyboard())
    await call.answer()

@dp.message(AnswerOrderState.text)
async def ans_order_send(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await db.close_order(data["order_id"])
    perms = await db.get_user_permissions(message.from_user.id)
    role = await db.get_user_role(message.from_user.id)
    try:
        await bot.send_message(
            chat_id=data["target_user_id"],
            text=f"🔔 <b>Kino buyurtmangiz bo'yicha javob:</b>\n\n💬 <b>{message.text}</b>",
            parse_mode="HTML"
        )
        await message.answer("✅ Javob yetkazildi!", reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")))
    except Exception as e:
        await message.answer(f"❌ Xato: {e}", reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")))

@dp.message(F.text.in_(["📊 Statistika", "📊 Kengaytirilgan Statistika"]))
async def full_statistics_cmd(message: Message):
    if not await db.has_permission(message.from_user.id, "stats"):
        await message.answer("⛔ Sizda statistikani ko'rish huquqi yo'q!")
        return
    st = await db.get_full_stats()
    top_movies = await db.get_top_movies(5)
    top_m_txt = "".join([f"{i}. <b>#{m['code']} {m['name']}</b> — {m['views']} 👁 | 👍 {m['likes']}\n" for i, m in enumerate(top_movies, 1)])

    text = (
        f"📊 <b>MOVIE LAND ULTRA — STATISTIKA</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {st['total_users']} ta\n"
        f"📅 <b>Bugun qo'shilganlar:</b> +{st['today_users']} ta\n"
        f"📈 <b>Oxirgi 7 kunda:</b> +{st['week_users']} ta\n"
        f"💎 <b>Premium (VIP) a'zolar:</b> {st['vip_users']} ta\n"
        f"👮 <b>Moder/Adminlar soni:</b> {st['staff_count']} ta\n"
        f"🚫 <b>Bloklanganlar (Ban):</b> {st['banned_users']} ta\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎬 <b>Filmlar:</b> {st['total_movies']} ta | 🎞 <b>Seriallar:</b> {st['total_serials']} ta ({st['total_episodes']} qism)\n"
        f"📥 <b>Arxivdan olingan postlar:</b> {st['archive_count']} ta\n"
        f"👁 <b>Jami ko'rishlar:</b> {st['total_views']} marta\n"
        f"📩 <b>Kutilayotgan buyurtmalar:</b> {st['pending_orders']} ta\n"
        f"💾 <b>Baza hajmi (WAL):</b> {st['db_size_kb']} KB\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 <b>Top-5 Kinolar:</b>\n{top_m_txt or 'Yo‘q'}"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "⚙️ Texnik Sozlamalar va Himoya")
async def bot_settings_menu(message: Message):
    if await db.get_user_role(message.from_user.id) != "superadmin":
        return
    prot = await db.get_setting("protect_content", "1")
    ch = await db.get_setting("auto_post_channel", config.DEFAULT_POST_CHANNEL_ID)
    act = await db.get_setting("bot_active", "1")
    await message.answer(
        "⚙️ <b>TEXNIK SOZLAMALAR VA KONTENT HIMOYASI:</b>\n"
        "• <b>Forward va Saqlashni cheklash</b> yoqilsa, botdagi barcha xabarlar va kinolarni hech kim forward qila olmaydi va saqlay olmaydi!",
        reply_markup=kb.settings_inline_keyboard(prot, ch, act),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "toggle_protect")
async def cb_toggle_protect(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    cur = await db.get_setting("protect_content", "1")
    new_val = "0" if cur == "1" else "1"
    await db.set_setting("protect_content", new_val)
    ch = await db.get_setting("auto_post_channel", config.DEFAULT_POST_CHANNEL_ID)
    act = await db.get_setting("bot_active", "1")
    await call.message.edit_reply_markup(reply_markup=kb.settings_inline_keyboard(new_val, ch, act))
    await call.answer("🔒 Forward va Saqlash himoyasi yangilandi!")

@dp.callback_query(F.data == "toggle_bot_active")
async def cb_toggle_bot_active(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    cur = await db.get_setting("bot_active", "1")
    new_val = "0" if cur == "1" else "1"
    await db.set_setting("bot_active", new_val)
    prot = await db.get_setting("protect_content", "1")
    ch = await db.get_setting("auto_post_channel", config.DEFAULT_POST_CHANNEL_ID)
    await call.message.edit_reply_markup(reply_markup=kb.settings_inline_keyboard(prot, ch, new_val))
    await call.answer("🤖 Bot holati yangilandi!")

@dp.callback_query(F.data == "set_autopost_ch")
async def cb_set_autopost_ch(call: CallbackQuery, state: FSMContext):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return
    await state.set_state(SetAutoPostState.channel_id)
    await call.message.answer("📢 Avto-Post kanal ID sini yoki @username ni yuboring (masalan: <code>@movieee_land</code>):", reply_markup=kb.cancel_keyboard(), parse_mode="HTML")
    await call.answer()

@dp.callback_query(F.data == "btn_shutdown_bot")
async def cb_shutdown_bot(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return await call.answer("⛔ Faqat Super Administrator uchun!", show_alert=True)
    await call.message.answer("🛑 <b>Movie Land BOT to'liq to'xtatilmoqda...</b>\n\nJarayon xavfsiz yakunlandi.", parse_mode="HTML")
    await call.answer("🛑 Bot to'xtatilmoqda...")
    logging.info(f"Super Admin ({call.from_user.id}) tomonidan inline tugma orqali bot to'xtatildi.")
    cleanup_pid()
    os._exit(0)

@dp.callback_query(F.data == "btn_restart_bot")
async def cb_restart_bot(call: CallbackQuery):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        return await call.answer("⛔ Faqat Super Administrator uchun!", show_alert=True)
    await call.message.answer("🔄 <b>Movie Land BOT qayta ishga tushirilmoqda...</b>", parse_mode="HTML")
    await call.answer("🔄 Qayta ishga tushirilmoqda...")
    logging.info(f"Super Admin ({call.from_user.id}) tomonidan inline tugma orqali bot qayta yuklandi.")
    cleanup_pid()
    python_exe = sys.executable
    os.execl(python_exe, python_exe, *sys.argv)

@dp.message(SetAutoPostState.channel_id)
async def save_autopost_ch(message: Message, state: FSMContext):
    await db.set_setting("auto_post_channel", message.text.strip())
    await state.clear()
    await message.answer("✅ Avto-Post kanali saqlandi!", reply_markup=kb.super_admin_keyboard())

@dp.message(F.text == "🚫 User qidirish va Ban")
async def user_ban_menu(message: Message, state: FSMContext):
    if not await db.has_permission(message.from_user.id, "users_ban"):
        await message.answer("⛔ Sizda bu funksiya uchun huquq yo'q!")
        return
    await state.set_state(UserManageState.ban_id)
    await message.answer(
        "🔍 Foydalanuvchini ko'rish va <b>Ban / Unban</b> qilish uchun uning <b>Chat ID</b> raqamini yuboring:",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(UserManageState.ban_id)
async def user_ban_proc(message: Message, state: FSMContext):
    await state.clear()
    perms = await db.get_user_permissions(message.from_user.id)
    role = await db.get_user_role(message.from_user.id)
    if not message.text.strip().isdigit():
        await message.answer("❌ Noto'g'ri ID!", reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")))
        return
    uid = int(message.text.strip())
    u = await db.get_user(uid)
    is_b = await db.is_user_banned(uid)
    await db.set_ban(uid, 0 if is_b else 1)
    st_txt = "✅ Blokdan chiqarildi (Unban)!" if is_b else "🚫 Bloklandi (Ban)!"
    u_name = u.get("full_name", "User") if u else "User"
    await message.answer(
        f"👤 <b>{u_name}</b> (<code>{uid}</code>)\nHolati: <b>{st_txt}</b>",
        reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")),
        parse_mode="HTML"
    )

@dp.message(F.text == "✉️ Xabar yuborish")
async def broadcast_start_cmd(message: Message, state: FSMContext):
    if not await db.has_permission(message.from_user.id, "broadcast"):
        await message.answer("⛔ Sizda xabar tarqatish huquqi yo'q!")
        return
    await state.set_state(BroadcastState.message)
    await message.answer(
        "✉️ <b>Barcha foydalanuvchilarga yuboriladigan xabarni tashlang:</b>",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )

@dp.message(BroadcastState.message)
async def broadcast_send_proc(message: Message, state: FSMContext):
    await state.clear()
    users = await db.get_all_users()
    status_msg = await message.answer(f"📤 Xabar <b>{len(users)}</b> ta foydalanuvchiga asinxron yuborilmoqda...", parse_mode="HTML")

    sem = asyncio.Semaphore(25)
    sent, failed = 0, 0

    async def send_one(uid):
        nonlocal sent, failed
        async with sem:
            try:
                await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    reply_markup=message.reply_markup
                )
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.04)

    await asyncio.gather(*(send_one(u) for u in users))
    perms = await db.get_user_permissions(message.from_user.id)
    role = await db.get_user_role(message.from_user.id)
    await status_msg.edit_text(
        f"✅ <b>Xabar tarqatish yakunlandi!</b>\n📬 Yetkazildi: <b>{sent} ta</b> | 🚫 Xato: <b>{failed} ta</b>",
        parse_mode="HTML"
    )
    await message.answer("Boshqaruv paneli:", reply_markup=kb.staff_panel_keyboard(perms, is_super=(role == "superadmin")))


# ===================== ASOSIY MATNLI QIDIRUV (UZ / RU) =====================
@fallback_router.message(F.text)
async def general_text_handler(message: Message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    if await db.is_user_banned(user_id):
        return

    lang = await db.get_user_lang(user_id)
    text = message.text.strip()
    unsubscribed = await check_subscriptions(user_id)
    if unsubscribed:
        code_arg = text.lstrip("#") if text.lstrip("#").isdigit() else None
        await message.answer(
            t("sub_first", lang),
            reply_markup=kb.subscription_keyboard(unsubscribed, code_arg, lang=lang),
            parse_mode="HTML"
        )
        return

    clean_code = text.lstrip("#")
    if clean_code.isdigit():
        await send_movie_card(message, user_id, clean_code)
        return

    exact_movie = await db.get_movie(clean_code, increment_view=False)
    if exact_movie:
        await send_movie_card(message, user_id, clean_code)
        return

    results = await db.search_movies_by_name(text)
    if results:
        if len(results) == 1:
            await send_movie_card(message, user_id, results[0]["code"])
        else:
            await message.answer(
                t("search_results", lang, q=text, cnt=len(results)),
                reply_markup=kb.movies_list_inline(results, "🎬", lang=lang, query=text),
                parse_mode="HTML"
            )
    else:
        await message.answer(
            t("movie_not_found_text", lang, q=text),
            parse_mode="HTML"
        )


# ===================== AVTO-BACKUP VA PREMIUM TUGASHINI NAZORAT QILUVCHI ENGINE =====================
async def premium_expiry_worker():
    """
    Har 30 soniyada Premium muddati tugagan foydalanuvchilarni tekshiradi.
    Muddati tugagan zahoti botdan VIP ni o'chiradi va Mavzuli Guruhdan (-1002748514315)
    uning [PREMIUM] tegini darhol olib tashlaydi!
    """
    while True:
        await asyncio.sleep(30)
        try:
            expired_users = await db.pop_expired_premium_users()
            for u in expired_users:
                uid = u["user_id"]
                await remove_vip_tag_across_ecosystem(bot, uid)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                await log_to_activity_topic(
                    bot,
                    f"⏰ <b>PREMIUM MUDDATI TUGADI (TEG O'CHIRILDI)</b>\n"
                    f"👤 Foydalanuvchi: <b>{u.get('full_name', 'User')}</b> (<code>{uid}</code>)\n"
                    f"🏷 Olib tashlangan teg: <code>[{u.get('vip_tag', 'PREMIUM')}]</code>\n"
                    f"🕒 Vaqt: <code>{now_str}</code>"
                )

                u_lang = await db.get_user_lang(uid)
                renew_btn = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="💎 Продлить Premium (VIP)" if u_lang == "ru" else "💎 Premium (VIP) ni uzaytirish",
                        callback_data="open_vip_shop"
                    )]
                ])
                try:
                    if u_lang == "ru":
                        msg = (
                            "⏰ <b>Срок вашей подписки 💎 PREMIUM (VIP) истек!</b>\n\n"
                            "Ваш специальный тег <code>[PREMIUM]</code> в группе <b>Movie Land Group</b> и VIP-лимиты в боте отключены.\n"
                            "👇 Вы можете продлить подписку в любой момент:"
                        )
                    else:
                        msg = (
                            "⏰ <b>Sizning 💎 PREMIUM (VIP) obuna muddatingiz tugadi!</b>\n\n"
                            "<b>Movie Land Group</b> mavzuli guruhidagi <code>[PREMIUM]</code> tegingiz va botdagi VIP imtiyozlaringiz to'xtatildi.\n"
                            "👇 Istalgan vaqtda obunani qayta uzaytirishingiz mumkin:"
                        )
                    await bot.send_message(uid, msg, reply_markup=renew_btn, parse_mode="HTML")
                except Exception:
                    pass
        except Exception as e:
            logging.warning(f"Premium expiry worker xato: {e}")


async def auto_backup_worker():
    """
    Har haftada (168 soatda) yoki belgilangan soatda to'liq bazani (.db va .json)
    avtomatik ravishda Arxiv Guruhga (-1003124847141) yuborib turadi!
    """
    while True:
        await asyncio.sleep(600)
        try:
            hours_str = await db.get_setting("auto_backup_hours", "168")
            target_id = await db.get_setting("auto_backup_target", config.DEFAULT_ARCHIVE_CHANNEL_ID)
            if hours_str != "0" and target_id.lstrip("-").isdigit():
                hours = int(hours_str)
                last_bkp = await db.get_setting("last_auto_backup_ts", "0")
                now_ts = int(time.time())
                if now_ts - int(last_bkp or 0) >= hours * 3600:
                    await db.set_setting("last_auto_backup_ts", str(now_ts))
                    lbl = "AVTOMATIK HAFTALIK BACKUP" if hours == 168 else f"AVTOMATIK BACKUP (Har {hours} soatda)"
                    await send_full_backup_to_target(int(target_id), title_note=lbl)
        except Exception as e:
            logging.warning(f"Auto-backup xato: {e}")


# ===================== BOTNI TO'XTATISH VA QAYTA YUKLASH BUYRUQLARI =====================
@dp.message(Command("shutdown", "stopbot"))
async def cmd_shutdown_bot(message: Message):
    uid = message.from_user.id
    if not (await db.is_super_admin(uid) or uid in config.ADMINS):
        return await message.answer("❌ Bu buyruq faqat Super Administratorga tegishli!")
    await message.answer("🛑 <b>Movie Land BOT to'liq to'xtatilmoqda...</b>\n\nJarayon xavfsiz yakunlandi.", parse_mode="HTML")
    logging.info(f"Super Admin ({uid}) tomonidan /shutdown buyrug'i berildi. Jarayon to'xtatilmoqda...")
    cleanup_pid()
    os._exit(0)

@dp.message(Command("restart", "restartbot"))
async def cmd_restart_bot(message: Message):
    uid = message.from_user.id
    if not (await db.is_super_admin(uid) or uid in config.ADMINS):
        return await message.answer("❌ Bu buyruq faqat Super Administratorga tegishli!")
    await message.answer("🔄 <b>Movie Land BOT qayta ishga tushirilmoqda...</b>", parse_mode="HTML")
    logging.info(f"Super Admin ({uid}) tomonidan /restart buyrug'i berildi.")
    cleanup_pid()
    python_exe = sys.executable
    os.execl(python_exe, python_exe, *sys.argv)


# ===================== CLOUD / RENDER WEB SERVICE HEALTH CHECK =====================
async def start_dummy_health_server():
    port_str = os.getenv("PORT")
    if not port_str:
        return
    # Agar Gradio (app.py) orqali ishlayotgan bo'lsa, Gradio o'zi portni boshqaradi
    if "gradio" in sys.modules or os.path.basename(sys.argv[0]) == "app.py":
        return
    try:
        from aiohttp import web
        port = int(port_str)
        app = web.Application()

        async def handle_ping(request):
            return web.Response(text="Movie Land Ultra Bot is alive 24/7! 🎬", content_type="text/plain")

        app.router.add_get("/", handle_ping)
        app.router.add_get("/health", handle_ping)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logging.info(f"Render/Cloud HTTP Health server listening on port {port}")
    except Exception as e:
        logging.warning(f"Could not start cloud health server on port {port_str}: {e}")


# ===================== ASOSIY ISHGA TUSHIRISH =====================
async def main():
    global BOT_USERNAME
    single_instance_guard()
    try:
        await start_dummy_health_server()
        await db.init_db()
        dp.include_router(eco_router)
        dp.include_router(fallback_router)
        me = await bot.get_me()
        BOT_USERNAME = me.username
        # Barcha mavjud Premium foydalanuvchilarga Mavzuli Guruhda (-1002748514315) avtomatik PREMIUM tegini sinxronlash
        try:
            vips = await db.get_all_premium_users()
            for v in vips:
                await apply_vip_tag_across_ecosystem(bot, v["user_id"], v.get("vip_tag", "PREMIUM"))
        except Exception:
            pass

        asyncio.create_task(auto_backup_worker())
        asyncio.create_task(premium_expiry_worker())
        logging.info(f"Movie Land Ultra Bot (@{BOT_USERNAME}) [PID: {os.getpid()}] 2-Tilli (UZ/RU), TMDB Poster va Mavzuli Guruh (-1002748514315) Ekotizimi bilan ishga tushdi!")
        allowed = list(set(dp.resolve_used_update_types() + ["chat_member", "my_chat_member", "chat_join_request", "inline_query", "chosen_inline_result"]))
        await dp.start_polling(bot, handle_as_tasks=True, allowed_updates=allowed)
    finally:
        cleanup_pid()
        try:
            await bot.session.close()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        cleanup_pid()
        logging.info("Bot jarayoni toza yakunlandi.")
