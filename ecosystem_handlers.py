import logging
from datetime import datetime
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import config
import database as db
import keyboards as kb
from i18n import b_vals, t, DEFAULT_RULES_UZ, DEFAULT_RULES_RU

eco_router = Router()


# ===================== FSM HOLATLARI =====================
class CustomTagState(StatesGroup):
    waiting_tag = State()

class CardPaymentState(StatesGroup):
    waiting_receipt = State()

class AdminReceiptBalState(StatesGroup):
    waiting_amount = State()

class EconomySettingState(StatesGroup):
    waiting_value = State()
    waiting_user_bal = State()

class VIPReviewState(StatesGroup):
    waiting_text = State()


# ===================== «⚡ АКТИВНЫЙ FAOLIK» BO'LIMIGA MUHIM SEANSLARNI YUBORISH =====================
async def log_to_activity_topic(bot: Bot, text: str, reply_markup=None):
    """
    Muhim hodisalarni (Yangi user, Premium xarid, To'lov cheki, VIP tugashi)
    Movie Land Group (-1002748514315) ichidagi «⚡ Активный Faolik» (thread_id=196) bo'limiga yuboradi!
    """
    try:
        await bot.send_message(
            chat_id=int(config.MAIN_TOPIC_GROUP_ID),
            message_thread_id=config.TOPIC_ACTIVITY_ID,
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.debug(f"Faolik bo'limiga yozishda xato: {e}")


# ===================== MAVZULI GURUHDA (-1002748514315) AVTO «PREMIUM» TEG O'RNATISH VA O'CHIRISH =====================
async def apply_vip_tag_across_ecosystem(bot: Bot, user_id: int, custom_tag: str = None) -> int:
    """
    Foydalanuvchi Premium olganda yagona rasmiy Mavzuli Guruhda (-1002748514315)
    unga rasmiy Telegram Member Tag (`setChatMemberTag` -> `PREMIUM` tegi) beradi!
    """
    u = await db.get_user(user_id)
    tag = (custom_tag or (u.get("vip_tag") if u else "PREMIUM") or "PREMIUM").strip()[:16]
    chat_id = int(config.MAIN_TOPIC_GROUP_ID)

    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status in ("left", "kicked"):
            return 0

        # 1. Telegram Bot API rasmiy setChatMemberTag orqali a'zoga bevosita PREMIUM tegini o'rnatamiz!
        try:
            await bot.set_chat_member_tag(
                chat_id=chat_id,
                user_id=user_id,
                tag=tag
            )
            return 1
        except Exception as tag_err:
            logging.debug(f"set_chat_member_tag xato ({chat_id}): {tag_err}")

        # 2. Zaxira: Agar u guruhda administrator bo'lsa custom_title ni ham o'rnatamiz
        if member.status == "administrator":
            try:
                await bot.set_chat_administrator_custom_title(
                    chat_id=chat_id,
                    user_id=user_id,
                    custom_title=tag
                )
                return 1
            except Exception:
                pass
        return 0
    except Exception as e:
        logging.debug(f"Mavzuli guruhda teg o'rnatishda ({chat_id}): {e}")
        return 0


async def remove_vip_tag_across_ecosystem(bot: Bot, user_id: int) -> bool:
    """
    Foydalanuvchining Premium muddati tugagan zahoti (yoki olib tashlanganda)
    Mavzuli Guruhdan (-1002748514315) uning [PREMIUM] tegini darhol olib tashlaydi!
    """
    role = await db.get_user_role(user_id)
    if role in ("admin", "superadmin"):
        return False

    chat_id = int(config.MAIN_TOPIC_GROUP_ID)
    removed = False
    try:
        # 1. Member Tag ni bo'shatib ('') olib tashlaymiz
        try:
            await bot.set_chat_member_tag(
                chat_id=chat_id,
                user_id=user_id,
                tag=""
            )
            removed = True
        except Exception:
            pass

        # 2. Agar avval admin qilingan bo'lsa, oddiy a'zoga qaytaramiz
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status == "administrator":
            await bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
                can_manage_topics=False
            )
            removed = True
    except Exception as e:
        logging.debug(f"Mavzuli guruhdan tegni o'chirishda ({chat_id}): {e}")
    return removed


# ===================== 0. TIL TANLASH VA QOIDALAR BO'LIMI (UZ / RU) =====================
@eco_router.message(Command("lang", "language"))
@eco_router.message(F.text.in_(b_vals("lang")))
async def cmd_change_language(message: Message):
    lang = await db.get_user_lang(message.from_user.id)
    await message.answer(
        t("choose_lang", lang),
        reply_markup=kb.language_select_inline(),
        parse_mode="HTML"
    )

