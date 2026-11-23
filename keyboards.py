from urllib.parse import quote
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
import config
from i18n import BTN


def _detect_custom_emoji_id(text: str) -> str | None:
    """Tugma matnidagi emojiga mos rasmiy Telegram Premium Custom Emoji ID ni topadi."""
    if not text:
        return None
    for em, eid in config.PREMIUM_EMOJI_MAP.items():
        if text.startswith(em):
            return eid
    for em, eid in config.PREMIUM_EMOJI_MAP.items():
        if em in text:
            return eid
    return None


def ibtn(text: str, style: str | None = None, icon_custom_emoji_id: str | None = "AUTO", **kwargs) -> InlineKeyboardButton:
    """Simmetrik rangli (style) va Premium Custom Emojili (icon_custom_emoji_id) Inline tugma yaratuvchi."""
    if icon_custom_emoji_id == "AUTO":
        icon_custom_emoji_id = _detect_custom_emoji_id(text)
    return InlineKeyboardButton(
        text=text,
        style=style,
        icon_custom_emoji_id=icon_custom_emoji_id,
        **kwargs
    )


def kbtn(text: str, style: str | None = None, icon_custom_emoji_id: str | None = "AUTO", **kwargs) -> KeyboardButton:
    """Premium Custom Emojili va rangli Reply tugma yaratuvchi."""
    if icon_custom_emoji_id == "AUTO":
        icon_custom_emoji_id = _detect_custom_emoji_id(text)
    return KeyboardButton(
        text=text,
        style=style,
        icon_custom_emoji_id=icon_custom_emoji_id,
        **kwargs
    )


# ===================== 0. TIL TANLASH INLINE =====================
def language_select_inline(movie_code: str = None):
    suffix = f":{movie_code}" if movie_code else ""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ibtn(text="🇺🇿 O'zbek tili", callback_data=f"set_lang:uz{suffix}", style="primary"),
                ibtn(text="🇷🇺 Русский язык", callback_data=f"set_lang:ru{suffix}")
            ]
        ]
    )


# ===================== 1. FOYDALANUVCHI IXCHAM REPLY VA INLINE PANELI (UZ / RU) =====================
def user_main_keyboard(role: str = "user", lang: str = "uz"):
    lang = "ru" if lang == "ru" else "uz"
    kb = [
        [
            kbtn(text=BTN["cabinet"][lang]),
            kbtn(text=BTN["lang"][lang])
        ]
    ]
    if role == "superadmin":
        kb.append([
            kbtn(text="👮 Admin Panel", style="primary"),
            kbtn(text="👑 SUPER ADMIN PANEL", style="danger")
        ])
    elif role in ("moderator", "admin"):
        kb.append([kbtn(text="👮 Admin Panel", style="primary")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def user_inline_dashboard(lang: str = "uz", webapp_url: str = None):
    """Bosh sahifadagi ixcham, simmetrik, toza rangli Ultimate Inline Menyu."""
    lang = "ru" if lang == "ru" else "uz"
    search_lbl = "🔍 Поиск фильмов" if lang == "ru" else "🔍 Kino qidirish"
    webapp_lbl = "🎬 Movie Land WebApp"
    ai_lbl = "🤖 Movie Land AI"
    w_url = (webapp_url or config.WEBAPP_URL).strip()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ibtn(text=search_lbl, switch_inline_query_current_chat="", style="primary")
            ],
            [
                ibtn(text=webapp_lbl, web_app=WebAppInfo(url=w_url), style="success"),
                ibtn(text=ai_lbl, callback_data="nav:ai", style="primary")
            ],
            [
                ibtn(text=BTN["top"][lang], switch_inline_query_current_chat="top"),
                ibtn(text=BTN["new"][lang], switch_inline_query_current_chat="new")
            ],
            [
                ibtn(text=BTN["genres"][lang], callback_data="nav:genres"),
                ibtn(text=BTN["serials"][lang], switch_inline_query_current_chat="serial")
            ],
            [
                ibtn(text=BTN["random"][lang], callback_data="nav:random"),
                ibtn(text=BTN["favs"][lang], callback_data="nav:favs")
            ],
            [
                ibtn(text=BTN["vip_shop"][lang], callback_data="open_vip_shop"),
                ibtn(text=BTN["earn"][lang], callback_data="go_earn_menu")
            ],
            [
                ibtn(text=BTN["order"][lang], callback_data="nav:order"),
                ibtn(text=BTN["topic_group"][lang], callback_data="nav:topic_group")
            ],
            [
                ibtn(text=BTN["cabinet"][lang], callback_data="nav:cabinet"),
                ibtn(text=BTN["lang"][lang], callback_data="nav:lang")
            ]
        ]
    )


