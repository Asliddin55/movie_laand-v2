from urllib.parse import quote
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import config
from i18n import BTN


# ===================== 0. TIL TANLASH INLINE =====================
def language_select_inline(movie_code: str = None):
    suffix = f":{movie_code}" if movie_code else ""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek tili ✦ UZ", callback_data=f"set_lang:uz{suffix}"),
                InlineKeyboardButton(text="🇷🇺 Русский язык ✦ RU", callback_data=f"set_lang:ru{suffix}")
            ]
        ]
    )


# ===================== 1. POLZOVATEL (FOYDALANUVCHI) IXCHAM REPLY VA INLINE PANELI (UZ / RU) =====================
def user_main_keyboard(role: str = "user", lang: str = "uz"):
    """
    Pastki Reply tugmalar maksimal darajada ixcham va chiroyli:
    - 🔍 Kino qidirish
    - 👤 Shaxsiy Kabinet | 🌐 Til / Язык
    - (Agar Admin/SuperAdmin bo'lsa: 👮 Admin Panel | 👑 SUPER ADMIN PANEL)
    Qolgan barcha bo'limlar chiroyli Inline menyuda chiqadi!
    """
    lang = "ru" if lang == "ru" else "uz"
    kb = [
        [KeyboardButton(text=BTN["search"][lang])],
        [KeyboardButton(text=BTN["cabinet"][lang]), KeyboardButton(text=BTN["lang"][lang])]
    ]
    if role == "superadmin":
        kb.append([KeyboardButton(text="👮 Admin Panel"), KeyboardButton(text="👑 SUPER ADMIN PANEL")])
    elif role in ("moderator", "admin"):
        kb.append([KeyboardButton(text="👮 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def user_inline_dashboard(lang: str = "uz"):
    """Bosh sahifadagi asosiy interaktiv Inline Menyu (Inline Search eng ustida!)."""
    lang = "ru" if lang == "ru" else "uz"
    inline_search_lbl = (
        "🔍 В режиме Инлайн (Список с постерами)"
        if lang == "ru"
        else "🔍 Inline rejimda (Rasmli Ro'yxat) qidirish"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=inline_search_lbl, switch_inline_query_current_chat="")
            ],
            [
                InlineKeyboardButton(text=BTN["top"][lang], switch_inline_query_current_chat="top"),
                InlineKeyboardButton(text=BTN["new"][lang], switch_inline_query_current_chat="new")
            ],
            [
                InlineKeyboardButton(text=BTN["genres"][lang], callback_data="nav:genres"),
                InlineKeyboardButton(text=BTN["serials"][lang], switch_inline_query_current_chat="serial")
            ],
            [
                InlineKeyboardButton(text=BTN["random"][lang], callback_data="nav:random"),
                InlineKeyboardButton(text=BTN["order"][lang], callback_data="nav:order")
            ],
            [
                InlineKeyboardButton(text=BTN["earn"][lang], callback_data="go_earn_menu")
            ],
            [
                InlineKeyboardButton(text=BTN["vip_shop"][lang], callback_data="open_vip_shop")
            ],
            [
                InlineKeyboardButton(text=BTN["topic_group"][lang], callback_data="nav:topic_group")
            ],
            [
                InlineKeyboardButton(text=BTN["favs"][lang], callback_data="nav:favs"),
                InlineKeyboardButton(text=BTN["rules"][lang], callback_data="nav:rules")
            ]
        ]
    )


# ===================== 2. MODERATOR VA ADMINISTRATOR PANELI =====================
def staff_panel_keyboard(perms: list, is_super: bool = False):
    kb = []

    if is_super or "archive_load" in perms or "add_movie" in perms:
        kb.append([
            KeyboardButton(text="🗂 Arxiv boshqaruvi va Chala postlar"),
            KeyboardButton(text="📥 Bazadan Kino yuklash")
        ])
        kb.append([KeyboardButton(text="📺 Bazadan Serial yuklash")])

    if is_super or "add_movie" in perms:
        kb.append([KeyboardButton(text="➕ Kino qo'shish (Pro)"), KeyboardButton(text="⚡ Tezkor kino qo'shish")])
        kb.append([KeyboardButton(text="🎞 Serial qismi qo'shish")])

    row2 = []
    if is_super or "del_movie" in perms:
        row2.append(KeyboardButton(text="🗑 Kino o'chirish"))
    if is_super or "orders" in perms:
        row2.append(KeyboardButton(text="📩 Kino buyurtmalar"))
    if row2:
        kb.append(row2)

    row3 = []
    if is_super or "channels" in perms:
        row3.append(KeyboardButton(text="📢 Kanallarni boshqarish"))
        row3.append(KeyboardButton(text="🌐 Mavzuli Guruh Boshqaruvi"))
    if row3:
        kb.append(row3)

    row4 = []
    if is_super or "stats" in perms:
        row4.append(KeyboardButton(text="📊 Statistika"))
    if is_super or "broadcast" in perms:
        row4.append(KeyboardButton(text="✉️ Xabar yuborish"))
    if row4:
        kb.append(row4)

    row5 = []
    if is_super or "users_ban" in perms:
        row5.append(KeyboardButton(text="🚫 User qidirish va Ban"))
    if is_super or "vip_manage" in perms:
        row5.append(KeyboardButton(text="💎 VIP, Narxlar va Bonuslar"))
    if row5:
        kb.append(row5)

    if is_super:
        kb.append([KeyboardButton(text="👑 SUPER ADMIN PANEL")])

    kb.append([KeyboardButton(text="🏠 Foydalanuvchi menyusi")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ===================== 3. SUPER ADMINISTRATOR PANELI (/spanel, /sadmin) =====================
def super_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗂 Arxiv boshqaruvi va Chala postlar"), KeyboardButton(text="📥 Bazadan Kino yuklash")],
            [KeyboardButton(text="📺 Bazadan Serial yuklash"), KeyboardButton(text="🗑 Faqat kinolar bazasini tozalash")],
            [KeyboardButton(text="🖥 Server Holati va CPU Analiz"), KeyboardButton(text="🧹 Kesh va __pycache__ tozalash")],
            [KeyboardButton(text="👁 Kinolarga Ko'rish qo'shish"), KeyboardButton(text="📊 Kengaytirilgan Statistika")],
            [KeyboardButton(text="🌐 Mavzuli Guruh Boshqaruvi"), KeyboardButton(text="💎 VIP, Narxlar va Bonuslar")],
            [KeyboardButton(text="👮 Lavozim va Ruxsatlar"), KeyboardButton(text="🧠 Top-15 AI Tizimi")],
            [KeyboardButton(text="💾 Backup va Export/Import"), KeyboardButton(text="⚙️ Texnik Sozlamalar va Himoya")],
            [KeyboardButton(text="🔐 Super-Parolni o'zgartirish"), KeyboardButton(text="🏠 Foydalanuvchi menyusi")],
            [KeyboardButton(text="👮 Admin Panel")]
        ],
        resize_keyboard=True
    )