async def send_rules_screen(target, user_id: int):
    lang = await db.get_user_lang(user_id)
    rules_txt = DEFAULT_RULES_RU if lang == "ru" else DEFAULT_RULES_UZ
    btn_txt = "💎 Открыть правила в группе" if lang == "ru" else "💎 Guruhdagi qoidalar bo'limi"
    back_txt = "🔙 В главное меню" if lang == "ru" else "🔙 Asosiy menyuga qaytish"
    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_txt, url=f"{config.MAIN_TOPIC_GROUP_LINK}/{config.TOPIC_RULES_ID}")],
        [InlineKeyboardButton(text=back_txt, callback_data="back_main_menu")]
    ])
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(rules_txt, reply_markup=btn, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            await target.message.answer(rules_txt, reply_markup=btn, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await target.answer(rules_txt, reply_markup=btn, parse_mode="HTML", disable_web_page_preview=True)

@eco_router.message(Command("rules", "qoidalar"))
@eco_router.message(F.text.in_(b_vals("rules")))
async def cmd_show_rules(message: Message):
    await send_rules_screen(message, message.from_user.id)

@eco_router.callback_query(F.data == "nav:rules")
async def cb_nav_rules(call: CallbackQuery):
    await call.answer()
    await send_rules_screen(call, call.from_user.id)


# ===================== 1. KUNLIK BONUS VA PUL ISHLASH (UZ / RU) =====================
async def send_earn_money_screen(target, user_id: int, bot: Bot):
    b_uname = (await bot.get_me()).username
    lang = await db.get_user_lang(user_id)
    u = await db.get_user(user_id) or {}
    daily_amt = await db.get_setting("daily_reward_amount", config.DEFAULT_DAILY_REWARD)
    ref_amt = await db.get_setting("ref_reward_amount", config.DEFAULT_REF_REWARD)
    p7 = await db.get_setting("vip_7_price", config.DEFAULT_VIP_7_PRICE)

    bal = u.get("balance") or 0
    earned = u.get("total_earned") or 0
    streak = u.get("daily_streak") or 0
    refs = u.get("ref_count") or 0
    ref_link = f"https://t.me/{b_uname}?start=ref_{user_id}"

    if lang == "ru":
        text = (
            f"🎁 <b>ЦЕНТР ЕЖЕДНЕВНЫХ БОНУСОВ И ЗАРАБОТКА</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"💰 <b>Ваш текущий баланс:</b> <code>{bal:,}</code> сум\n"
            f"📈 <b>Всего заработано:</b> <code>{earned:,}</code> сум\n"
            f"🔥 <b>Ежедневный стрик:</b> {streak} / 7 дней\n"
            f"👥 <b>Приглашено друзей:</b> {refs} чел."
            f"</blockquote>\n\n"
            f"💡 <b>Как бесплатно заработать деньги и 💎 VIP?</b>\n"
            f"<blockquote>"
            f"1️⃣ <b>Ежедневный бонус:</b> Базовый <b>+{int(daily_amt):,} сум</b> (+15% за каждый день подряд, а на 7-й день — <b>2x Бонус + 1 день Бесплатного VIP</b>!)\n"
            f"2️⃣ <b>Приглашайте друзей:</b> За каждого друга на баланс сразу начисляется <b>+{int(ref_amt):,} сум</b>!\n"
            f"3️⃣ Накопив <b>{int(p7):,} сум</b>, активируйте <b>💎 Premium (VIP)</b> прямо с баланса!"
            f"</blockquote>\n\n"
            f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{ref_link}</code>"
        )
    else:
        text = (
            f"🎁 <b>KUNLIK BONUS VA PUL ISHLASH MARKAZI</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"💰 <b>Joriy balansingiz:</b> <code>{bal:,}</code> so'm\n"
            f"📈 <b>Jami ishlangan pul:</b> <code>{earned:,}</code> so'm\n"
            f"🔥 <b>Kunlik Streak:</b> {streak} / 7 kun\n"
            f"👥 <b>Taklif etilgan do'stlar:</b> {refs} ta"
            f"</blockquote>\n\n"
            f"💡 <b>Qanday qilib bepul pul va 💎 VIP olish mumkin?</b>\n"
            f"<blockquote>"
            f"1️⃣ <b>Kunlik bonus oling:</b> Boshlang'ich <b>+{int(daily_amt):,} so'm</b> (har ketma-ket kun uchun +15%, 7-kunda esa <b>2x Bonus + 1 kun Bepul VIP</b>!)\n"
            f"2️⃣ <b>Do'stlarni taklif qiling:</b> Har bir taklif uchun balansingizga darhol <b>+{int(ref_amt):,} so'm</b> tushadi!\n"
            f"3️⃣ Balansingiz <b>{int(p7):,} so'm</b> ga yetganda 1 klikda <b>💎 Premium (VIP)</b> xarid qiling!"
            f"</blockquote>\n\n"
            f"🔗 <b>Shaxsiy taklif havolangiz:</b>\n<code>{ref_link}</code>"
        )

    markup = kb.earn_money_inline(ref_link, daily_amt, ref_amt, lang=lang)
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await target.message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=markup, parse_mode="HTML")

@eco_router.message(F.text.in_(b_vals("earn")))
async def cmd_earn_money(message: Message, bot: Bot):
    await send_earn_money_screen(message, message.from_user.id, bot)

@eco_router.callback_query(F.data == "go_earn_menu")
async def cb_go_earn_menu(call: CallbackQuery, bot: Bot):
    await call.answer()
    await send_earn_money_screen(call, call.from_user.id, bot)

@eco_router.callback_query(F.data == "claim_daily")
async def cb_claim_daily(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    res = await db.claim_daily_reward(user_id)

    if not res.get("ok"):
        msg = (
            f"⏳ Вы уже получили сегодняшний бонус!\n🔥 Стрик: {res.get('streak', 1)} дн. Приходите завтра!"
            if lang == "ru" else
            f"⏳ Siz bugungi kunlik bonusni olgansiz!\n🔥 Streak: {res.get('streak', 1)} kun. Ertaga yana keling!"
        )
        await call.answer(msg, show_alert=True)
        return

    earned = res["earned"]
    streak = res["streak"]
    vip_bonus = res.get("bonus_vip_days", 0)
    new_bal = res["balance"]

    extra_vip_txt = ""
    if vip_bonus > 0:
        await apply_vip_tag_across_ecosystem(bot, user_id)
        if lang == "ru":
            extra_vip_txt = f"\n🎉 <b>СУПЕР СТРИК (7-Й ДЕНЬ)! Вам подарен +{vip_bonus} день 💎 PREMIUM (VIP) и тег [PREMIUM] в группе!</b>"
        else:
            extra_vip_txt = f"\n🎉 <b>SUPER STREAK (7-KUN)! Sizga qo'shimcha +{vip_bonus} kunlik 💎 PREMIUM (VIP) va guruhda [PREMIUM] tegi sovg'a qilindi!</b>"

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await log_to_activity_topic(
            bot,
            f"🎁 <b>7-KUNLIK STREAK VIP SOVG'A!</b>\n"
            f"👤 Foydalanuvchi: <b>{call.from_user.full_name}</b> (<code>{user_id}</code>)\n"
            f"💎 Mukofot: <b>+{vip_bonus} kun VIP + [{earned:,} so'm]</b>\n"
            f"🕒 Vaqti: <code>{now_str}</code>"
        )

    if lang == "ru":
        await call.answer(f"🎉 +{earned:,} сум зачислено на ваш баланс!", show_alert=True)
        await call.message.answer(
            f"🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС ПОЛУЧЕН!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💵 Начислено: <b>+{earned:,} сум</b>\n"
            f"🔥 Стрик подряд: <b>{streak} / 7 дней</b>\n"
            f"💰 Новый баланс: <b>{new_bal:,} сум</b>"
            f"{extra_vip_txt}",
            parse_mode="HTML"
        )
    else:
        await call.answer(f"🎉 +{earned:,} so'm balansingizga qo'shildi!", show_alert=True)
        await call.message.answer(
            f"🎁 <b>KUNLIK BONUS QABUL QILINDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💵 Qo'shildi: <b>+{earned:,} so'm</b>\n"
            f"🔥 Ketma-ketlik (Streak): <b>{streak} / 7 kun</b>\n"
            f"💰 Yangi balansingiz: <b>{new_bal:,} so'm</b>"
            f"{extra_vip_txt}",
            parse_mode="HTML"
        )

@eco_router.callback_query(F.data == "show_leaderboard")
async def cb_show_leaderboard(call: CallbackQuery):
    lang = await db.get_user_lang(call.from_user.id)
    top_users = await db.get_top_referrers(10)
    if not top_users:
        await call.answer("Рейтинг пока пуст." if lang == "ru" else "Hozircha reyting bo'sh.", show_alert=True)
        return

    header = (
        "🏆 <b>ТОП-10 САМЫХ АКТИВНЫХ И БОГАТЫХ ПОЛЬЗОВАТЕЛЕЙ:</b>\n━━━━━━━━━━━━━━━━━━\n"
        if lang == "ru" else
        "🏆 <b>TOP-10 ENG FAOL VA BOY FOYDALANUVCHILAR:</b>\n━━━━━━━━━━━━━━━━━━\n"
    )
    txt = header
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for idx, u in enumerate(top_users, 1):
        m = medals.get(idx, f"{idx}.")
        tag_b = f" [💎 {u.get('vip_tag', 'PREMIUM')}]" if u.get("is_premium") else ""
        if lang == "ru":
            txt += f"{m} <b>{u['full_name']}</b>{tag_b}\n   👥 Рефералы: <b>{u['ref_count']}</b> | 💰 Баланс: <b>{u.get('balance', 0):,} сум</b>\n"
        else:
            txt += f"{m} <b>{u['full_name']}</b>{tag_b}\n   👥 Takliflar: <b>{u['ref_count']} ta</b> | 💰 Balans: <b>{u.get('balance', 0):,} so'm</b>\n"
    await call.message.answer(txt, parse_mode="HTML")
    await call.answer()


# ===================== 2. PREMIUM (VIP) DO'KON, TEG VA OTZIVLAR (UZ / RU) =====================
async def send_vip_shop_screen(target, user_id: int):
    lang = await db.get_user_lang(user_id)
    u = await db.get_user(user_id) or {}
    is_vip = await db.is_user_premium(user_id)
    bal = u.get("balance") or 0
    cur_tag = u.get("vip_tag") or "PREMIUM"

    p7 = await db.get_setting("vip_7_price", config.DEFAULT_VIP_7_PRICE)
    p30 = await db.get_setting("vip_30_price", config.DEFAULT_VIP_30_PRICE)
    p90 = await db.get_setting("vip_90_price", config.DEFAULT_VIP_90_PRICE)
    vip_lim = await db.get_setting("premium_order_limit", "5")
    used_today = await db.get_user_today_orders_count(user_id)

    if lang == "ru":
        if is_vip:
            until = (u.get("premium_until") or "Бессрочно")[:16].replace("T", " ")
            status_block = (
                f"<blockquote>"
                f"💎 <b>Ваш статус: PREMIUM VIP АКТИВЕН</b>\n"
                f"📅 Срок действия: <code>{until}</code>\n"
                f"🏷 Ваш Тег в группе: <b>[{cur_tag}]</b>\n"
                f"🎬 Заказов сегодня: <b>{used_today} / {vip_lim} шт.</b>"
                f"</blockquote>"
            )
        else:
            status_block = (
                f"<blockquote>"
                f"👤 Текущий статус: <b>Обычный пользователь</b>\n"
                f"💰 Ваш баланс: <b>{bal:,} сум</b>"
                f"</blockquote>"
            )
        text = (
            f"💎 <b>МАГАЗИН PREMIUM И ЭКОСИСТЕМА</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{status_block}\n\n"
            f"🌟 <b>Преимущества Premium:</b>\n"
            f"<blockquote>"
            f"1️⃣ <b>Официальный тег <code>[PREMIUM]</code> рядом с именем в Movie Land Group!</b>\n"
            f"2️⃣ Доступ к выбору уникального тега (<code>PREMIUM</code>, <code>VIP KING</code>)!\n"
            f"3️⃣ Заказ до <b>{vip_lim} фильмов в день</b> вне очереди!\n"
            f"4️⃣ Доступ в раздел <b>💸 Premium</b> для отзывов!"
            f"</blockquote>\n\n"
            f"👇 <i>Купите в 1 клик с баланса или оплатите картой:</i>"
        )
    else:
        if is_vip:
            until = (u.get("premium_until") or "Cheksiz")[:16].replace("T", " ")
            status_block = (
                f"<blockquote>"
                f"💎 <b>Sizning maqomingiz: PREMIUM VIP FAOL</b>\n"
                f"📅 Amal qilish muddati: <code>{until}</code> gacha\n"
                f"🏷 Guruhdagi Tegingiz: <b>[{cur_tag}]</b>\n"
                f"🎬 Bugungi kino buyurtma: <b>{used_today} / {vip_lim} ta</b>"
                f"</blockquote>"
            )
        else:
            status_block = (
                f"<blockquote>"
                f"👤 Joriy maqomingiz: <b>Oddiy foydalanuvchi</b>\n"
                f"💰 Balansingiz: <b>{bal:,} so'm</b>"
                f"</blockquote>"
            )
        text = (
            f"💎 <b>MOVIE LAND PREMIUM DO'KONI</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{status_block}\n\n"
            f"🌟 <b>Premium imkoniyatlari:</b>\n"
            f"<blockquote>"
            f"1️⃣ <b>Mavzuli Guruhda ismingiz yonida rasmiy <code>[PREMIUM]</code> Teg!</b>\n"
            f"2️⃣ O'zingiz xohlagan maxsus Teg (<code>PREMIUM</code>, <code>VIP KING</code>) tanlash!\n"
            f"3️⃣ Kuniga 1 ta o'rniga <b>{vip_lim} tagacha kino buyurtma</b> qilish!\n"
            f"4️⃣ Guruhning <b>💸 Premium</b> bo'limiga Otziv yozish huquqi!"
            f"</blockquote>\n\n"
            f"👇 <i>Balansingizdan 1 klikda xarid qiling yoki Karta orqali to'lang:</i>"
        )

    markup = kb.user_vip_shop_inline(p7, p30, p90, is_vip=is_vip, cur_tag=cur_tag, lang=lang)
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await target.message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=markup, parse_mode="HTML")

@eco_router.message(F.text.in_(b_vals("vip_shop") + ["💎 Premium (VIP)"]))
async def cmd_vip_shop(message: Message):
    await send_vip_shop_screen(message, message.from_user.id)

@eco_router.callback_query(F.data == "open_vip_shop")
async def cb_open_vip_shop(call: CallbackQuery):
    await call.answer()
    await send_vip_shop_screen(call, call.from_user.id)

@eco_router.callback_query(F.data.startswith("buy_vip:"))
async def cb_buy_vip_with_balance(call: CallbackQuery, bot: Bot):
    days = int(call.data.split(":")[1])
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)

    price_key = {7: "vip_7_price", 30: "vip_30_price", 90: "vip_90_price"}.get(days, "vip_30_price")
    def_price = {7: config.DEFAULT_VIP_7_PRICE, 30: config.DEFAULT_VIP_30_PRICE, 90: config.DEFAULT_VIP_90_PRICE}.get(days, "25000")
    price = int(await db.get_setting(price_key, def_price))

    res = await db.buy_premium_with_balance(user_id, days, price)
    if not res["ok"]:
        needed = res.get("needed", price)
        err_msg = (
            f"❌ На балансе недостаточно средств!\nНе хватает еще {needed:,} сум. Собирайте бонусы или оплатите картой!"
            if lang == "ru" else
            f"❌ Balansingizda mablag' yetarli emas!\nYana {needed:,} so'm kerak. Kunlik bonus oling, do'stlarni taklif qiling yoki karta orqali to'lang!"
        )
        await call.answer(err_msg, show_alert=True)
        return

    await apply_vip_tag_across_ecosystem(bot, user_id)
    u = await db.get_user(user_id) or {}
    cur_tag = u.get("vip_tag", "PREMIUM")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ⚡ Активный Faolik bo'limiga seans logini yuboramiz
    await log_to_activity_topic(
        bot,
        f"💎 <b>BALANSDAN YANGI PREMIUM XARID QILINDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Foydalanuvchi:</b> {call.from_user.full_name} (@{call.from_user.username or 'yoq'})\n"
        f"🆔 <b>Chat ID:</b> <code>{user_id}</code>\n"
        f"📦 <b>Tarif:</b> {days} kunlik VIP ({price:,} so'm)\n"
        f"🏷 <b>Berilgan Teg:</b> <code>[{cur_tag}]</code>\n"
        f"📅 <b>Amal qiladi:</b> <code>{res['premium_until']}</code> gacha\n"
        f"🕒 <b>Sana va vaqt:</b> <code>{now_str}</code>"
    )

    rev_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Оставить отзыв о Premium" if lang == "ru" else "💬 Premium haqida Otziv qoldirish",
            callback_data="vip_leave_review"
        )],
        [InlineKeyboardButton(
            text="🌐 Войти в Movie Land Group" if lang == "ru" else "🌐 Movie Land Group ga kirish",
            url=f"{config.MAIN_TOPIC_GROUP_LINK}/{config.TOPIC_CHAT_ID}"
        )]
    ])

    if lang == "ru":
        await call.answer("🎉 Поздравляем! Premium (VIP) активирован!", show_alert=True)
        await call.message.answer(
            f"🎉 <b>ПОЗДРАВЛЯЕМ! ВЫ ПРИОБРЕЛИ PREMIUM (VIP)!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>Тариф:</b> VIP на {days} дней\n"
            f"📅 <b>Действует до:</b> <code>{res['premium_until']}</code>\n"
            f"🏷 <b>Ваш VIP Тег в группе:</b> <code>[{cur_tag}]</code>\n"
            f"💰 <b>Остаток на балансе:</b> {res['new_balance']:,} сум\n\n"
            f"💬 <i>Пожалуйста, оставьте свой отзыв о покупке Premium по кнопке ниже — он сразу появится в разделе <b>💸 Premium</b>!</i>",
            reply_markup=rev_btn,
            parse_mode="HTML"
        )
    else:
        await call.answer("🎉 Tabriklaymiz! Premium (VIP) faollashtirildi!", show_alert=True)
        await call.message.answer(
            f"🎉 <b>TABRIKLAYMIZ! PREMIUM (VIP) XARID QILINDI!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>Paket:</b> {days} kunlik VIP\n"
            f"📅 <b>Amal qilish muddati:</b> <code>{res['premium_until']}</code> gacha\n"
            f"🏷 <b>Mavzuli guruhdagi Tegingiz:</b> <code>[{cur_tag}]</code>\n"
            f"💰 <b>Qolgan balansingiz:</b> {res['new_balance']:,} so'm\n\n"
            f"💬 <i>Quyidagi tugma orqali Premium haqida o'z fikringizni (Otziv) yozib qoldiring — u darhol guruhning <b>💸 Premium</b> bo'limiga chiqadi!</i>",
            reply_markup=rev_btn,
            parse_mode="HTML"
        )