def movie_land_ai_inline(recommended_movies: list = None, lang: str = "uz"):
    """Movie Land AI yordamchisi uchun tezkor tavsiya va kino ochish tugmalari."""
    rows = []
    if recommended_movies:
        for m in recommended_movies[:6]:
            badge = "📺" if m.get("is_serial") else "🎬"
            m_name = str(m.get("name", ""))[:30]
            rows.append([
                ibtn(
                    text=f"{badge} #{m['code']} — {m_name} ({m.get('year', '')})",
                    callback_data=f"open_mov:{m['code']}",
                    style="success"
                )
            ])
    else:
        if lang == "ru":
            rows.extend([
                [
                    ibtn(text="🔥 Лучшие боевики", callback_data="ai_quick:боевик топ"),
                    ibtn(text="😂 Смешная комедия", callback_data="ai_quick:комедия")
                ],
                [
                    ibtn(text="📺 Посоветуй сериал", callback_data="ai_quick:сериал"),
                    ibtn(text="🚀 Фантастика", callback_data="ai_quick:фантастика")
                ]
            ])
        else:
            rows.extend([
                [
                    ibtn(text="🔥 Eng zo'r jangari", callback_data="ai_quick:eng zor jangari kino"),
                    ibtn(text="😂 Kulgili komediya", callback_data="ai_quick:kulgili komediya kino")
                ],
                [
                    ibtn(text="📺 Zo'r serial tavsiya qil", callback_data="ai_quick:zor serial tavsiya qil"),
                    ibtn(text="🚀 Fantastika va sehr", callback_data="ai_quick:fantastika sehrgar kino")
                ]
            ])
    exit_lbl = "🔙 Выйти из AI" if lang == "ru" else "🔙 AI dan chiqish"
    rows.append([ibtn(text=exit_lbl, callback_data="exit_ai_mode", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ===================== 2. MODERATOR VA ADMINISTRATOR PANELI =====================
def staff_panel_keyboard(perms: list, is_super: bool = False):
    kb = []

    if is_super or "archive_load" in perms or "add_movie" in perms:
        kb.append([
            kbtn(text="🗂 Arxiv boshqaruvi va Chala postlar"),
            kbtn(text="📥 Bazadan Kino yuklash")
        ])
        kb.append([kbtn(text="📺 Bazadan Serial yuklash")])

    if is_super or "add_movie" in perms:
        kb.append([kbtn(text="➕ Kino qo'shish (Pro)"), kbtn(text="⚡ Tezkor kino qo'shish")])
        kb.append([kbtn(text="🎞 Serial qismi qo'shish")])

    row2 = []
    if is_super or "del_movie" in perms:
        row2.append(kbtn(text="🗑 Kino o'chirish"))
    if is_super or "orders" in perms:
        row2.append(kbtn(text="📩 Kino buyurtmalar"))
    if row2:
        kb.append(row2)

    row3 = []
    if is_super or "channels" in perms:
        row3.append(kbtn(text="📢 Kanallarni boshqarish"))
        row3.append(kbtn(text="🌐 Mavzuli Guruh Boshqaruvi"))
    if row3:
        kb.append(row3)

    row4 = []
    if is_super or "stats" in perms:
        row4.append(kbtn(text="📊 Statistika"))
    if is_super or "broadcast" in perms:
        row4.append(kbtn(text="✉️ Xabar yuborish"))
    if row4:
        kb.append(row4)

    row5 = []
    if is_super or "users_ban" in perms:
        row5.append(kbtn(text="🚫 User qidirish va Ban"))
    if is_super or "vip_manage" in perms:
        row5.append(kbtn(text="💎 VIP, Narxlar va Bonuslar"))
    if row5:
        kb.append(row5)

    if is_super:
        kb.append([kbtn(text="👑 SUPER ADMIN PANEL", style="danger")])

    kb.append([kbtn(text="🏠 Foydalanuvchi menyusi", style="success")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ===================== 3. SUPER ADMINISTRATOR PANELI (/spanel, /sadmin) =====================
def super_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [kbtn(text="🗂 Arxiv boshqaruvi va Chala postlar"), kbtn(text="📥 Bazadan Kino yuklash")],
            [kbtn(text="📺 Bazadan Serial yuklash"), kbtn(text="🗑 Faqat kinolar bazasini tozalash")],
            [kbtn(text="🌐 WebApp Admin", style="primary"), kbtn(text="🖥 Server Holati va CPU Analiz")],
            [kbtn(text="👁 Kinolarga Ko'rish qo'shish"), kbtn(text="📊 Kengaytirilgan Statistika")],
            [kbtn(text="🌐 Mavzuli Guruh Boshqaruvi"), kbtn(text="💎 VIP, Narxlar va Bonuslar")],
            [kbtn(text="👮 Lavozim va Ruxsatlar"), kbtn(text="🧠 Top-15 AI Tizimi")],
            [kbtn(text="💾 Backup va Export/Import"), kbtn(text="⚙️ Texnik Sozlamalar va Himoya")],
            [kbtn(text="🧹 Kesh va __pycache__ tozalash"), kbtn(text="🔐 Super-Parolni o'zgartirish")],
            [kbtn(text="👮 Admin Panel", style="primary"), kbtn(text="🏠 Foydalanuvchi menyusi", style="success")]
        ],
        resize_keyboard=True
    )

def cancel_keyboard(lang: str = "uz"):
    lang = "ru" if lang == "ru" else "uz"
    return ReplyKeyboardMarkup(
        keyboard=[[kbtn(text=BTN["cancel"][lang], style="danger")]],
        resize_keyboard=True
    )

def skip_or_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [kbtn(text="⏭ O'tkazib yuborish", style="primary")],
            [kbtn(text="❌ Bekor qilish", style="danger")]
        ],
        resize_keyboard=True
    )

def channels_manage_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [kbtn(text="📢 Ochiq kanal qo'shish"), kbtn(text="🔒 Zayavkali kanal qo'shish")],
            [kbtn(text="🌐 Ijtimoiy tarmoq havolasi"), kbtn(text="➖ Kanal o'chirish")],
            [kbtn(text="📋 Kanallar ro'yxati")],
            [kbtn(text="👮 Admin Panel")]
        ],
        resize_keyboard=True
    )


# ===================== 4. KUNLIK BONUS VA PUL ISHLASH INLINE (UZ / RU) =====================
def earn_money_inline(ref_link: str, daily_amount: str, ref_amount: str, lang: str = "uz"):
    if lang == "ru":
        share_url = f"https://t.me/share/url?url={ref_link}&text=🎬 Лучший бот фильмов и сериалов! Заходи, получай ежедневный бонус и бесплатный VIP!"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [ibtn(text=f"🎁 Ежедневный бонус (+{int(daily_amount):,} сум)", callback_data="claim_daily", style="primary")],
                [ibtn(text=f"📲 Пригласить друзей (+{int(ref_amount):,} сум)", url=share_url)],
                [
                    ibtn(text="💎 VIP Магазин", callback_data="open_vip_shop"),
                    ibtn(text="🏆 Рейтинг", callback_data="show_leaderboard")
                ],
                [ibtn(text="🔙 Назад", callback_data="back_main_menu")]
            ]
        )
    share_url = f"https://t.me/share/url?url={ref_link}&text=🎬 Eng yangi kinolar va seriallar botiga kiring, kunlik bonus oling va bepul VIP yuting!"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text=f"🎁 Kunlik Bonus (+{int(daily_amount):,} so'm)", callback_data="claim_daily", style="primary")],
            [ibtn(text=f"📲 Do'stlarni taklif qilish (+{int(ref_amount):,} so'm)", url=share_url)],
            [
                ibtn(text="💎 VIP Do'kon", callback_data="open_vip_shop"),
                ibtn(text="🏆 Top Reyting", callback_data="show_leaderboard")
            ],
            [ibtn(text="🔙 Orqaga", callback_data="back_main_menu")]
        ]
    )