def cancel_keyboard(lang: str = "uz"):
    lang = "ru" if lang == "ru" else "uz"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN["cancel"][lang])]],
        resize_keyboard=True
    )

def skip_or_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

def channels_manage_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Ochiq kanal qo'shish"), KeyboardButton(text="🔒 Zayavkali kanal qo'shish")],
            [KeyboardButton(text="🌐 Ijtimoiy tarmoq havolasi"), KeyboardButton(text="➖ Kanal o'chirish")],
            [KeyboardButton(text="📋 Kanallar ro'yxati")],
            [KeyboardButton(text="👮 Admin Panel")]
        ],
        resize_keyboard=True
    )


# ===================== 4. KUNLIK BONUS VA PUL ISHLASH INLINE (UZ / RU) =====================
def earn_money_inline(ref_link: str, daily_amount: str, ref_amount: str, lang: str = "uz"):
    if lang == "ru":
        share_url = f"https://t.me/share/url?url={ref_link}&text=🎬 Лучший бот фильмов и сериалов! Заходи, получай ежедневный бонус и бесплатный VIP!"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"🎁 Получить ежедневный бонус (+{int(daily_amount):,} сум)", callback_data="claim_daily")],
                [InlineKeyboardButton(text=f"📲 Пригласить друзей (+{int(ref_amount):,} сум)", url=share_url)],
                [InlineKeyboardButton(text="💎 Купить Premium (VIP) за баланс", callback_data="open_vip_shop")],
                [InlineKeyboardButton(text="🏆 Топ богачей и рефералов", callback_data="show_leaderboard")],
                [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_main_menu")]
            ]
        )
    share_url = f"https://t.me/share/url?url={ref_link}&text=🎬 Eng yangi kinolar va seriallar botiga kiring, kunlik bonus oling va bepul VIP yuting!"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🎁 Kunlik Bonusni olish (+{int(daily_amount):,} so'm)", callback_data="claim_daily")],
            [InlineKeyboardButton(text=f"📲 Do'stlarni taklif qilish (+{int(ref_amount):,} so'm)", url=share_url)],
            [InlineKeyboardButton(text="💎 Balansga Premium (VIP) sotib olish", callback_data="open_vip_shop")],
            [InlineKeyboardButton(text="🏆 Top Boylar va Referallar Reytingi", callback_data="show_leaderboard")],
            [InlineKeyboardButton(text="🔙 Asosiy menyuga qaytish", callback_data="back_main_menu")]
        ]
    )