# ===================== 2.1. «💸 PREMIUM» BO'LIMIGA OTZIV (FIKR) QOLDIRISH =====================
@eco_router.callback_query(F.data == "vip_leave_review")
async def cb_vip_leave_review(call: CallbackQuery):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    if not await db.is_user_premium(user_id):
        await call.answer(
            "⛔ Только пользователи с активным Premium могут оставлять отзывы!" if lang == "ru"
            else "⛔ Faqat Premium (VIP) sotib olgan foydalanuvchilar otziv qoldira oladi!",
            show_alert=True
        )
        return

    prompt = (
        "🌟 <b>ОЦЕНИТЕ НАШ PREMIUM (VIP) СЕРВИС:</b>\n\n"
        "Выберите оценку от 3 до 5 звезд ниже:"
        if lang == "ru" else
        "🌟 <b>PREMIUM (VIP) XIZMATIMIZNI BAHOLANG:</b>\n\n"
        "Quyidan yulduzcha (baho) ni tanlang:"
    )
    await call.message.answer(prompt, reply_markup=kb.vip_review_stars_inline(lang), parse_mode="HTML")
    await call.answer()

@eco_router.callback_query(F.data.startswith("rev_star:"))
async def cb_rev_star_selected(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    if not await db.is_user_premium(user_id):
        return
    stars = int(call.data.split(":")[1])
    await state.update_data(review_stars=stars)
    await state.set_state(VIPReviewState.waiting_text)

    msg = (
        f"✍️ <b>Вы выбрали: {'⭐' * stars} ({stars}/5)</b>\n\n"
        f"Теперь напишите ваш отзыв о боте и Premium (он будет опубликован в разделе <b>💸 Premium</b> тематической группы):"
        if lang == "ru" else
        f"✍️ <b>Siz tanladingiz: {'⭐' * stars} ({stars}/5)</b>\n\n"
        f"Endi Premium va bot haqidagi fikringizni (Otziv) yozib yuboring — u darhol guruhning <b>💸 Premium</b> bo'limiga joylanadi:"
    )
    await call.message.answer(msg, reply_markup=kb.cancel_keyboard(lang), parse_mode="HTML")
    await call.answer()

@eco_router.message(VIPReviewState.waiting_text, F.text)
async def save_and_post_vip_review(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    role = await db.get_user_role(user_id)

    if message.text in b_vals("cancel"):
        await state.clear()
        await message.answer(t("cancelled", lang), reply_markup=kb.user_main_keyboard(role, lang=lang))
        return

    data = await state.get_data()
    stars = data.get("review_stars", 5)
    await state.clear()

    u = await db.get_user(user_id) or {}
    tag = u.get("vip_tag") or "PREMIUM"
    until = (u.get("premium_until") or "")[:10]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    review_text = message.text.strip()[:600]

    # Guruhning 💸 Premium (thread_id=190) bo'limiga yuboramiz!
    group_post = (
        f"💸 <b>YANGI PREMIUM OTZIV (FIKR)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>VIP A'zo:</b> {message.from_user.full_name} [<code>💎 {tag}</code>]\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"🌟 <b>Baho:</b> {'⭐' * stars} ({stars}/5)\n"
        f"📅 <b>VIP muddati:</b> <code>{until}</code> gacha\n"
        f"🕒 <b>Sana:</b> <code>{now_str}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 <b>Fikri (Otziv):</b>\n<i>«{review_text}»</i>"
    )
    try:
        await bot.send_message(
            chat_id=int(config.MAIN_TOPIC_GROUP_ID),
            message_thread_id=config.TOPIC_PREMIUM_REVIEWS_ID,
            text=group_post,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.warning(f"Premium otziv yuborishda xato: {e}")

    btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💸 Посмотреть отзыв в группе" if lang == "ru" else "💸 Guruhda Otzivni ko'rish",
            url=f"{config.MAIN_TOPIC_GROUP_LINK}/{config.TOPIC_PREMIUM_REVIEWS_ID}"
        )]
    ])
    thanks = (
        "✅ <b>Спасибо за ваш отзыв!</b>\nВаш отзыв успешно опубликован в разделе <b>💸 Premium</b> тематической группы!"
        if lang == "ru" else
        "✅ <b>Fikringiz (Otziv) uchun rahmat!</b>\nOtzivingiz mavzuli guruhning <b>💸 Premium</b> bo'limiga muvaffaqiyatli joylandi!"
    )
    await message.answer(thanks, reply_markup=kb.user_main_keyboard(role, lang=lang), parse_mode="HTML")
    await message.answer("👇", reply_markup=btn)