# ===================== 5. FOYDALANUVCHI VIP DO'KON, KARTA VA OTZIV INLINE (UZ / RU) =====================
def user_vip_shop_inline(p7: str, p30: str, p90: str, is_vip: bool = False, cur_tag: str = "PREMIUM", lang: str = "uz", show_extend: bool = False):
    if lang == "ru":
        if is_vip and not show_extend:
            return InlineKeyboardMarkup(inline_keyboard=[
                [ibtn(text=f"🏷 VIP Тег: [{cur_tag}]", callback_data="vip_choose_tag", style="primary")],
                [
                    ibtn(text="⚡ Включить тег", callback_data="vip_apply_tags_now"),
                    ibtn(text="💬 Отзыв", callback_data="vip_leave_review")
                ],
                [ibtn(text="🔄 Продлить VIP подписку", callback_data="vip_extend_menu")],
                [ibtn(text="🔙 Назад", callback_data="back_main_menu")]
            ])
        buttons = [
            [ibtn(text=f"💎 7 дней VIP ✦ {int(p7):,} сум", callback_data="buy_vip:7")],
            [ibtn(text=f"🔥 30 дней VIP ✦ {int(p30):,} сум", callback_data="buy_vip:30", style="primary")],
            [ibtn(text=f"👑 90 дней VIP ✦ {int(p90):,} сум", callback_data="buy_vip:90")],
            [
                ibtn(text="💳 Оплата картой", callback_data="pay_by_card"),
                ibtn(text="🎁 Бонусы", callback_data="go_earn_menu")
            ],
            [ibtn(text="🔙 Назад", callback_data="open_vip_shop" if is_vip else "back_main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    if is_vip and not show_extend:
        return InlineKeyboardMarkup(inline_keyboard=[
            [ibtn(text=f"🏷 VIP Tegim: [{cur_tag}]", callback_data="vip_choose_tag", style="primary")],
            [
                ibtn(text="⚡ Tegni yoqish", callback_data="vip_apply_tags_now"),
                ibtn(text="💬 Otziv yozish", callback_data="vip_leave_review")
            ],
            [ibtn(text="🔄 VIP muddatini uzaytirish", callback_data="vip_extend_menu")],
            [ibtn(text="🔙 Orqaga", callback_data="back_main_menu")]
        ])

    buttons = [
        [ibtn(text=f"💎 7 Kunlik VIP ✦ {int(p7):,} so'm", callback_data="buy_vip:7")],
        [ibtn(text=f"🔥 30 Kunlik VIP ✦ {int(p30):,} so'm", callback_data="buy_vip:30", style="primary")],
        [ibtn(text=f"👑 90 Kunlik VIP ✦ {int(p90):,} so'm", callback_data="buy_vip:90")],
        [
            ibtn(text="💳 Karta orqali to'lov", callback_data="pay_by_card"),
            ibtn(text="🎁 Bonus yig'ish", callback_data="go_earn_menu")
        ],
        [ibtn(text="🔙 Orqaga", callback_data="open_vip_shop" if is_vip else "back_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_card_plan_select_inline(p7: str, p30: str, p90: str, lang: str = "uz"):
    if lang == "ru":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [ibtn(text=f"💎 7 дней VIP — {int(p7):,} сум", callback_data="card_plan:7", style="primary")],
                [ibtn(text=f"🔥 30 дней VIP — {int(p30):,} сум", callback_data="card_plan:30", style="danger")],
                [ibtn(text=f"👑 90 дней VIP — {int(p90):,} сум", callback_data="card_plan:90", style="success")],
                [ibtn(text="🔙 Назад", callback_data="open_vip_shop")]
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text=f"💎 7 kunlik VIP — {int(p7):,} so'm", callback_data="card_plan:7", style="primary")],
            [ibtn(text=f"🔥 30 kunlik VIP — {int(p30):,} so'm", callback_data="card_plan:30", style="danger")],
            [ibtn(text=f"👑 90 kunlik VIP — {int(p90):,} so'm", callback_data="card_plan:90", style="success")],
            [ibtn(text="🔙 Orqaga", callback_data="open_vip_shop")]
        ]
    )


def vip_tags_choice_inline(current_tag: str, lang: str = "uz"):
    buttons = []
    row = []
    for t in config.VIP_CUSTOM_TAGS:
        is_cur = (t == current_tag)
        mark = "✅ " if is_cur else "🏷 "
        row.append(ibtn(text=f"{mark}{t}", callback_data=f"set_vtag:{t}", style="success" if is_cur else None))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if lang == "ru":
        buttons.append([ibtn(text="✍️ Свой собственный Тег", callback_data="custom_vtag_write", style="primary")])
        buttons.append([ibtn(text="🔙 Назад", callback_data="open_vip_shop")])
    else:
        buttons.append([ibtn(text="✍️ Maxsus Teg yozish", callback_data="custom_vtag_write", style="primary")])
        buttons.append([ibtn(text="🔙 Orqaga", callback_data="open_vip_shop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_review_stars_inline(lang: str = "uz"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text="⭐⭐⭐⭐⭐ (5/5)", callback_data="rev_star:5", style="success")],
            [ibtn(text="⭐⭐⭐⭐ (4/5)", callback_data="rev_star:4", style="primary")],
            [ibtn(text="⭐⭐⭐ (3/5)", callback_data="rev_star:3")],
            [ibtn(text="🔙 Orqaga", callback_data="open_vip_shop")]
        ]
    )


def payment_receipt_superadmin_inline(user_id: int, plan_days: int = 30):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ibtn(
                    text=f"✅ Tasdiqlash ({plan_days} kun VIP)",
                    callback_data=f"sadm_pay_ok:{user_id}:{plan_days}",
                    style="success"
                )
            ],
            [
                ibtn(text="✅ 7k VIP", callback_data=f"sadm_pay_ok:{user_id}:7", style="success"),
                ibtn(text="✅ 30k VIP", callback_data=f"sadm_pay_ok:{user_id}:30", style="success"),
                ibtn(text="✅ 90k VIP", callback_data=f"sadm_pay_ok:{user_id}:90", style="success")
            ],
            [
                ibtn(text="💰 Balans qo'shish", callback_data=f"adm_pay_bal:{user_id}", style="primary"),
                ibtn(text="❌ Rad etish", callback_data=f"sadm_pay_reject:{user_id}", style="danger")
            ]
        ]
    )