# ===================== 5. FOYDALANUVCHI VIP DO'KON, KARTA VA OTZIV INLINE (UZ / RU) =====================
def user_vip_shop_inline(p7: str, p30: str, p90: str, is_vip: bool = False, cur_tag: str = "PREMIUM", lang: str = "uz"):
    if lang == "ru":
        buttons = [
            [InlineKeyboardButton(text=f"💎 VIP на 7 дней  ✦  {int(p7):,} сум", callback_data="buy_vip:7")],
            [InlineKeyboardButton(text=f"🔥 VIP на 30 дней  ✦  {int(p30):,} сум", callback_data="buy_vip:30")],
            [InlineKeyboardButton(text=f"👑 VIP на 90 дней  ✦  {int(p90):,} сум", callback_data="buy_vip:90")],
            [InlineKeyboardButton(text="💳 Оплата картой (Отправить чек)", callback_data="pay_by_card")],
            [InlineKeyboardButton(text="🎁 Бесплатные бонусы и рефералы", callback_data="go_earn_menu")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_main_menu")]
        ]
        if is_vip:
            buttons.insert(0, [
                InlineKeyboardButton(text=f"🏷 Мой VIP Тег: [{cur_tag}] (Изменить)", callback_data="vip_choose_tag")
            ])
            buttons.insert(1, [
                InlineKeyboardButton(text="⚡ Активировать тег [PREMIUM] в группе", callback_data="vip_apply_tags_now")
            ])
            buttons.insert(2, [
                InlineKeyboardButton(text="💬 Оставить отзыв о Premium (в группу)", callback_data="vip_leave_review")
            ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    buttons = [
        [InlineKeyboardButton(text=f"💎 7 Kunlik VIP  ✦  {int(p7):,} so'm", callback_data="buy_vip:7")],
        [InlineKeyboardButton(text=f"🔥 30 Kunlik VIP  ✦  {int(p30):,} so'm", callback_data="buy_vip:30")],
        [InlineKeyboardButton(text=f"👑 90 Kunlik VIP  ✦  {int(p90):,} so'm", callback_data="buy_vip:90")],
        [InlineKeyboardButton(text="💳 Karta orqali to'lov (Chek yuborish)", callback_data="pay_by_card")],
        [InlineKeyboardButton(text="🎁 Kunlik Bonus & Do'stlar orqali yig'ish", callback_data="go_earn_menu")],
        [InlineKeyboardButton(text="🔙 Asosiy menyuga qaytish", callback_data="back_main_menu")]
    ]
    if is_vip:
        buttons.insert(0, [
            InlineKeyboardButton(text=f"🏷 Mening VIP Tegim: [{cur_tag}] (O'zgartirish)", callback_data="vip_choose_tag")
        ])
        buttons.insert(1, [
            InlineKeyboardButton(text="⚡ Mavzuli guruhda [PREMIUM] Tegni faollashtirish", callback_data="vip_apply_tags_now")
        ])
        buttons.insert(2, [
            InlineKeyboardButton(text="💬 Premium haqida fikr (Otziv) qoldirish", callback_data="vip_leave_review")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_card_plan_select_inline(p7: str, p30: str, p90: str, lang: str = "uz"):
    """Karta orqali to'lashda foydalanuvchi qaysi tarif uchun chek yuborayotganini tanlaydi."""
    if lang == "ru":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"💎 Тариф 7 дней VIP — {int(p7):,} сум", callback_data="card_plan:7")],
                [InlineKeyboardButton(text=f"🔥 Тариф 30 дней VIP — {int(p30):,} сум", callback_data="card_plan:30")],
                [InlineKeyboardButton(text=f"👑 Тариф 90 дней VIP — {int(p90):,} сум", callback_data="card_plan:90")],
                [InlineKeyboardButton(text="🔙 Назад в магазин VIP", callback_data="open_vip_shop")]
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💎 7 kunlik VIP tarifi — {int(p7):,} so'm", callback_data="card_plan:7")],
            [InlineKeyboardButton(text=f"🔥 30 kunlik VIP tarifi — {int(p30):,} so'm", callback_data="card_plan:30")],
            [InlineKeyboardButton(text=f"👑 90 kunlik VIP tarifi — {int(p90):,} so'm", callback_data="card_plan:90")],
            [InlineKeyboardButton(text="🔙 VIP Do'konga qaytish", callback_data="open_vip_shop")]
        ]
    )


def vip_tags_choice_inline(current_tag: str, lang: str = "uz"):
    buttons = []
    row = []
    for t in config.VIP_CUSTOM_TAGS:
        mark = "✅ " if t == current_tag else "🏷 "
        row.append(InlineKeyboardButton(text=f"{mark}{t}", callback_data=f"set_vtag:{t}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if lang == "ru":
        buttons.append([InlineKeyboardButton(text="✍️ Написать свой собственный Тег", callback_data="custom_vtag_write")])
        buttons.append([InlineKeyboardButton(text="🔙 Назад в магазин VIP", callback_data="open_vip_shop")])
    else:
        buttons.append([InlineKeyboardButton(text="✍️ O'zim xohlagan maxsus Teg yozish", callback_data="custom_vtag_write")])
        buttons.append([InlineKeyboardButton(text="🔙 VIP Do'konga qaytish", callback_data="open_vip_shop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def vip_review_stars_inline(lang: str = "uz"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐⭐⭐⭐⭐ (5/5 — A'lo / Отлично)", callback_data="rev_star:5")],
            [InlineKeyboardButton(text="⭐⭐⭐⭐ (4/5 — Yaxshi / Хорошо)", callback_data="rev_star:4")],
            [InlineKeyboardButton(text="⭐⭐⭐ (3/5 — O'rtacha / Нормально)", callback_data="rev_star:3")],
            [InlineKeyboardButton(text="🔙 Orqaga / Назад", callback_data="open_vip_shop")]
        ]
    )


def payment_receipt_superadmin_inline(user_id: int, plan_days: int = 30):
    """
    ⚡ Активный Faolik bo'limiga va Super-Adminga boradigan chek ostidagi tugmalar.
    FAQAT Super-Admin bosa oladi!
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ Tasdiqlash ({plan_days} kun VIP berish)",
                    callback_data=f"sadm_pay_ok:{user_id}:{plan_days}"
                )
            ],
            [
                InlineKeyboardButton(text="✅ 7k VIP", callback_data=f"sadm_pay_ok:{user_id}:7"),
                InlineKeyboardButton(text="✅ 30k VIP", callback_data=f"sadm_pay_ok:{user_id}:30"),
                InlineKeyboardButton(text="✅ 90k VIP", callback_data=f"sadm_pay_ok:{user_id}:90")
            ],
            [
                InlineKeyboardButton(text="💰 Balans qo'shish", callback_data=f"adm_pay_bal:{user_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"sadm_pay_reject:{user_id}")
            ]
        ]
    )


# ===================== 6. YAGONA MAVZULI GURUH (-1002748514315) INLINE =====================
def single_topic_group_user_inline(is_vip: bool, user_tag: str = "PREMIUM", lang: str = "uz"):
    base = config.MAIN_TOPIC_GROUP_LINK
    if lang == "ru":
        buttons = [
            [InlineKeyboardButton(text="👑 Чат Muhokama (Общение)", url=f"{base}/{config.TOPIC_CHAT_ID}")],
            [
                InlineKeyboardButton(text="⭐ Buyurtmalar (Заказы)", url=f"{base}/{config.TOPIC_ORDERS_ID}"),
                InlineKeyboardButton(text="💸 Premium (Отзывы)", url=f"{base}/{config.TOPIC_PREMIUM_REVIEWS_ID}")
            ],
            [
                InlineKeyboardButton(text="💎 Qoidalar (Правила)", url=f"{base}/{config.TOPIC_RULES_ID}"),
                InlineKeyboardButton(text="⚡ Faolik (Активность)", url=f"{base}/{config.TOPIC_ACTIVITY_ID}")
            ]
        ]
        if is_vip:
            buttons.append([
                InlineKeyboardButton(text=f"🏷 Обновить мой тег [{user_tag}] в группе", callback_data="vip_apply_tags_now")
            ])
            buttons.append([
                InlineKeyboardButton(text="💬 Оставить отзыв в раздел 💸 Premium", callback_data="vip_leave_review")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="💎 Купить VIP для получения тега [PREMIUM] в группе!", callback_data="open_vip_shop")
            ])
        buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_main_menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    buttons = [
        [InlineKeyboardButton(text="👑 Чат Muhokama (Suhbat bo'limi)", url=f"{base}/{config.TOPIC_CHAT_ID}")],
        [
            InlineKeyboardButton(text="⭐ Buyurtmalar bo'limi", url=f"{base}/{config.TOPIC_ORDERS_ID}"),
            InlineKeyboardButton(text="💸 Premium (Otzivlar)", url=f"{base}/{config.TOPIC_PREMIUM_REVIEWS_ID}")
        ],
        [
            InlineKeyboardButton(text="💎 Qoidalar bo'limi", url=f"{base}/{config.TOPIC_RULES_ID}"),
            InlineKeyboardButton(text="⚡ Faolik (Seanslar)", url=f"{base}/{config.TOPIC_ACTIVITY_ID}")
        ]
    ]
    if is_vip:
        buttons.append([
            InlineKeyboardButton(text=f"🏷 Guruhda [{user_tag}] tegimni faollashtirish!", callback_data="vip_apply_tags_now")
        ])
        buttons.append([
            InlineKeyboardButton(text="💬 💸 Premium bo'limiga Otziv yozish", callback_data="vip_leave_review")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="💎 Guruhda [PREMIUM] tegi olish uchun VIP xarid qiling!", callback_data="open_vip_shop")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Asosiy menyuga qaytish", callback_data="back_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def topic_channels_admin_inline(topic_channels: list):
    base = config.MAIN_TOPIC_GROUP_LINK
    buttons = [
        [InlineKeyboardButton(text="🌐 Rasmiy Guruh: Movie Land Group (-1002748514315)", url=base)],
        [
            InlineKeyboardButton(text="⚡ Faolik (196)", url=f"{base}/{config.TOPIC_ACTIVITY_ID}"),
            InlineKeyboardButton(text="💸 Premium (190)", url=f"{base}/{config.TOPIC_PREMIUM_REVIEWS_ID}")
        ],
        [
            InlineKeyboardButton(text="⭐ Buyurtmalar (193)", url=f"{base}/{config.TOPIC_ORDERS_ID}"),
            InlineKeyboardButton(text="💎 Qoidalar (195)", url=f"{base}/{config.TOPIC_RULES_ID}")
        ],
        [InlineKeyboardButton(text="🔄 Barcha VIP a'zolarga guruhda Tegni yangilash", callback_data="adm_sync_all_vip_tags")]
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
                InlineKeyboardButton(text=f"🎁 Kunlik Bonus: {int(daily_rew):,} so'm", callback_data="eco_set:daily_reward_amount"),
                InlineKeyboardButton(text=f"👥 Referal: {int(ref_rew):,} so'm", callback_data="eco_set:ref_reward_amount")
            ],
            [
                InlineKeyboardButton(text=f"💎 7k VIP: {int(p7):,} so'm", callback_data="eco_set:vip_7_price"),
                InlineKeyboardButton(text=f"🔥 30k VIP: {int(p30):,} so'm", callback_data="eco_set:vip_30_price")
            ],
            [
                InlineKeyboardButton(text=f"👑 90k VIP: {int(p90):,} so'm", callback_data="eco_set:vip_90_price"),
                InlineKeyboardButton(text="💳 Karta raqamni sozlash", callback_data="eco_set:payment_card_info")
            ],
            [
                InlineKeyboardButton(text=f"👤 Oddiy limit: {free_limit} ta/kun", callback_data="vip_chg_free"),
                InlineKeyboardButton(text=f"💎 VIP limit: {vip_limit} ta/kun", callback_data="vip_chg_vip")
            ],
            [
                InlineKeyboardButton(text="💎 Userga VIP berish", callback_data="vip_give"),
                InlineKeyboardButton(text="❌ Userdan VIP olish", callback_data="vip_remove")
            ],
            [
                InlineKeyboardButton(text="💰 User balansiga pul qo'shish/ayirish", callback_data="eco_user_bal"),
                InlineKeyboardButton(text="📋 VIP userlar ro'yxati", callback_data="vip_list")
            ]
        ]
    )


# ===================== 8. ARXIV KANAL BOSHQARUVI INLINE =====================
def archive_center_inline(auto_grab: str, auto_post: str, archive_ch: str, post_ch: str):
    grab_txt = "🟢 Yoqilgan (Avto-qabul)" if auto_grab == "1" else "🔴 O'chirilgan"
    post_txt = "🟢 Yoqilgan" if auto_post == "1" else "🔴 O'chirilgan"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📡 Arxiv kanalni to'liq skanerlash", callback_data="arch_scan_channel")],
            [InlineKeyboardButton(text="✨ Chala postlarni to'ldirish va tartiblash", callback_data="arch_ai_fix_posts")],
            [
                InlineKeyboardButton(text="📥 10 ta kino yuklash", callback_data="arch_load_10"),
                InlineKeyboardButton(text="📺 1 ta serial yuklash", callback_data="arch_load_1_serial")
            ],
            [InlineKeyboardButton(text="🗑 Faqat kinolar bazasini tozalash", callback_data="clear_movies_confirm")],
            [InlineKeyboardButton(text=f"🤖 Yangi kinolarni avto-olish: {grab_txt}", callback_data="arch_toggle_grab")],
            [InlineKeyboardButton(text=f"📢 Kanalga avto-post: {post_txt}", callback_data="arch_toggle_post")]
        ]
    )


# ===================== 9. GRANULAR PRIVILEGIYA VA RUXSATLAR INLINE =====================
def staff_control_menu_inline(staff_list: list):
    buttons = [
        [InlineKeyboardButton(text="➕ Chat ID orqali yangi Moder/Admin tayinlash", callback_data="sadm_add_staff")]
    ]
    for s in staff_list:
        uid = s["user_id"]
        role = s.get("role", "moderator")
        r_badge = {"moderator": "🛡 Moder", "admin": "👮 Admin", "superadmin": "👑 Super"}.get(role, "🛡 Staff")
        buttons.append([
            InlineKeyboardButton(
                text=f"{r_badge}: {s.get('full_name', 'User')} ({uid})",
                callback_data=f"sadm_edit_staff:{uid}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def staff_permissions_inline(target_id: int, current_role: str, user_perms: list):
    buttons = [
        [
            InlineKeyboardButton(
                text=("✅ " if current_role == "moderator" else "") + "🛡 Moderator",
                callback_data=f"setrole:{target_id}:moderator"
            ),
            InlineKeyboardButton(
                text=("✅ " if current_role == "admin" else "") + "👮 Admin",
                callback_data=f"setrole:{target_id}:admin"
            ),
            InlineKeyboardButton(
                text=("✅ " if current_role == "superadmin" else "") + "👑 Super",
                callback_data=f"setrole:{target_id}:superadmin"
            )
        ]
    ]

    for perm_key, perm_label in config.PERMISSIONS.items():
        has_it = (current_role == "superadmin") or (perm_key in user_perms)
        status_icon = "✅ Yoqilgan" if has_it else "❌ O'chirilgan"
        buttons.append([
            InlineKeyboardButton(
                text=f"{perm_label}: {status_icon}",
                callback_data=f"togperm:{target_id}:{perm_key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🗑 Barcha huquqlarni olib tashlash (Oddiy User)", callback_data=f"setrole:{target_id}:user")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Xodimlar ro'yxatiga qaytish", callback_data="sadm_back_staff")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ===================== 10. TOP-15 AI VA BACKUP INLINE =====================
def ai_dashboard_inline(ai_enabled: str, active_prov: str, configured_keys: dict):
    status_txt = "🟢 YOQILGAN (Faol)" if ai_enabled == "1" else "🔴 O'CHIRILGAN"
    active_name = config.TOP_15_AI_PROVIDERS.get(active_prov, {}).get("name", active_prov)

    buttons = [
        [InlineKeyboardButton(text=f"⚡ AI Tizimi holati: {status_txt}", callback_data="ai_toggle_status")],
        [InlineKeyboardButton(text=f"🎯 Hozirgi tanlangan: {active_name}", callback_data="ai_noop")],
        [InlineKeyboardButton(text="🪄 Bazadagi barcha kinolarni AI da to'ldirish", callback_data="ai_run_batch")]
    ]

    for p_key, p_info in config.TOP_15_AI_PROVIDERS.items():
        has_key = "🔑 Token bor" if configured_keys.get(p_key) else "⚙️ Ichki AI"
        is_sel = "🎯 " if p_key == active_prov else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{is_sel}{p_info['name']} [{has_key}]",
                callback_data=f"ai_select:{p_key}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def ai_provider_detail_inline(p_key: str, has_token: bool):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔑 API Token kiritish / yangilash", callback_data=f"ai_setkey:{p_key}")],
            [InlineKeyboardButton(text="✅ Shu AI ni asosiy qilib tanlash va yoqish", callback_data=f"ai_activate:{p_key}")],
            [InlineKeyboardButton(text="🧪 Test qilib ko'rish", callback_data=f"ai_test:{p_key}")],
            [InlineKeyboardButton(text="🔙 AI ro'yxatiga qaytish", callback_data="ai_back_main")]
        ]
    )

def backup_center_inline(auto_hours: str):
    if auto_hours == "168":
        h_txt = "Har haftada (168 soat)"
    elif auto_hours != "0":
        h_txt = f"Har {auto_hours} soatda"
    else:
        h_txt = "O'chirilgan"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Hoziroq Arxiv Guruhga Backup Yuborish", callback_data="bkp_send_archive_now")],
            [InlineKeyboardButton(text="📥 To'liq bazani yuklab olish (database.db)", callback_data="bkp_download_db")],
            [
                InlineKeyboardButton(text="📦 JSON Export (Kino+User)", callback_data="bkp_export_json"),
                InlineKeyboardButton(text="📊 Excel/CSV Export", callback_data="bkp_export_csv")
            ],
            [InlineKeyboardButton(text="📤 Baza Import qilish (.json yoki .db yuklash)", callback_data="bkp_import_start")],
            [InlineKeyboardButton(text=f"⏰ Avto-Backup rejimi: {h_txt}", callback_data="bkp_toggle_auto")]
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
        buttons.append([InlineKeyboardButton(text=btn_text, url=link)])

    cb_data = f"check_sub:{movie_code}" if movie_code else "check_sub"
    chk_txt = "✅ Я подписался / Проверить" if lang == "ru" else "✅ A'zo bo'ldim / Tekshirish"
    buttons.append([InlineKeyboardButton(text=chk_txt, callback_data=cb_data)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def genres_inline_keyboard(for_admin: bool = False, lang: str = "uz"):
    buttons = []
    if for_admin:
        buttons.append([InlineKeyboardButton(text="🤖 AI o'zi janrni aniqlasin (Avto)", callback_data="adm_genre:auto")])
    row = []
    for g in config.GENRES:
        if for_admin:
            row.append(InlineKeyboardButton(text=g, callback_data=f"adm_genre:{g}"))
        else:
            row.append(InlineKeyboardButton(text=g, switch_inline_query_current_chat=g))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if not for_admin:
        back_txt = "🔙 В главное меню" if lang == "ru" else "🔙 Asosiy menyuga qaytish"
        buttons.append([InlineKeyboardButton(text=back_txt, callback_data="back_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def quality_inline_keyboard():
    qualities = ["480p SD", "720p HD", "1080p Full HD", "4K Ultra HD"]
    buttons = [
        [InlineKeyboardButton(text="🤖 AI o'zi sifatni aniqlasin (Avto)", callback_data="adm_qual:auto")],
        [InlineKeyboardButton(text=q, callback_data=f"adm_qual:{q}") for q in qualities[:2]],
        [InlineKeyboardButton(text=q, callback_data=f"adm_qual:{q}") for q in qualities[2:]]
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
    Kino yoki serial tanlanganida avval Poster Card chiqadi (reski video berilmaydi!):
    - Agar qismlari <= 1 bo'lsa: [ ▶️ Kino ko'rish ]
    - Agar qismlari 2 yoki 3 ta bo'lsa: [ ▶️ Kino ko'rish (1-qism) ] [ ▶️ Kino ko'rish (2-qism) ] ...
    - Agar qismlari 3 tadan ko'p bo'lsa (yoki serial bo'lsa): [ 1 ] [ 2 ] [ 3 ] [ 4 ] [ 5 ] ...
    """
    code = movie["code"]
    user_perms = user_perms or []
    episodes = episodes or []
    buttons = []

    total_eps = len(episodes)
    if total_eps <= 1:
        watch_lbl = "▶️ Смотреть фильм" if lang == "ru" else "▶️ Kino ko'rish"
        buttons.append([
            InlineKeyboardButton(text=watch_lbl, callback_data=f"watch:{code}:1")
        ])
    elif 2 <= total_eps <= 3:
        ep_word = "ч." if lang == "ru" else "qism"
        watch_prefix = "▶️ Смотреть" if lang == "ru" else "▶️ Kino ko'rish"
        for ep in episodes:
            ep_num = ep["episode_num"]
            play_icon = "▶️ " if (current_ep and ep_num == current_ep) else ""
            buttons.append([
                InlineKeyboardButton(
                    text=f"{play_icon}{watch_prefix} ({ep_num}-{ep_word})",
                    callback_data=f"watch:{code}:{ep_num}"
                )
            ])
    else:
        # 3 tadan ko'p qism yoki serial: 1 2 3 4 5 ... ko'rinishida
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
            btn_txt = f"▶️ {ep_num}" if (current_ep and ep_num == current_ep) else f"{ep_num}"
            row.append(InlineKeyboardButton(text=btn_txt, callback_data=f"watch:{code}:{ep_num}"))
            if len(row) == 5:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        if total_pages > 1:
            nav_row = []
            if ep_page > 1:
                nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"eppage:{code}:{ep_page - 1}"))
            nav_row.append(InlineKeyboardButton(text=f"📄 {ep_page}/{total_pages}", callback_data="noop"))
            if ep_page < total_pages:
                nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"eppage:{code}:{ep_page + 1}"))
            buttons.append(nav_row)

    # 5 talik yulduzcha baholash qatori
    star_row = []
    for s in range(1, 6):
        lbl = f"🌟 {s}" if user_rating == s else f"⭐ {s}"
        star_row.append(InlineKeyboardButton(text=lbl, callback_data=f"rate:{code}:{s}"))
    buttons.append(star_row)

    deep_link_enc = quote(f"https://t.me/{bot_username}?start={code}")
    if lang == "ru":
        fav_text = "✅ В избранном" if is_fav else "⭐ Сохранить"
        share_txt = "↗️ Поделиться"
        share_cap_enc = quote(f"🎬 {movie['name']} — Смотрите фильм в боте!")
        share_url = f"https://t.me/share/url?url={deep_link_enc}&text={share_cap_enc}"
    else:
        fav_text = "✅ Saqlangan" if is_fav else "⭐ Saqlab qo'yish"
        share_txt = "↗️ Ulashish"
        share_cap_enc = quote(f"🎬 {movie['name']} — Kinoni bot orqali tomosha qiling!")
        share_url = f"https://t.me/share/url?url={deep_link_enc}&text={share_cap_enc}"

    buttons.append([
        InlineKeyboardButton(text=fav_text, callback_data=f"fav:{code}"),
        InlineKeyboardButton(text=share_txt, url=share_url)
    ])

    adm_row1 = []
    if "add_movie" in user_perms or "autopost" in user_perms:
        has_pic = "🖼 Rasm yangilash" if movie.get("photo_id") else "🖼 Rasm qo'shish"
        adm_row1.append(InlineKeyboardButton(text=has_pic, callback_data=f"editpic:{code}"))
    if "autopost" in user_perms:
        adm_row1.append(InlineKeyboardButton(text="📢 Kanalga Post", callback_data=f"autopost:{code}"))
    if adm_row1:
        buttons.append(adm_row1)

    adm_row2 = []
    if "add_movie" in user_perms:
        adm_row2.append(InlineKeyboardButton(text="➕ Qism ulash", callback_data=f"addep:{code}"))
    if "del_movie" in user_perms:
        adm_row2.append(InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delmov:{code}"))
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
        if total_eps <= 3:
            ep_row = []
            ep_word = "серия" if lang == "ru" else "qism"
            for ep in episodes:
                ep_num = ep["episode_num"]
                label = f"▶️ {ep_num}-{ep_word}" if ep_num == current_ep else f"{ep_num}-{ep_word}"
                ep_row.append(InlineKeyboardButton(text=label, callback_data=f"ep:{code}:{ep_num}"))
            buttons.append(ep_row)
        else:
            # Agar qismlar > 3 bo'lsa, joriy qism turgan 15 talik blokni 1 2 3 4 5 qilib chiqaramiz
            idx = 0
            for i, ep in enumerate(episodes):
                if ep["episode_num"] == current_ep:
                    idx = i
                    break
            block_start = (idx // 15) * 15
            window_eps = episodes[block_start : block_start + 15]
            ep_row = []
            for ep in window_eps:
                ep_num = ep["episode_num"]
                label = f"▶️ {ep_num}" if ep_num == current_ep else f"{ep_num}"
                ep_row.append(InlineKeyboardButton(text=label, callback_data=f"ep:{code}:{ep_num}"))
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
                    prev_ep = max(1, cur_block * 15)
                    nav.append(InlineKeyboardButton(text="⬅️ Oldingi 15", callback_data=f"ep:{code}:{prev_ep}"))
                nav.append(InlineKeyboardButton(text=f"🎞 {current_ep}/{total_eps}", callback_data="noop"))
                if cur_block < max_blocks:
                    next_ep = min(total_eps, (cur_block + 1) * 15 + 1)
                    nav.append(InlineKeyboardButton(text="Keyingi 15 ➡️", callback_data=f"ep:{code}:{next_ep}"))
                buttons.append(nav)

        if total_eps > 1:
            step_row = []
            prev_lbl = "◀️ Предыдущая" if lang == "ru" else "◀️ Oldingi qism"
            next_lbl = "Следующая ⏩" if lang == "ru" else "Keyingi qism ⏩"
            if current_ep > 1:
                step_row.append(InlineKeyboardButton(text=prev_lbl, callback_data=f"ep:{code}:{current_ep - 1}"))
            if current_ep < total_eps:
                step_row.append(InlineKeyboardButton(text=next_lbl, callback_data=f"ep:{code}:{current_ep + 1}"))
            if step_row:
                buttons.append(step_row)

    # 5 talik yulduzcha baholash qatori (👍/👎 o'rniga)
    star_row = []
    for s in range(1, 6):
        lbl = f"🌟 {s}" if user_rating == s else f"⭐ {s}"
        star_row.append(InlineKeyboardButton(text=lbl, callback_data=f"rate:{code}:{s}"))
    buttons.append(star_row)

    deep_link_enc = quote(f"https://t.me/{bot_username}?start={code}")
    if lang == "ru":
        fav_text = "✅ В избранном" if is_fav else "⭐ Сохранить"
        share_txt = "↗️ Поделиться"
        share_cap_enc = quote(f"🎬 {movie['name']} — Смотрите фильм в боте!")
        share_url = f"https://t.me/share/url?url={deep_link_enc}&text={share_cap_enc}"
    else:
        fav_text = "✅ Saqlangan" if is_fav else "⭐ Saqlab qo'yish"
        share_txt = "↗️ Ulashish"
        share_cap_enc = quote(f"🎬 {movie['name']} — Kinoni bot orqali tomosha qiling!")
        share_url = f"https://t.me/share/url?url={deep_link_enc}&text={share_cap_enc}"

    buttons.append([
        InlineKeyboardButton(text=fav_text, callback_data=f"fav:{code}"),
        InlineKeyboardButton(text=share_txt, url=share_url)
    ])

    adm_row1 = []
    if "add_movie" in user_perms or "autopost" in user_perms:
        has_pic = "🖼 Rasm yangilash" if movie.get("photo_id") else "🖼 Rasm qo'shish"
        adm_row1.append(InlineKeyboardButton(text=has_pic, callback_data=f"editpic:{code}"))
    if "autopost" in user_perms:
        adm_row1.append(InlineKeyboardButton(text="📢 Kanalga Post", callback_data=f"autopost:{code}"))
    if adm_row1:
        buttons.append(adm_row1)

    adm_row2 = []
    if "add_movie" in user_perms:
        adm_row2.append(InlineKeyboardButton(text="➕ Qism ulash", callback_data=f"addep:{code}"))
    if "del_movie" in user_perms:
        adm_row2.append(InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delmov:{code}"))
    if adm_row2:
        buttons.append(adm_row2)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def movies_list_inline(movies: list, title_prefix: str = "🎬", lang: str = "uz", query: str = ""):
    """
    Menyuli ro'yxat o'rniga 3-rasmdagidek rasmli avto-qidiruv (switch_inline_query_current_chat) tugmasi.
    """
    search_lbl = (
        "🔍 В режиме Инлайн (Список с постерами)"
        if lang == "ru"
        else "🔍 Inline rejimda (Rasmli Ro'yxat) qidirish"
    )
    back_txt = "🔙 В главное меню" if lang == "ru" else "🔙 Asosiy menyuga qaytish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=search_lbl, switch_inline_query_current_chat=query)],
            [InlineKeyboardButton(text=back_txt, callback_data="back_main_menu")]
        ]
    )

def movies_catalog_paginated_inline(movies: list = None, page: int = 1, total_pages: int = 1, lang: str = "uz"):
    """
    «🔍 Kino qidirish» bosilganda:
    2-rasmdagi menyuli ro'yxat (menulik kino poisk) butkul olib tashlangan!
    Faqat 3-rasmdagidek «🔍 Inline rejimda (Rasmli Ro'yxat) qidirish» tugmasi chiqadi.
    """
    search_lbl = (
        "🔍 В режиме Инлайн (Список с постерами)"
        if lang == "ru"
        else "🔍 Inline rejimda (Rasmli Ro'yxat) qidirish"
    )
    back_txt = "🔙 В главное меню" if lang == "ru" else "🔙 Asosiy menyuga qaytish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=search_lbl, switch_inline_query_current_chat="")],
            [InlineKeyboardButton(text=back_txt, callback_data="back_main_menu")]
        ]
    )