# ===================== 2.2. VIP TEG TANLASH =====================
@eco_router.callback_query(F.data == "vip_choose_tag")
async def cb_vip_choose_tag(call: CallbackQuery):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    if not await db.is_user_premium(user_id):
        await call.answer("Faqat Premium foydalanuvchilar Teg tanlay oladi!", show_alert=True)
        return
    u = await db.get_user(user_id) or {}
    cur_tag = u.get("vip_tag") or "PREMIUM"

    txt = (
        f"🏷 <b>ВЫБОР СПЕЦИАЛЬНОГО VIP ТЕГА</b>\n\n"
        f"Ваш текущий тег: <b>[{cur_tag}]</b>\n"
        f"Этот тег отображается рядом с вашим именем в группе <b>Movie Land Group</b>!\n\n"
        f"👇 Выберите готовый тег или напишите свой собственный:"
        if lang == "ru" else
        f"🏷 <b>MAXSUS VIP TEG (UNVON) TANLASH</b>\n\n"
        f"Hozirgi tegingiz: <b>[{cur_tag}]</b>\n"
        f"Ushbu teg <b>Movie Land Group</b> mavzuli guruhida ismingiz yonida ko'rinib turadi!\n\n"
        f"👇 Quyidagi tayyor teglardan birini tanlang yoki o'zingiz xohlagan tegni yozing:"
    )
    await call.message.edit_text(txt, reply_markup=kb.vip_tags_choice_inline(cur_tag, lang=lang), parse_mode="HTML")