# ===================== 6. YAGONA MAVZULI GURUH (-1002748514315) INLINE =====================
def single_topic_group_user_inline(is_vip: bool, user_tag: str = "PREMIUM", lang: str = "uz"):
    base = config.MAIN_TOPIC_GROUP_LINK
    if lang == "ru":
        buttons = [
            [ibtn(text="👑 Чат Muhokama (Общение)", url=f"{base}/{config.TOPIC_CHAT_ID}", style="primary")],
            [
                ibtn(text="⭐ Заказы", url=f"{base}/{config.TOPIC_ORDERS_ID}"),
                ibtn(text="💸 Отзывы", url=f"{base}/{config.TOPIC_PREMIUM_REVIEWS_ID}")
            ],
            [
                ibtn(text="💎 Правила", url=f"{base}/{config.TOPIC_RULES_ID}"),
                ibtn(text="⚡ Активность", url=f"{base}/{config.TOPIC_ACTIVITY_ID}")
            ]
        ]
        if is_vip:
            buttons.append([ibtn(text=f"🏷 Обновить тег [{user_tag}]", callback_data="vip_apply_tags_now", style="success")])
        else:
            buttons.append([ibtn(text="💎 Получить тег [PREMIUM]", callback_data="open_vip_shop", style="primary")])
        buttons.append([ibtn(text="🔙 Назад", callback_data="back_main_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    buttons = [
        [ibtn(text="👑 Чат Muhokama (Suhbat)", url=f"{base}/{config.TOPIC_CHAT_ID}", style="primary")],
        [
            ibtn(text="⭐ Buyurtmalar", url=f"{base}/{config.TOPIC_ORDERS_ID}"),
            ibtn(text="💸 Premium Otziv", url=f"{base}/{config.TOPIC_PREMIUM_REVIEWS_ID}")
        ],
        [
            ibtn(text="💎 Qoidalar", url=f"{base}/{config.TOPIC_RULES_ID}"),
            ibtn(text="⚡ Faolik", url=f"{base}/{config.TOPIC_ACTIVITY_ID}")
        ]
    ]
    if is_vip:
        buttons.append([ibtn(text=f"🏷 Guruhda [{user_tag}] tegni yoqish", callback_data="vip_apply_tags_now", style="success")])
    else:
        buttons.append([ibtn(text="💎 Guruhda [PREMIUM] tegi olish", callback_data="open_vip_shop", style="primary")])
    buttons.append([ibtn(text="🔙 Orqaga", callback_data="back_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def topic_channels_admin_inline(topic_channels: list):
    base = config.MAIN_TOPIC_GROUP_LINK
    buttons = [
        [ibtn(text="🌐 Movie Land Group (-1002748514315)", url=base, style="primary")],
        [
            ibtn(text="⚡ Faolik (196)", url=f"{base}/{config.TOPIC_ACTIVITY_ID}"),
            ibtn(text="💸 Premium (190)", url=f"{base}/{config.TOPIC_PREMIUM_REVIEWS_ID}")
        ],
        [
            ibtn(text="⭐ Buyurtmalar (193)", url=f"{base}/{config.TOPIC_ORDERS_ID}"),
            ibtn(text="💎 Qoidalar (195)", url=f"{base}/{config.TOPIC_RULES_ID}")
        ],
        [ibtn(text="🔄 Barcha VIP a'zolarga Tegni yangilash", callback_data="adm_sync_all_vip_tags", style="success")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===================== 7. SUPER ADMIN: VIP, NARXLAR VA BONUSLAR BOSHQARUVI INLINE =====================
def vip_economy_admin_inline(
    free_limit: str,
    vip_limit: str,
    daily_rew: str,
    ref_rew: str,
    p7: str,
    p30: str,
    p90: str
):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ibtn(text=f"🎁 Bonus: {int(daily_rew):,}", callback_data="eco_set:daily_reward_amount", style="success"),
                ibtn(text=f"👥 Referal: {int(ref_rew):,}", callback_data="eco_set:ref_reward_amount", style="primary")
            ],
            [
                ibtn(text=f"💎 7k VIP: {int(p7):,}", callback_data="eco_set:vip_7_price"),
                ibtn(text=f"🔥 30k VIP: {int(p30):,}", callback_data="eco_set:vip_30_price")
            ],
            [
                ibtn(text=f"👑 90k VIP: {int(p90):,}", callback_data="eco_set:vip_90_price"),
                ibtn(text="💳 Karta raqam", callback_data="eco_set:payment_card_info", style="primary")
            ],
            [
                ibtn(text=f"👤 Limit: {free_limit}/kun", callback_data="vip_chg_free"),
                ibtn(text=f"💎 VIP Limit: {vip_limit}/kun", callback_data="vip_chg_vip")
            ],
            [
                ibtn(text="💎 VIP berish", callback_data="vip_give", style="success"),
                ibtn(text="❌ VIP olish", callback_data="vip_remove", style="danger")
            ],
            [
                ibtn(text="💰 Balans boshqaruvi", callback_data="eco_user_bal", style="primary"),
                ibtn(text="📋 VIP ro'yxat", callback_data="vip_list")
            ]
        ]
    )


# ===================== 8. ARXIV KANAL BOSHQARUVI INLINE =====================
def archive_center_inline(auto_grab: str, auto_post: str, archive_ch: str, post_ch: str):
    grab_txt = "🟢 Yoqilgan" if auto_grab == "1" else "🔴 O'chirilgan"
    post_txt = "🟢 Yoqilgan" if auto_post == "1" else "🔴 O'chirilgan"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text="📡 Arxiv kanalni to'liq skanerlash", callback_data="arch_scan_channel", style="primary")],
            [ibtn(text="✨ Chala postlarni to'ldirish va tartiblash", callback_data="arch_ai_fix_posts", style="primary")],
            [
                ibtn(text="📥 10 ta kino yuklash", callback_data="arch_load_10", style="success"),
                ibtn(text="📺 1 ta serial yuklash", callback_data="arch_load_1_serial", style="success")
            ],
            [ibtn(text="🗑 Faqat kinolar bazasini tozalash", callback_data="clear_movies_confirm", style="danger")],
            [ibtn(text=f"🤖 Avto-olish: {grab_txt}", callback_data="arch_toggle_grab")],
            [ibtn(text=f"📢 Avto-post: {post_txt}", callback_data="arch_toggle_post")]
        ]
    )