def settings_inline_keyboard(protect_content: str, auto_post_channel: str, bot_active: str):
    prot_txt = "🟢 Yoqilgan (Forward/Saqlash Yopiq)" if protect_content == "1" else "🔴 O'chirilgan (Erkin)"
    act_txt = "🟢 Faol ishlamoqda" if bot_active == "1" else "🔴 Texnik ishlar rejimi"
    ch_txt = auto_post_channel if auto_post_channel else "Belgilanmagan"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🔒 Forward va Saqlashni cheklash: {prot_txt}", callback_data="toggle_protect")],
            [InlineKeyboardButton(text=f"🤖 Bot holati: {act_txt}", callback_data="toggle_bot_active")],
            [InlineKeyboardButton(text=f"📢 Avto-Post kanali: {ch_txt}", callback_data="set_autopost_ch")],
            [
                InlineKeyboardButton(text="🛑 Botni to'xtatish", callback_data="btn_shutdown_bot"),
                InlineKeyboardButton(text="🔄 Qayta yuklash", callback_data="btn_restart_bot")
            ]
        ]
    )

def order_admin_keyboard(order_id: int, user_id: int, status: str = "pending"):
    rows = []
    if status != "accepted":
        rows.append([
            InlineKeyboardButton(text="⏳ Qabul qilish (Moderator)", callback_data=f"accept_order:{order_id}:{user_id}")
        ])
    rows.append([
        InlineKeyboardButton(text="✉️ Javob / Kod yuborish", callback_data=f"ans_order:{order_id}:{user_id}"),
        InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"done_order:{order_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