@eco_router.callback_query(F.data.startswith("set_vtag:"))
async def cb_set_vtag(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    if not await db.is_user_premium(user_id):
        return
    new_tag = call.data.split(":", 1)[1]
    await db.set_user_vip_tag(user_id, new_tag)
    await apply_vip_tag_across_ecosystem(bot, user_id, new_tag)
    await call.answer(f"✅ [{new_tag}]!", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=kb.vip_tags_choice_inline(new_tag, lang=lang))

@eco_router.callback_query(F.data == "custom_vtag_write")
async def cb_custom_vtag_write(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    if not await db.is_user_premium(user_id):
        return
    await state.set_state(CustomTagState.waiting_tag)
    prompt = (
        "✍️ <b>Напишите желаемый VIP Тег</b> (максимум 15 символов, например: <code>BOSS VIP</code> или <code>PREMIUM</code>):"
        if lang == "ru" else
        "✍️ <b>O'zingiz xohlagan maxsus VIP Tegni yozib yuboring</b> (maksimum 15 ta harf, masalan: <code>BOSS VIP</code> yoki <code>PREMIUM</code>):"
    )
    await call.message.answer(prompt, reply_markup=kb.cancel_keyboard(lang), parse_mode="HTML")
    await call.answer()

@eco_router.message(CustomTagState.waiting_tag, F.text)
async def save_custom_vtag(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    role = await db.get_user_role(user_id)
    if message.text in b_vals("cancel"):
        await state.clear()
        await message.answer(t("cancelled", lang), reply_markup=kb.user_main_keyboard(role, lang=lang))
        return

    await state.clear()
    new_tag = message.text.strip()[:15]
    await db.set_user_vip_tag(user_id, new_tag)
    await apply_vip_tag_across_ecosystem(bot, user_id, new_tag)
    msg = (
        f"✅ <b>Ваш VIP Тег сохранен:</b> <code>[{new_tag}]</code>\n🌐 Тег обновлен в группе Movie Land Group!"
        if lang == "ru" else
        f"✅ <b>Maxsus VIP Tegingiz saqlandi:</b> <code>[{new_tag}]</code>\n🌐 Movie Land Group guruhida tegingiz yangilandi!"
    )
    await message.answer(msg, reply_markup=kb.user_main_keyboard(role, lang=lang), parse_mode="HTML")

@eco_router.callback_query(F.data == "vip_apply_tags_now")
async def cb_vip_apply_tags_now(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    if not await db.is_user_premium(user_id):
        await call.answer("Сначала приобретите Premium!" if lang == "ru" else "Avval Premium oling!", show_alert=True)
        return
    u = await db.get_user(user_id) or {}
    tag = u.get("vip_tag") or "PREMIUM"
    ok = await apply_vip_tag_across_ecosystem(bot, user_id, tag)
    if ok:
        await call.answer(
            f"✅ Тег [{tag}] успешно установлен в Movie Land Group!" if lang == "ru"
            else f"✅ [{tag}] tegingiz Movie Land Group da faollashtirildi!",
            show_alert=True
        )
    else:
        await call.answer(
            "ℹ️ Вступите в группу Movie Land Group и напишите сообщение, чтобы бот выдал вам тег [PREMIUM]!" if lang == "ru"
            else "ℹ️ Movie Land Group ga a'zo bo'ling (va botga guruhda 'Admin qo'shish' huquqi berilganligini tekshiring)!",
            show_alert=True
        )


# ===================== 3. KARTA ORQALI TO'LOV VA «⚡ FAOLIK» BO'LIMIGA TO'LIQ CHEK YUBORISH =====================
@eco_router.callback_query(F.data == "pay_by_card")
async def cb_pay_by_card_choose_plan(call: CallbackQuery):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    p7 = await db.get_setting("vip_7_price", config.DEFAULT_VIP_7_PRICE)
    p30 = await db.get_setting("vip_30_price", config.DEFAULT_VIP_30_PRICE)
    p90 = await db.get_setting("vip_90_price", config.DEFAULT_VIP_90_PRICE)

    txt = (
        "💳 <b>ОПЛАТА КАРТОЙ — ВЫБЕРИТЕ ТАРИФ VIP:</b>\n\n"
        "Выберите тариф, который хотите оплатить:"
        if lang == "ru" else
        "💳 <b>KARTA ORQALI TO'LOV — TARIFNI TANLANG:</b>\n\n"
        "Qaysi VIP tarifni xarid qilmoqchisiz? Quyidan tanlang:"
    )
    await call.message.edit_text(txt, reply_markup=kb.vip_card_plan_select_inline(p7, p30, p90, lang=lang), parse_mode="HTML")
    await call.answer()

@eco_router.callback_query(F.data.startswith("card_plan:"))
async def cb_card_plan_selected(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    lang = await db.get_user_lang(user_id)
    plan_days = int(call.data.split(":")[1])

    price_key = {7: "vip_7_price", 30: "vip_30_price", 90: "vip_90_price"}.get(plan_days, "vip_30_price")
    def_price = {7: config.DEFAULT_VIP_7_PRICE, 30: config.DEFAULT_VIP_30_PRICE, 90: config.DEFAULT_VIP_90_PRICE}.get(plan_days, "25000")
    price = int(await db.get_setting(price_key, def_price))
    card_info = await db.get_setting("payment_card_info", config.DEFAULT_PAYMENT_CARD)

    await state.update_data(card_plan_days=plan_days, card_plan_price=price)
    await state.set_state(CardPaymentState.waiting_receipt)

    if lang == "ru":
        txt = (
            f"💳 <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ КАРТОЙ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Выбранный тариф:</b> VIP на {plan_days} дней\n"
            f"💵 <b>Сумма к оплате:</b> <code>{price:,}</code> сум\n"
            f"🏦 <b>Карта для перевода:</b>\n<code>{card_info}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📸 <i>После перевода отправьте <b>скриншот или фото чека оплаты</b> сюда! Чек с датой и деталями будет передан Супер-Администратору на проверку.</i>"
        )
    else:
        txt = (
            f"💳 <b>KARTA ORQALI TO'LOV REKVIZITLARI</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Tanlangan tarif:</b> {plan_days} kunlik VIP\n"
            f"💵 <b>To'lov summasi:</b> <code>{price:,}</code> so'm\n"
            f"🏦 <b>To'lov uchun karta raqami:</b>\n<code>{card_info}</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📸 <i>To'lovni amalga oshirgach, <b>to'lov cheki (skrinshot)</b> ni shu yerga yuboring! Chek to'liq sanasi bilan «⚡ Faolik» bo'limiga va Super-Adminga yuboriladi.</i>"
        )

    await call.message.answer(txt, reply_markup=kb.cancel_keyboard(lang), parse_mode="HTML")
    await call.answer()

@eco_router.message(CardPaymentState.waiting_receipt, F.photo | F.document)
async def process_payment_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    plan_days = data.get("card_plan_days", 30)
    plan_price = data.get("card_plan_price", 25000)
    await state.clear()

    user_id = message.from_user.id
    lang = await db.get_user_lang(user_id)
    role = await db.get_user_role(user_id)
    card_info = await db.get_setting("payment_card_info", config.DEFAULT_PAYMENT_CARD)
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    chk_id = f"CHK-{now_dt.strftime('%m%d%H%M')}-{str(user_id)[-4:]}"

    cap = (
        f"🧾 <b>YANGI TO'LOV CHEKI KELIB TUSHDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔢 <b>Chek raqami:</b> <code>#{chk_id}</code>\n"
        f"📅 <b>Sana va vaqt:</b> <code>{now_str}</code>\n"
        f"👤 <b>Foydalanuvchi:</b> {message.from_user.full_name} (@{message.from_user.username or 'yoq'})\n"
        f"🆔 <b>Chat ID:</b> <code>{user_id}</code>\n"
        f"💎 <b>So'ralgan tarif:</b> <b>{plan_days} kunlik VIP</b> ({plan_price:,} so'm)\n"
        f"💳 <b>To'lov kartasi:</b> <code>{card_info}</code>\n"
        f"💬 <b>Izoh:</b> {message.caption or 'Kiritilmagan'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👑 <i>Faqat Super Administrator qabul qila oladi yoki rad eta oladi:</i>"
    )
    adm_kb = kb.payment_receipt_superadmin_inline(user_id, plan_days=plan_days)

    # 1. Mavzuli Guruhning «⚡ Активный Faolik» (thread_id=196) bo'limiga to'liq formatda yuboramiz!
    try:
        if message.photo:
            await bot.send_photo(
                chat_id=int(config.MAIN_TOPIC_GROUP_ID),
                message_thread_id=config.TOPIC_ACTIVITY_ID,
                photo=message.photo[-1].file_id,
                caption=cap,
                reply_markup=adm_kb,
                parse_mode="HTML"
            )
        else:
            await bot.send_document(
                chat_id=int(config.MAIN_TOPIC_GROUP_ID),
                message_thread_id=config.TOPIC_ACTIVITY_ID,
                document=message.document.file_id,
                caption=cap,
                reply_markup=adm_kb,
                parse_mode="HTML"
            )
    except Exception as e:
        logging.warning(f"Faolik bo'limiga chek yuborishda xato: {e}")

    # 2. Super Adminlarning lichkasiga ham yuboramiz
    staff_list = await db.get_all_staff()
    for s in staff_list:
        if s.get("role") == "superadmin":
            sid = s["user_id"]
            try:
                if message.photo:
                    await bot.send_photo(sid, message.photo[-1].file_id, caption=cap, reply_markup=adm_kb, parse_mode="HTML")
                else:
                    await bot.send_document(sid, message.document.file_id, caption=cap, reply_markup=adm_kb, parse_mode="HTML")
            except Exception:
                pass

    msg = (
        f"✅ <b>Ваш чек (#{chk_id}) принят и отправлен на проверку!</b>\n"
        f"📅 Дата: <code>{now_str}</code>\n"
        f"После подтверждения Супер-Администратором вам автоматически будет выдан VIP и тег [PREMIUM]!"
        if lang == "ru" else
        f"✅ <b>To'lov chekingiz (#{chk_id}) qabul qilindi va tekshiruvga yuborildi!</b>\n"
        f"📅 Sana: <code>{now_str}</code>\n"
        f"Super-Administrator tasdiqlashi bilan sizga avtomatik 💎 VIP va guruhda [PREMIUM] tegi beriladi!"
    )
    await message.answer(msg, reply_markup=kb.user_main_keyboard(role, lang=lang), parse_mode="HTML")


# ===================== FAQAT SUPER ADMIN UCHUN: CHEKNI QABUL QILISH / RAD ETISH =====================
@eco_router.callback_query(F.data.startswith("sadm_pay_ok:"))
async def cb_sadm_pay_approve(call: CallbackQuery, bot: Bot):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        await call.answer("⛔ Faqat Super Administrator to'lov cheklarini qabul qila oladi!", show_alert=True)
        return

    _, uid_str, days_str = call.data.split(":")
    uid = int(uid_str)
    days = int(days_str)

    await db.extend_user_premium(uid, days)
    await apply_vip_tag_across_ecosystem(bot, uid)

    u = await db.get_user(uid) or {}
    until = (u.get("premium_until") or "")[:10]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        await call.message.edit_caption(
            caption=(
                f"{call.message.caption}\n\n"
                f"✅ <b>TASDIQLANDI ({days} kun VIP berildi)!</b>\n"
                f"👑 Tasdiqladi: <b>{call.from_user.full_name}</b>\n"
                f"🕒 Vaqti: <code>{now_str}</code>"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.answer(f"✅ {days} kunlik VIP berildi!", show_alert=True)

    u_lang = await db.get_user_lang(uid)
    rev_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Оставить отзыв в 💸 Premium" if u_lang == "ru" else "💬 💸 Premium bo'limiga Otziv yozish",
            callback_data="vip_leave_review"
        )],
        [InlineKeyboardButton(
            text="🌐 Войти в Movie Land Group" if u_lang == "ru" else "🌐 Movie Land Group ga kirish",
            url=f"{config.MAIN_TOPIC_GROUP_LINK}/{config.TOPIC_CHAT_ID}"
        )]
    ])

    try:
        if u_lang == "ru":
            await bot.send_message(
                uid,
                f"🎉 <b>ВАШ ЧЕК ОПЛАТЫ ПОДТВЕРЖДЕН!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💎 Вам выдан <b>PREMIUM (VIP) на {days} дней</b> (до <code>{until}</code>)!\n"
                f"🏷 В группе <b>Movie Land Group</b> вам установлен тег <code>[PREMIUM]</code>!\n\n"
                f"💬 <i>Пожалуйста, оставьте свой отзыв о покупке по кнопке ниже!</i>",
                reply_markup=rev_btn,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                uid,
                f"🎉 <b>TO'LOV CHEKINGIZ TASDIQLANDI!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💎 Sizga <b>{days} kun muddatga PREMIUM (VIP)</b> berildi (<code>{until}</code> gacha)!\n"
                f"🏷 <b>Movie Land Group</b> mavzuli guruhida sizga <code>[PREMIUM]</code> tegi o'rnatildi!\n\n"
                f"💬 <i>Quyidagi tugma orqali guruhning 💸 Premium bo'limiga o'z fikringizni (Otziv) qoldiring!</i>",
                reply_markup=rev_btn,
                parse_mode="HTML"
            )
    except Exception:
        pass

@eco_router.callback_query(F.data.startswith("sadm_pay_reject:"))
async def cb_sadm_pay_reject(call: CallbackQuery, bot: Bot):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        await call.answer("⛔ Faqat Super Administrator to'lov cheklarini rad eta oladi!", show_alert=True)
        return

    uid = int(call.data.split(":")[1])
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        await call.message.edit_caption(
            caption=(
                f"{call.message.caption}\n\n"
                f"❌ <b>RAD ETILDI!</b>\n"
                f"👑 Rad etdi: <b>{call.from_user.full_name}</b> ({now_str})"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.answer("❌ Chek rad etildi!", show_alert=True)
    u_lang = await db.get_user_lang(uid)
    try:
        msg = (
            "❌ <b>Отправленный вами чек оплаты был отклонен Супер-Администратором.</b>\nПроверьте правильность чека и отправьте снова."
            if u_lang == "ru" else
            "❌ <b>Yuborgan to'lov chekingiz Super-Administrator tomonidan rad etildi.</b>\nIltimos, to'g'ri chekni qayta tekshirib yuboring."
        )
        await bot.send_message(uid, msg, parse_mode="HTML")
    except Exception:
        pass

@eco_router.callback_query(F.data.startswith("adm_pay_bal:"))
async def cb_adm_pay_bal(call: CallbackQuery, state: FSMContext):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        await call.answer("⛔ Faqat Super Administrator balans qo'sha oladi!", show_alert=True)
        return
    uid = int(call.data.split(":")[1])
    await state.update_data(receipt_uid=uid)
    await state.set_state(AdminReceiptBalState.waiting_amount)
    await call.message.answer(f"💰 Foydalanuvchi (<code>{uid}</code>) balansiga qancha so'm qo'shilsin? Raqam yozing:", reply_markup=kb.cancel_keyboard(), parse_mode="HTML")
    await call.answer()

@eco_router.message(AdminReceiptBalState.waiting_amount)
async def adm_pay_bal_save(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    uid = data["receipt_uid"]
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("❌ Faqat raqam yozing!")
        return
    amt = int(message.text.strip())
    await db.add_user_balance(uid, amt)
    await message.answer(f"✅ <code>{uid}</code> balansiga <b>+{amt:,} so'm</b> qo'shildi!", parse_mode="HTML")
    u_lang = await db.get_user_lang(uid)
    try:
        txt = (
            f"🎉 <b>Ваш платеж подтвержден! На ваш баланс зачислено +{amt:,} сум!</b>"
            if u_lang == "ru" else
            f"🎉 <b>To'lovingiz tasdiqlandi! Balansingizga +{amt:,} so'm qo'shildi!</b>"
        )
        await bot.send_message(uid, txt, parse_mode="HTML")
    except Exception:
        pass


# ===================== 4. YAGONA MAVZULI GURUH (-1002748514315) VA AVTO-TEG =====================
async def send_topic_group_screen(target, user_id: int):
    lang = await db.get_user_lang(user_id)
    is_vip = await db.is_user_premium(user_id)
    u = await db.get_user(user_id) or {}
    user_tag = u.get("vip_tag") or "PREMIUM"

    if lang == "ru":
        vip_txt = (
            f"<blockquote>✅ У вас активен <b>💎 PREMIUM VIP</b>!\nВ группе <b>Movie Land Group</b> рядом с вашим именем сияет тег <b>[{user_tag}]</b>!</blockquote>"
            if is_vip else
            "<blockquote>ℹ️ Все пользователи общаются в единой группе <b>Movie Land Group</b>.\n"
            "💎 <b>Преимущество VIP:</b> автоматический тег <b>[PREMIUM]</b> рядом с вашим именем!</blockquote>"
        )
        text = (
            f"🌐 <b>ТЕМАТИЧЕСКАЯ ГРУППА: MOVIE LAND GROUP</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{vip_txt}\n\n"
            f"📌 <b>Разделы (Топики) нашей группы:</b>\n"
            f"<blockquote>"
            f"• 👑 <b>Чат Muhokama</b> — Общение и обсуждение кино\n"
            f"• ⭐ <b>Buyurtmalar</b> — Стол заказов фильмов\n"
            f"• 💸 <b>Premium</b> — Отзывы покупателей VIP\n"
            f"• 💎 <b>Qoidalar</b> — Правила группы и бота\n"
            f"• ⚡ <b>Faolik</b> — Важные события и сеансы"
            f"</blockquote>\n\n"
            f"👇 <i>Переходите в нужный раздел по кнопкам ниже:</i>"
        )
    else:
        vip_txt = (
            f"<blockquote>✅ Sizda <b>💎 PREMIUM VIP</b> faol!\n<b>Movie Land Group</b> guruhida ismingiz yonida rasmiy <b>[{user_tag}]</b> tegingiz porlab turibdi!</blockquote>"
            if is_vip else
            "<blockquote>ℹ️ Barcha foydalanuvchilar yagona <b>Movie Land Group</b> guruhida suhbatlashadilar.\n"
            "💎 <b>VIP afzalligi:</b> ismingiz yonida rasmiy <b>[PREMIUM]</b> unvonli maxsus teg beriladi!</blockquote>"
        )
        text = (
            f"🌐 <b>RASMIY MAVZULI GURUH: MOVIE LAND GROUP</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{vip_txt}\n\n"
            f"📌 <b>Guruhimizdagi mavzuli bo'limlar:</b>\n"
            f"<blockquote>"
            f"• 👑 <b>Чат Muhokama</b> — Kino muhokamasi va erkin suhbat\n"
            f"• ⭐ <b>Buyurtmalar</b> — Kino buyurtmalar bo'limi\n"
            f"• 💸 <b>Premium</b> — VIP sotib olganlar fikri (Otzivlar)\n"
            f"• 💎 <b>Qoidalar</b> — Guruh va bot qoidalari\n"
            f"• ⚡ <b>Faolik</b> — Yangi a'zolar, VIP xaridlar va seanslar"
            f"</blockquote>\n\n"
            f"👇 <i>Kerakli bo'limga to'g'ridan-to'g'ri o'tish uchun bosing:</i>"
        )

    markup = kb.single_topic_group_user_inline(is_vip=is_vip, user_tag=user_tag, lang=lang)
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await target.message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=markup, parse_mode="HTML")

@eco_router.message(F.text.in_(b_vals("topic_group") + ["🌐 Mavzuli Kanallar"]))
async def user_topic_group_menu(message: Message):
    await send_topic_group_screen(message, message.from_user.id)

@eco_router.callback_query(F.data == "nav:topic_group")
async def cb_nav_topic_group(call: CallbackQuery):
    await call.answer()
    await send_topic_group_screen(call, call.from_user.id)

# Mavzuli guruhda (-1002748514315) xabar yozgan userning PREMIUM holatini tekshirish:
# - Agar PREMIUM bo'lsa va hali tegi yo'q bo'lsa -> avtomatik [PREMIUM] teg beradi!
# - Agar PREMIUM muddati tugagan bo'lsa-yu tegi qolib ketgan bo'lsa -> darhol tegini olib tashlaydi!
@eco_router.message(F.chat.type.in_({"group", "supergroup"}))
async def auto_sync_vip_tag_in_topic_group(message: Message, bot: Bot):
    if not message.from_user or message.from_user.is_bot:
        return
    if str(message.chat.id) != str(config.MAIN_TOPIC_GROUP_ID):
        return
    uid = message.from_user.id
    is_vip = await db.is_user_premium(uid)
    if is_vip:
        u = await db.get_user(uid) or {}
        tag = (u.get("vip_tag") or "PREMIUM")[:16]
        try:
            member = await bot.get_chat_member(message.chat.id, uid)
            cur_tag = getattr(member, "tag", None)
            if cur_tag != tag:
                await apply_vip_tag_across_ecosystem(bot, uid, tag)
        except Exception:
            pass
    else:
        role = await db.get_user_role(uid)
        if role == "user":
            try:
                member = await bot.get_chat_member(message.chat.id, uid)
                cur_tag = getattr(member, "tag", None)
                if cur_tag or member.status == "administrator":
                    await remove_vip_tag_across_ecosystem(bot, uid)
            except Exception:
                pass

@eco_router.message(F.text.in_(["🌐 Mavzuli Guruh Boshqaruvi", "🌐 Mavzuli Kanallar Boshqaruvi"]))
async def admin_topic_channels_menu(message: Message):
    if not await db.has_permission(message.from_user.id, "channels"):
        await message.answer("⛔ Sizda bu bo'limga ruxsat yo'q!")
        return
    t_channels = await db.get_topic_channels()
    await message.answer(
        f"🌐 <b>YAGONA MAVZULI GURUH EKOTIZIMI BOSHQARUVI</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏷 <b>Guruh:</b> Movie Land Group (<code>{config.MAIN_TOPIC_GROUP_ID}</code>)\n"
        f"🔗 <b>Manzil:</b> {config.MAIN_TOPIC_GROUP_LINK}\n\n"
        f"📌 <b>Avtomatik ulangan Topic ID lar:</b>\n"
        f"• ⚡ Активный Faolik: <code>{config.TOPIC_ACTIVITY_ID}</code> (Muhim seanslar va To'lov cheklari)\n"
        f"• 💸 Premium: <code>{config.TOPIC_PREMIUM_REVIEWS_ID}</code> (Premium olganlardan Otzivlar)\n"
        f"• ⭐ Buyurtmalar: <code>{config.TOPIC_ORDERS_ID}</code> (Kino buyurtmalar)\n"
        f"• 💎 Qoidalar: <code>{config.TOPIC_RULES_ID}</code> (Qoidalar)\n"
        f"• 👑 Чат Muhokama: <code>{config.TOPIC_CHAT_ID}</code> (Muhokama)\n\n"
        f"💡 <i>Eslatma: Bot guruhda a'zolarga avtomatik <b>[PREMIUM]</b> tegini berishi va muddati tugaganda olib tashlashi uchun guruh Admin sozlamalarida botga <b>«Add New Admins / Yangi adminlar qo'shish»</b> huquqini yoqib qo'ying!</i>",
        reply_markup=kb.topic_channels_admin_inline(t_channels),
        parse_mode="HTML"
    )

@eco_router.callback_query(F.data == "adm_sync_all_vip_tags")
async def cb_adm_sync_all_vip_tags(call: CallbackQuery, bot: Bot):
    if not await db.has_permission(call.from_user.id, "vip_manage"):
        return
    vips = await db.get_all_premium_users()
    cnt = 0
    for v in vips:
        ok = await apply_vip_tag_across_ecosystem(bot, v["user_id"], v.get("vip_tag", "PREMIUM"))
        if ok:
            cnt += 1
    await call.answer(f"✅ {cnt} ta VIP foydalanuvchining tegi guruhda yangilandi!", show_alert=True)


# ===================== 5. SUPER ADMIN: IQTISODIYOT, KARTA, NARXLAR VA BONUSLAR =====================
async def render_economy_admin_panel(target):
    free_lim = await db.get_setting("free_order_limit", "1")
    vip_lim = await db.get_setting("premium_order_limit", "5")
    daily_rew = await db.get_setting("daily_reward_amount", config.DEFAULT_DAILY_REWARD)
    ref_rew = await db.get_setting("ref_reward_amount", config.DEFAULT_REF_REWARD)
    p7 = await db.get_setting("vip_7_price", config.DEFAULT_VIP_7_PRICE)
    p30 = await db.get_setting("vip_30_price", config.DEFAULT_VIP_30_PRICE)
    p90 = await db.get_setting("vip_90_price", config.DEFAULT_VIP_90_PRICE)
    card = await db.get_setting("payment_card_info", config.DEFAULT_PAYMENT_CARD)

    text = (
        f"💎 <b>IQTISODIYOT: PREMIUM NARXLARI, KARTA, REFERAL VA DAILY REWARD</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎁 <b>Kunlik Bonus (Daily Reward):</b> {int(daily_rew):,} so'm\n"
        f"👥 <b>1 ta Referal mukofoti:</b> {int(ref_rew):,} so'm\n"
        f"💎 <b>7 kunlik VIP narxi:</b> {int(p7):,} so'm\n"
        f"🔥 <b>30 kunlik VIP narxi:</b> {int(p30):,} so'm\n"
        f"👑 <b>90 kunlik VIP narxi:</b> {int(p90):,} so'm\n"
        f"💳 <b>To'lov kartasi:</b> <code>{card}</code>\n"
        f"🎬 <b>Buyurtma limitlari:</b> Oddiy={free_lim} ta | VIP={vip_lim} ta\n\n"
        f"👇 <i>Istalgan qiymatni (yoki Karta raqamini) o'zgartirish uchun ustiga bosing:</i>"
    )
    markup = kb.vip_economy_admin_inline(free_lim, vip_lim, daily_rew, ref_rew, p7, p30, p90)
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=markup, parse_mode="HTML")

@eco_router.message(F.text == "💎 VIP, Narxlar va Bonuslar")
async def cmd_economy_admin(message: Message):
    if not await db.has_permission(message.from_user.id, "vip_manage"):
        await message.answer("⛔ Ruxsat yo'q!")
        return
    await render_economy_admin_panel(message)

@eco_router.callback_query(F.data.startswith("eco_set:"))
async def cb_eco_set_start(call: CallbackQuery, state: FSMContext):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        await call.answer("Faqat Super Administrator narx, karta va bonuslarni o'zgartira oladi!", show_alert=True)
        return
    s_key = call.data.split(":")[1]
    labels = {
        "daily_reward_amount": "🎁 Kunlik Bonus summasini kiriting (so'mda, masalan: 1000):",
        "ref_reward_amount": "👥 1 ta Referal uchun beriladigan summani kiriting (so'mda, masalan: 1500):",
        "vip_7_price": "💎 7 kunlik VIP narxini kiriting (so'mda, masalan: 10000):",
        "vip_30_price": "🔥 30 kunlik VIP narxini kiriting (so'mda, masalan: 25000):",
        "vip_90_price": "👑 90 kunlik VIP narxini kiriting (so'mda, masalan: 60000):",
        "payment_card_info": "💳 To'lov uchun Karta raqami va Karta egasi F.I.Sh ni kiriting (masalan: 9860 1234 5678 9012 — Asliddin):"
    }
    await state.update_data(eco_key=s_key)
    await state.set_state(EconomySettingState.waiting_value)
    await call.message.answer(labels.get(s_key, "Yangi qiymatni kiriting:"), reply_markup=kb.cancel_keyboard())
    await call.answer()

@eco_router.message(EconomySettingState.waiting_value)
async def eco_set_save(message: Message, state: FSMContext):
    if message.text in b_vals("cancel"):
        await state.clear()
        await message.answer("✅ Bekor qilindi.", reply_markup=kb.super_admin_keyboard())
        return
    data = await state.get_data()
    s_key = data["eco_key"]
    val = message.text.strip()

    if s_key != "payment_card_info":
        val_clean = val.replace(" ", "").replace(",", "")
        if not val_clean.isdigit():
            await message.answer("❌ Faqat raqam kiriting!")
            return
        val = val_clean

    await db.set_setting(s_key, val)
    await state.clear()
    await message.answer("✅ Sozlama muvaffaqiyatli yangilandi!", reply_markup=kb.super_admin_keyboard())
    await render_economy_admin_panel(message)

@eco_router.callback_query(F.data == "eco_user_bal")
async def cb_eco_user_bal(call: CallbackQuery, state: FSMContext):
    if await db.get_user_role(call.from_user.id) != "superadmin":
        await call.answer("Faqat Super Administrator balansni o'zgartira oladi!", show_alert=True)
        return
    await state.set_state(EconomySettingState.waiting_user_bal)
    await call.message.answer(
        "💰 Foydalanuvchi balansini o'zgartirish uchun quyidagi formatda yuboring:\n"
        "<code>CHAT_ID | SUMMA</code>\n\n"
        "Masalan: <code>123456789 | 25000</code> (ayirish uchun: <code>123456789 | -5000</code>)",
        reply_markup=kb.cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@eco_router.message(EconomySettingState.waiting_user_bal)
async def eco_user_bal_save(message: Message, state: FSMContext):
    await state.clear()
    parts = [p.strip() for p in message.text.split("|")]
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].lstrip("-").isdigit():
        await message.answer("❌ Noto'g'ri format!", reply_markup=kb.super_admin_keyboard())
        return
    uid = int(parts[0])
    amt = int(parts[1])
    await db.add_user_balance(uid, amt)
    u = await db.get_user(uid) or {}
    await message.answer(
        f"✅ Foydalanuvchi (<code>{uid}</code>) balansi yangilandi!\n"
        f"💰 Joriy balansi: <b>{u.get('balance', 0):,} so'm</b>",
        reply_markup=kb.super_admin_keyboard(),
        parse_mode="HTML"
    )