# ===================== 9. GRANULAR PRIVILEGIYA VA RUXSATLAR INLINE =====================
def staff_control_menu_inline(staff_list: list):
    buttons = [
        [ibtn(text="➕ Yangi Moder/Admin tayinlash", callback_data="sadm_add_staff", style="success")]
    ]
    for s in staff_list:
        uid = s["user_id"]
        role = s.get("role", "moderator")
        r_badge = {"moderator": "🛡 Moder", "admin": "👮 Admin", "superadmin": "👑 Super"}.get(role, "🛡 Staff")
        buttons.append([
            ibtn(
                text=f"{r_badge}: {s.get('full_name', 'User')} ({uid})",
                callback_data=f"sadm_edit_staff:{uid}",
                style="primary"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def staff_permissions_inline(target_id: int, current_role: str, user_perms: list):
    if int(target_id) in getattr(config, "OWNER_IDS", {6188085308}):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [ibtn(text="👑 Bot Egasi — Doimiy Super Administrator", callback_data="noop", style="success")],
                [ibtn(text="🔒 O'z lavozimini o'zgartirish himoyalangan", callback_data="noop")],
                [ibtn(text="🔙 Orqaga", callback_data="sadm_back_staff")]
            ]
        )
    buttons = [
        [
            ibtn(
                text=("✅ " if current_role == "moderator" else "") + "🛡 Moderator",
                callback_data=f"setrole:{target_id}:moderator",
                style="success" if current_role == "moderator" else None
            ),
            ibtn(
                text=("✅ " if current_role == "admin" else "") + "👮 Admin",
                callback_data=f"setrole:{target_id}:admin",
                style="success" if current_role == "admin" else None
            ),
            ibtn(
                text=("✅ " if current_role == "superadmin" else "") + "👑 Super",
                callback_data=f"setrole:{target_id}:superadmin",
                style="success" if current_role == "superadmin" else None
            )
        ]
    ]

    for perm_key, perm_label in config.PERMISSIONS.items():
        has_it = (current_role == "superadmin") or (perm_key in user_perms)
        status_icon = "✅" if has_it else "❌"
        buttons.append([
            ibtn(
                text=f"{perm_label}: {status_icon}",
                callback_data=f"togperm:{target_id}:{perm_key}",
                style="success" if has_it else None
            )
        ])

    buttons.append([
        ibtn(text="🗑 Huquqlarni olib tashlash (Oddiy User)", callback_data=f"setrole:{target_id}:user", style="danger")
    ])
    buttons.append([
        ibtn(text="🔙 Orqaga", callback_data="sadm_back_staff")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===================== 10. TOP-15 AI VA BACKUP INLINE =====================
def ai_dashboard_inline(ai_enabled: str, active_prov: str, configured_keys: dict):
    status_txt = "🟢 YOQILGAN" if ai_enabled == "1" else "🔴 O'CHIRILGAN"
    active_name = config.TOP_15_AI_PROVIDERS.get(active_prov, {}).get("name", active_prov)

    buttons = [
        [ibtn(text=f"⚡ AI holati: {status_txt}", callback_data="ai_toggle_status")],
        [ibtn(text=f"🎯 Tanlangan: {active_name}", callback_data="ai_noop", style="primary")],
        [ibtn(text="🪄 Bazadagi kinolarni AI da to'ldirish", callback_data="ai_run_batch", style="success")]
    ]

    for p_key, p_info in config.TOP_15_AI_PROVIDERS.items():
        has_key = "🔑 Token" if configured_keys.get(p_key) else "⚙️ Ichki"
        is_sel = "🎯 " if p_key == active_prov else ""
        buttons.append([
            ibtn(
                text=f"{is_sel}{p_info['name']} [{has_key}]",
                callback_data=f"ai_select:{p_key}",
                style="success" if p_key == active_prov else None
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def ai_provider_detail_inline(p_key: str, has_token: bool):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text="🔑 API Token kiritish", callback_data=f"ai_setkey:{p_key}", style="primary")],
            [ibtn(text="✅ Asosiy qilib yoqish", callback_data=f"ai_activate:{p_key}", style="success")],
            [ibtn(text="🧪 Test qilish", callback_data=f"ai_test:{p_key}")],
            [ibtn(text="🔙 Orqaga", callback_data="ai_back_main")]
        ]
    )

def backup_center_inline(auto_hours: str):
    if auto_hours == "168":
        h_txt = "Har haftada (168s)"
    elif auto_hours != "0":
        h_txt = f"Har {auto_hours} soatda"
    else:
        h_txt = "O'chirilgan"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text="📤 Arxiv Guruhga Backup Yuborish", callback_data="bkp_send_archive_now", style="success")],
            [ibtn(text="📥 Bazani yuklab olish (database.db)", callback_data="bkp_download_db", style="primary")],
            [
                ibtn(text="📦 JSON Export", callback_data="bkp_export_json"),
                ibtn(text="📊 CSV Export", callback_data="bkp_export_csv")
            ],
            [ibtn(text="📤 Baza Import (.json / .db)", callback_data="bkp_import_start", style="primary")],
            [ibtn(text=f"⏰ Avto-Backup: {h_txt}", callback_data="bkp_toggle_auto")]
        ]
    )


# ===================== 11. UMUMIY VA KINO INLINE TUGMALARI (UZ / RU) =====================
def subscription_keyboard(channels: list, movie_code: str = None, lang: str = "uz"):
    buttons = []
    for i, ch in enumerate(channels, start=1):
        ch_type = ch.get("ch_type", "public")
        icon = "🔒" if ch_type == "request" else ("🌐" if ch_type == "url" else "📢")
        btn_text = f"{icon} {ch.get('title') or f'{i}-kanal'}"
        link = ch.get("invite_link", "")
        if not link.startswith("http"):
            link = f"https://t.me/{link.lstrip('@')}"
        buttons.append([ibtn(text=btn_text, url=link, style="primary")])

    cb_data = f"check_sub:{movie_code}" if movie_code else "check_sub"
    chk_txt = "✅ Я подписался / Проверить" if lang == "ru" else "✅ A'zo bo'ldim / Tekshirish"
    buttons.append([ibtn(text=chk_txt, callback_data=cb_data, style="success")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def genres_inline_keyboard(for_admin: bool = False, lang: str = "uz"):
    buttons = []
    if for_admin:
        buttons.append([ibtn(text="🤖 AI o'zi aniqlasin (Avto)", callback_data="adm_genre:auto", style="primary")])
    row = []
    for g in config.GENRES:
        if for_admin:
            row.append(ibtn(text=g, callback_data=f"adm_genre:{g}", style=None))
        else:
            row.append(ibtn(text=g, switch_inline_query_current_chat=g, style="primary"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not for_admin:
        back_txt = "🔙 Назад" if lang == "ru" else "🔙 Orqaga"
        buttons.append([ibtn(text=back_txt, callback_data="back_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def quality_inline_keyboard():
    qualities = ["480p SD", "720p HD", "1080p Full HD", "4K Ultra HD"]
    buttons = [
        [ibtn(text="🤖 AI o'zi aniqlasin (Avto)", callback_data="adm_qual:auto", style="primary")],
        [ibtn(text=q, callback_data=f"adm_qual:{q}", style=None) for q in qualities[:2]],
        [ibtn(text=q, callback_data=f"adm_qual:{q}", style="success") for q in qualities[2:]]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def movie_poster_card_keyboard(
    movie: dict,
    bot_username: str,
    is_fav: bool = False,
    episodes: list = None,
    user_perms: list = None,
    lang: str = "uz",
    user_rating: int = 0,
    ep_page: int = 1,
    current_ep: int = None
):
    """
    Poster Card klaviaturasi — rangli (style) va Premium Custom Emojili (icon_custom_emoji_id)!
    Tanlangan qism yashil (success) rangda ▶️ N bo'lib yonib turadi.
    """
    code = movie["code"]
    user_perms = user_perms or []
    episodes = episodes or []
    buttons = []

    total_eps = len(episodes)
    if total_eps <= 1:
        watch_lbl = "▶️ Смотреть фильм" if lang == "ru" else "▶️ Kino ko'rish"
        buttons.append([
            ibtn(text=watch_lbl, callback_data=f"watch:{code}:1", style="success")
        ])
    elif 2 <= total_eps <= 3:
        ep_word = "ч." if lang == "ru" else "qism"
        watch_prefix = "▶️ Смотреть" if lang == "ru" else "▶️ Kino ko'rish"
        for ep in episodes:
            ep_num = ep["episode_num"]
            is_cur = bool(current_ep and ep_num == current_ep)
            play_icon = "▶️ " if is_cur else ""
            buttons.append([
                ibtn(
                    text=f"{play_icon}{watch_prefix} ({ep_num}-{ep_word})",
                    callback_data=f"watch:{code}:{ep_num}",
                    style="success" if is_cur else "primary"
                )
            ])
    else:
        per_page = 30
        total_pages = max(1, (total_eps + per_page - 1) // per_page)
        if current_ep:
            ep_page = max(1, min((current_ep - 1) // per_page + 1, total_pages))
        else:
            ep_page = max(1, min(ep_page, total_pages))

        start_idx = (ep_page - 1) * per_page
        page_eps = episodes[start_idx : start_idx + per_page]

        row = []
        for ep in page_eps:
            ep_num = ep["episode_num"]
            is_cur = bool(current_ep and ep_num == current_ep)
            btn_txt = f"▶️ {ep_num}" if is_cur else f"{ep_num}"
            row.append(
                InlineKeyboardButton(
                    text=btn_txt,
                    callback_data=f"watch:{code}:{ep_num}",
                    style="success" if is_cur else None,
                    icon_custom_emoji_id=config.PREMIUM_EMOJI_MAP["▶️"] if is_cur else None
                )
            )
            if len(row) == 5:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        if total_pages > 1:
            nav_row = []
            if ep_page > 1:
                nav_row.append(ibtn(text="⬅️ Oldingi", callback_data=f"eppage:{code}:{ep_page - 1}", style="primary"))
            nav_row.append(InlineKeyboardButton(text=f"📄 {ep_page}/{total_pages}", callback_data="noop"))
            if ep_page < total_pages:
                nav_row.append(ibtn(text="Keyingi ➡️", callback_data=f"eppage:{code}:{ep_page + 1}", style="primary"))
            buttons.append(nav_row)

    # 5 talik yulduzcha baholash qatori
    star_row = []
    for s in range(1, 6):
        is_sel = (user_rating == s)
        lbl = f"🌟 {s}" if is_sel else f"⭐ {s}"
        star_row.append(
            InlineKeyboardButton(
                text=lbl,
                callback_data=f"rate:{code}:{s}",
                style="success" if is_sel else None,
                icon_custom_emoji_id=config.PREMIUM_EMOJI_MAP["🌟" if is_sel else "⭐"]
            )
        )
    buttons.append(star_row)

    deep_link_enc = quote(f"https://t.me/{bot_username}?start={code}")
    if lang == "ru":
        fav_text = "✅ В избранном" if is_fav else "⭐ Сохранить"
        share_txt = "↗️ Поделиться"
        share_cap_enc = quote(f"🎬 {movie['name']} — Смотрите в боте!")
        share_url = f"https://t.me/share/url?url={deep_link_enc}&text={share_cap_enc}"
    else:
        fav_text = "✅ Saqlangan" if is_fav else "⭐ Saqlash"
        share_txt = "↗️ Ulashish"
        share_cap_enc = quote(f"🎬 {movie['name']} — Bot orqali tomosha qiling!")
        share_url = f"https://t.me/share/url?url={deep_link_enc}&text={share_cap_enc}"

    buttons.append([
        ibtn(text=fav_text, callback_data=f"fav:{code}", style="success" if is_fav else None),
        ibtn(text=share_txt, url=share_url)
    ])

    adm_row1 = []
    if "add_movie" in user_perms or "autopost" in user_perms:
        has_pic = "🖼 Rasm yangilash" if movie.get("photo_id") else "🖼 Rasm qo'shish"
        adm_row1.append(ibtn(text=has_pic, callback_data=f"editpic:{code}"))
    if "autopost" in user_perms:
        adm_row1.append(ibtn(text="📢 Kanalga Post", callback_data=f"autopost:{code}"))
    if adm_row1:
        buttons.append(adm_row1)

    adm_row2 = []
    if "add_movie" in user_perms:
        adm_row2.append(ibtn(text="➕ Qism ulash", callback_data=f"addep:{code}"))
    if "del_movie" in user_perms:
        adm_row2.append(ibtn(text="🗑 O'chirish", callback_data=f"delmov:{code}"))
    if adm_row2:
        buttons.append(adm_row2)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def movie_action_keyboard(
    movie: dict,
    bot_username: str,
    is_fav: bool = False,
    episodes: list = None,
    current_ep: int = 1,
    user_perms: list = None,
    lang: str = "uz",
    user_rating: int = 0
):
    code = movie["code"]
    user_perms = user_perms or []
    buttons = []

    if episodes and len(episodes) > 1:
        total_eps = len(episodes)
        idx = 0
        for i, ep in enumerate(episodes):
            if ep["episode_num"] == current_ep:
                idx = i
                break

        if total_eps <= 3:
            ep_row = []
            ep_word = "серия" if lang == "ru" else "qism"
            for ep in episodes:
                ep_num = ep["episode_num"]
                is_cur = (ep_num == current_ep)
                label = f"▶️ {ep_num}-{ep_word}" if is_cur else f"{ep_num}-{ep_word}"
                ep_row.append(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"ep:{code}:{ep_num}",
                        style="success" if is_cur else None,
                        icon_custom_emoji_id=config.PREMIUM_EMOJI_MAP["▶️"] if is_cur else None
                    )
                )
            buttons.append(ep_row)
        else:
            block_start = (idx // 15) * 15
            window_eps = episodes[block_start : block_start + 15]
            ep_row = []
            for ep in window_eps:
                ep_num = ep["episode_num"]
                is_cur = (ep_num == current_ep)
                label = f"▶️ {ep_num}" if is_cur else f"{ep_num}"
                ep_row.append(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"ep:{code}:{ep_num}",
                        style="success" if is_cur else None,
                        icon_custom_emoji_id=config.PREMIUM_EMOJI_MAP["▶️"] if is_cur else None
                    )
                )
                if len(ep_row) == 5:
                    buttons.append(ep_row)
                    ep_row = []
            if ep_row:
                buttons.append(ep_row)

            if total_eps > 15:
                nav = []
                cur_block = idx // 15
                max_blocks = (total_eps - 1) // 15
                if cur_block > 0:
                    prev_idx = (cur_block - 1) * 15
                    prev_ep = episodes[prev_idx]["episode_num"]
                    nav.append(ibtn(text="⬅️ Oldingi 15", callback_data=f"ep:{code}:{prev_ep}", style="primary"))
                nav.append(InlineKeyboardButton(text=f"🎞 {current_ep}/{total_eps}", callback_data="noop"))
                if cur_block < max_blocks:
                    next_idx = min(total_eps - 1, (cur_block + 1) * 15)
                    next_ep = episodes[next_idx]["episode_num"]
                    nav.append(ibtn(text="Keyingi 15 ➡️", callback_data=f"ep:{code}:{next_ep}", style="primary"))
                buttons.append(nav)

        if total_eps > 1:
            step_row = []
            prev_lbl = "◀️ Предыдущая" if lang == "ru" else "◀️ Oldingi qism"
            next_lbl = "Следующая ⏩" if lang == "ru" else "Keyingi qism ⏩"
            if idx > 0:
                prev_ep = episodes[idx - 1]["episode_num"]
                step_row.append(ibtn(text=prev_lbl, callback_data=f"ep:{code}:{prev_ep}"))
            if idx < total_eps - 1:
                next_ep = episodes[idx + 1]["episode_num"]
                step_row.append(ibtn(text=next_lbl, callback_data=f"ep:{code}:{next_ep}", style="primary"))
            if step_row:
                buttons.append(step_row)

    # 5 talik yulduzcha baholash qatori
    star_row = []
    for s in range(1, 6):
        is_sel = (user_rating == s)
        lbl = f"🌟 {s}" if is_sel else f"⭐ {s}"
        star_row.append(
            InlineKeyboardButton(
                text=lbl,
                callback_data=f"rate:{code}:{s}",
                style="success" if is_sel else None,
                icon_custom_emoji_id=config.PREMIUM_EMOJI_MAP["🌟" if is_sel else "⭐"]
            )
        )
    buttons.append(star_row)

    deep_link_enc = quote(f"https://t.me/{bot_username}?start={code}")
    if lang == "ru":
        fav_text = "✅ В избранном" if is_fav else "⭐ Сохранить"
        share_txt = "↗️ Поделиться"
        share_cap_enc = quote(f"🎬 {movie['name']} — Смотрите в боте!")
        share_url = f"https://t.me/share/url?url={deep_link_enc}&text={share_cap_enc}"
    else:
        fav_text = "✅ Saqlangan" if is_fav else "⭐ Saqlash"
        share_txt = "↗️ Ulashish"
        share_cap_enc = quote(f"🎬 {movie['name']} — Bot orqali tomosha qiling!")
        share_url = f"https://t.me/share/url?url={deep_link_enc}&text={share_cap_enc}"

    buttons.append([
        ibtn(text=fav_text, callback_data=f"fav:{code}", style="success" if is_fav else None),
        ibtn(text=share_txt, url=share_url)
    ])

    adm_row1 = []
    if "add_movie" in user_perms or "autopost" in user_perms:
        has_pic = "🖼 Rasm yangilash" if movie.get("photo_id") else "🖼 Rasm qo'shish"
        adm_row1.append(ibtn(text=has_pic, callback_data=f"editpic:{code}"))
    if "autopost" in user_perms:
        adm_row1.append(ibtn(text="📢 Kanalga Post", callback_data=f"autopost:{code}"))
    if adm_row1:
        buttons.append(adm_row1)

    adm_row2 = []
    if "add_movie" in user_perms:
        adm_row2.append(ibtn(text="➕ Qism ulash", callback_data=f"addep:{code}"))
    if "del_movie" in user_perms:
        adm_row2.append(ibtn(text="🗑 O'chirish", callback_data=f"delmov:{code}"))
    if adm_row2:
        buttons.append(adm_row2)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def movies_list_inline(movies: list, title_prefix: str = "🎬", lang: str = "uz", query: str = ""):
    search_lbl = "🔍 Поиск фильмов" if lang == "ru" else "🔍 Kino qidirish"
    back_txt = "🔙 Назад" if lang == "ru" else "🔙 Orqaga"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text=search_lbl, switch_inline_query_current_chat=query, style="primary")],
            [ibtn(text=back_txt, callback_data="back_main_menu")]
        ]
    )

def movies_catalog_paginated_inline(movies: list = None, page: int = 1, total_pages: int = 1, lang: str = "uz"):
    search_lbl = "🔍 Поиск фильмов" if lang == "ru" else "🔍 Kino qidirish"
    back_txt = "🔙 Назад" if lang == "ru" else "🔙 Orqaga"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text=search_lbl, switch_inline_query_current_chat="", style="primary")],
            [ibtn(text=back_txt, callback_data="back_main_menu")]
        ]
    )

def settings_inline_keyboard(protect_content: str, auto_post_channel: str, bot_active: str):
    prot_txt = "🟢 Yoqilgan" if protect_content == "1" else "🔴 O'chirilgan"
    act_txt = "🟢 Faol" if bot_active == "1" else "🔴 Texnik ishlar"
    ch_txt = auto_post_channel if auto_post_channel else "Belgilanmagan"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text=f"🔒 Kontent himoyasi: {prot_txt}", callback_data="toggle_protect")],
            [ibtn(text=f"🤖 Bot holati: {act_txt}", callback_data="toggle_bot_active")],
            [ibtn(text=f"📢 Avto-Post kanali: {ch_txt}", callback_data="set_autopost_ch", style="primary")],
            [
                ibtn(text="🛑 To'xtatish", callback_data="btn_shutdown_bot", style="danger"),
                ibtn(text="🔄 Qayta yuklash", callback_data="btn_restart_bot", style="primary")
            ]
        ]
    )

def order_admin_keyboard(order_id: int, user_id: int, status: str = "pending"):
    rows = []
    if status != "accepted":
        rows.append([
            ibtn(text="⏳ Qabul qilish", callback_data=f"accept_order:{order_id}:{user_id}", style="primary")
        ])
    rows.append([
        ibtn(text="✉️ Javob yuborish", callback_data=f"ans_order:{order_id}:{user_id}", style="primary"),
        ibtn(text="✅ Bajarildi", callback_data=f"done_order:{order_id}", style="success")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ===================== 12. WEBAPP ADMIN PANELI (/web_admin — BOT ICHIDA) =====================
def web_admin_panel_inline(webapp_enabled: str, webapp_url: str, trailers_cnt: int = 0):
    st_lbl = "🟢 WebApp Faol" if webapp_enabled == "1" else "🔴 WebApp O'chirilgan"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(text="🎬 WebApp ni ochib ko'rish", web_app=WebAppInfo(url=webapp_url), style="success")],
            [
                ibtn(text=st_lbl, callback_data="wadm_toggle_status"),
                ibtn(text=f"🎞 Treylerlar ({trailers_cnt})", callback_data="wadm_trailers", style="primary")
            ],
            [
                ibtn(text="🔗 Domen / URL", callback_data="wadm_set_url"),
                ibtn(text="🏷 Sarlavha & Slogan", callback_data="wadm_set_title")
            ],
            [
                ibtn(text="📣 E'lon / Banner", callback_data="wadm_set_banner"),
                ibtn(text="💎 VIP & Referal narxlar", callback_data="wadm_vip_prices")
            ],
            [
                ibtn(text="📊 WebApp Statistika", callback_data="wadm_stats"),
                ibtn(text="🔄 Menyuni sinxronlash", callback_data="wadm_sync_menu", style="primary")
            ],
            [
                ibtn(text="🔐 WebAdmin Parol", callback_data="wadm_change_pass", style="danger")
            ]
        ]
    )


def web_admin_trailers_inline(trailers: list):
    rows = [
        [ibtn(text="➕ Yangi treyler qo'shish", callback_data="wadm_trailer_add", style="success")]
    ]
    for tr in trailers[:15]:
        rows.append([
            ibtn(text=f"🗑 {tr['title']} ({tr.get('year', '')})", callback_data=f"wadm_trailer_del:{tr['id']}", style="danger")
        ])
    rows.append([ibtn(text="🔙 WebApp Admin menyusi", callback_data="wadm_back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
