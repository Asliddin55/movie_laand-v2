# ===================== 2 TILLI LOKALIZATSIYA TIZIMI (UZ / RU) — ULTIMATE MINIMAL =====================
from config import pe

DEFAULT_RULES_UZ = (
    f"{pe('📜')} <b>MOVIE LAND ULTRA — QOIDALAR</b>\n\n"
    "1️⃣ <b>Hurmat:</b> Guruhda so'kinish va haqorat taqiqlanadi.\n"
    "2️⃣ <b>Reklama yo'q:</b> Begona havola va reklama — Ban.\n"
    "3️⃣ <b>Bo'limlar:</b> 👑 Muhokama • ⭐ Buyurtmalar • 💸 Premium.\n"
    "4️⃣ <b>To'lov:</b> Soxta chek yuborish — bloklash.\n\n"
    "📌 <a href='https://t.me/movieeland_group/195'>💎 Guruh qoidalari</a>"
)

DEFAULT_RULES_RU = (
    f"{pe('📜')} <b>MOVIE LAND ULTRA — ПРАВИЛА</b>\n\n"
    "1️⃣ <b>Уважение:</b> Оскорбления и конфликты запрещены.\n"
    "2️⃣ <b>Без рекламы:</b> Спам и чужие ссылки — вечный бан.\n"
    "3️⃣ <b>Разделы:</b> 👑 Общение • ⭐ Заказы • 💸 Отзывы.\n"
    "4️⃣ <b>Оплата:</b> Поддельные чеки — блокировка.\n\n"
    "📌 <a href='https://t.me/movieeland_group/195'>💎 Правила в группе</a>"
)


# User Main Menu Buttons (UZ & RU)
BTN = {
    "search": {"uz": "🔍 Kino qidirish", "ru": "🔍 Поиск фильма"},
    "webapp": {"uz": "📱 Movie Land WebApp", "ru": "📱 Movie Land WebApp"},
    "random": {"uz": "🎲 Tasodifiy", "ru": "🎲 Случайный"},
    "top": {"uz": "🔥 Top Kinolar", "ru": "🔥 Топ Фильмы"},
    "new": {"uz": "🆕 Premyeralar", "ru": "🆕 Премьеры"},
    "genres": {"uz": "🎭 Janrlar", "ru": "🎭 Жанры"},
    "serials": {"uz": "🎞 Seriallar", "ru": "🎞 Сериалы"},
    "earn": {"uz": "🎁 Bonus & Referal", "ru": "🎁 Бонус и Рефералы"},
    "topic_group": {"uz": "🌐 Guruh", "ru": "🌐 Группа"},
    "favs": {"uz": "⭐ Sevimlilar", "ru": "⭐ Избранное"},
    "order": {"uz": "🎬 Buyurtma", "ru": "🎬 Заказ"},
    "vip_shop": {"uz": "💎 VIP Do'kon", "ru": "💎 VIP Магазин"},
    "cabinet": {"uz": "👤 Kabinet", "ru": "👤 Кабинет"},
    "rules": {"uz": "📜 Qoidalar", "ru": "📜 Правила"},
    "lang": {"uz": "🌐 Til / Язык", "ru": "🌐 Язык / Til"},
    "cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена"},
    "user_menu": {"uz": "🏠 Foydalanuvchi menyusi", "ru": "🏠 Меню пользователя"},
}

# Eski tugma nomlarini ham qo'llab-quvvatlash (eskirgan klaviaturalar xato bermasligi uchun)
LEGACY_BTN_ALIASES = {
    "cabinet": ["👤 Shaxsiy Kabinet", "👤 Личный кабинет", "👤 Kabinet", "👤 Кабинет"],
    "search": ["🔍 Kino qidirish", "🔍 Поиск фильма"],
    "top": ["🔥 Top-10 Kinolar", "🔥 Топ-10 Фильмов", "🔥 Top Kinolar", "🔥 Топ Фильмы"],
    "new": ["🆕 Premyeralar", "🆕 Премьеры"],
    "genres": ["🎭 Janrlar katalogi", "🎭 Каталог жанров", "🎭 Janrlar", "🎭 Жанры"],
    "serials": ["🎞 Seriallar", "🎞 Сериалы"],
    "random": ["🎲 Tasodifiy kino", "🎲 Случайный фильм", "🎲 Tasodifiy", "🎲 Случайный"],
    "earn": ["🎁 Kunlik Bonus & Pul ishlash", "🎁 Ежедневный бонус и Заработок", "🎁 Bonus & Referal", "🎁 Бонус и Рефералы"],
    "vip_shop": ["💎 Premium (VIP) Do'kon", "💎 Магазин Premium (VIP)", "💎 VIP Do'kon", "💎 VIP Магазин"],
    "topic_group": ["🌐 Mavzuli Guruh", "🌐 Тематическая группа", "🌐 Guruh", "🌐 Группа"],
    "favs": ["⭐ Sevimlilarim", "⭐ Избранное", "⭐ Sevimlilar"],
    "order": ["🎬 Kino buyurtma", "🎬 Заказать фильм", "🎬 Buyurtma", "🎬 Заказ"],
    "rules": ["📜 Qoidalar", "📜 Правила"],
    "lang": ["🌐 Til / Язык", "🌐 Язык / Til"],
    "cancel": ["❌ Bekor qilish", "❌ Отмена"],
    "user_menu": ["🏠 Foydalanuvchi menyusi", "🏠 Меню пользователя", "🏠 Asosiy menyu"],
}


def b_vals(key: str) -> list:
    """Ikkala tildagi va eski tugma matnlarini ro'yxat sifatida qaytaradi (F.text.in_(...) uchun)."""
    item = BTN.get(key, {})
    vals = set(item.values())
    vals.update(LEGACY_BTN_ALIASES.get(key, []))
    return list(vals)


TEXTS = {
    "choose_lang": {
        "uz": f"{pe('🇺🇿')} <b>Tilni tanlang / Выберите язык:</b>",
        "ru": f"{pe('🇷🇺')} <b>Выберите язык / Tilni tanlang:</b>",
    },
    "lang_saved": {
        "uz": f"{pe('✅')} <b>O'zbek tili o'rnatildi.</b>",
        "ru": f"{pe('✅')} <b>Установлен русский язык.</b>",
    },
    "banned": {
        "uz": f"{pe('🚫')} <b>Siz bloklangansiz!</b>",
        "ru": f"{pe('🚫')} <b>Вы заблокированы!</b>",
    },
    "maintenance": {
        "uz": "🛠 <b>Texnik ishlar olib borilmoqda. Tez orada ishga tushadi!</b>",
        "ru": "🛠 <b>Технические работы. Скоро запустимся!</b>",
    },
    "sub_prompt": {
        "uz": (
            f"{pe('🎬')} <b>MOVIE LAND ULTRA</b>\n"
            "<blockquote>👋 <b>{name}</b>, davom etish uchun rasmiy kanallarimizga obuna bo'ling:</blockquote>"
        ),
        "ru": (
            f"{pe('🎬')} <b>MOVIE LAND ULTRA</b>\n"
            "<blockquote>👋 <b>{name}</b>, подпишитесь на официальные каналы для доступа:</blockquote>"
        ),
    },
    "sub_not_all": {
        "uz": "❌ Barcha kanallarga obuna bo'ling!",
        "ru": "❌ Подпишитесь на все каналы!",
    },
    "sub_ok": {
        "uz": f"{pe('✅')} <b>Obuna tasdiqlandi!</b>",
        "ru": f"{pe('✅')} <b>Подписка подтверждена!</b>",
    },
    "sub_first": {
        "uz": (
            f"{pe('🔒')} <b>MOVIE LAND ULTRA</b>\n"
            "<blockquote>⚠️ Kinolarni ko'rish uchun quyidagi kanallarga obuna bo'ling (kanallardan chiqib ketishga urinmang):</blockquote>"
        ),
        "ru": (
            f"{pe('🔒')} <b>MOVIE LAND ULTRA</b>\n"
            "<blockquote>⚠️ Подпишитесь на каналы ниже для просмотра (не покидайте каналы):</blockquote>"
        ),
    },
    "left_channel_warn": {
        "uz": (
            f"{pe('🚫')} <b>KANALDAN CHIQISH ANIQLANDI</b>\n"
            "<blockquote>Siz «{title}» kanalidan chiqdingiz. Botdan foydalanish uchun kanallardan chiqib ketishga urinmang!</blockquote>"
        ),
        "ru": (
            f"{pe('🚫')} <b>ВЫХОД ИЗ КАНАЛА</b>\n"
            "<blockquote>Вы покинули «{title}». Для работы бота не покидайте каналы!</blockquote>"
        ),
    },
    "sub_left_reminder": {
        "uz": "⚠️ <b>Majburiy kanallarga qayta obuna bo'ling</b> (kanallardan chiqib ketishga urinmang):",
        "ru": "⚠️ <b>Подпишитесь заново на обязательные каналы</b> (не покидайте каналы):",
    },
    "welcome": {
        "uz": (
            f"{pe('🍿')} <b>MOVIE LAND ULTRA</b>\n"
            f"<blockquote>{pe('👤')} <b>{{name}}</b> • {{vip_badge}}\n"
            f"{pe('🔍')} <i>Kino kodini yozing yoki «Kino qidirish» tugmasini bosing:</i></blockquote>"
        ),
        "ru": (
            f"{pe('🍿')} <b>MOVIE LAND ULTRA</b>\n"
            f"<blockquote>{pe('👤')} <b>{{name}}</b> • {{vip_badge}}\n"
            f"{pe('🔍')} <i>Отправьте код фильма или нажмите «Поиск фильмов»:</i></blockquote>"
        ),
    },
    "vip_badge_active": {
        "uz": f"{pe('💎')} <b>VIP [{{tag}}]</b>",
        "ru": f"{pe('💎')} <b>VIP [{{tag}}]</b>",
    },
    "vip_badge_free": {
        "uz": "Standard",
        "ru": "Standard",
    },
    "loading_movie": {
        "uz": f"{pe('⏳')} <b>Yuklanmoqda...</b>",
        "ru": f"{pe('⏳')} <b>Загрузка...</b>",
    },
    "movie_not_found_code": {
        "uz": f"{pe('❌')} <b>#{{code}}</b> kodli kino topilmadi.",
        "ru": f"{pe('❌')} Фильм <b>#{{code}}</b> не найден.",
    },
    "movie_not_found_text": {
        "uz": f"{pe('❌')} <b>«{{q}}»</b> topilmadi. «Kino qidirish» orqali qidiring.",
        "ru": f"{pe('❌')} <b>«{{q}}»</b> не найдено. Воспользуйтесь поиском фильмов.",
    },
    "cancelled": {
        "uz": f"{pe('✅')} Bekor qilindi.",
        "ru": f"{pe('✅')} Отменено.",
    },
    "search_prompt": {
        "uz": f"{pe('🔍')} <b>Kino qidirish yoki kodini kiriting:</b>",
        "ru": f"{pe('🔍')} <b>Откройте поиск фильмов или введите код:</b>",
    },
    "search_results": {
        "uz": f"{pe('🔍')} <b>«{{q}}»</b> ({'{cnt}'} ta):",
        "ru": f"{pe('🔍')} <b>«{{q}}»</b> ({'{cnt}'} шт.):",
    },
    "choose_movie_above": {
        "uz": "Kinoni tanlang 👆",
        "ru": "Выберите фильм 👆",
    },
    "genres_title": {
        "uz": f"{pe('🎭')} <b>Janrni tanlang:</b>",
        "ru": f"{pe('🎭')} <b>Выберите жанр:</b>",
    },
    "genre_empty": {
        "uz": "{genre} janrida kinolar yo'q.",
        "ru": "В жанре {genre} пока пусто.",
    },
    "genre_list": {
        "uz": f"{pe('🎭')} <b>{{genre}}</b> ({{cnt}} ta):",
        "ru": f"{pe('🎭')} <b>{{genre}}</b> ({{cnt}} шт.):",
    },
    "db_empty": {
        "uz": "📭 Bazada hozircha kinolar yo'q.",
        "ru": "📭 База фильмов пока пуста.",
    },
    "top_title": {
        "uz": f"{pe('🔥')} <b>TOP Kinolar:</b>",
        "ru": f"{pe('🔥')} <b>ТОП Фильмы:</b>",
    },
    "new_title": {
        "uz": f"{pe('🆕')} <b>Premyeralar:</b>",
        "ru": f"{pe('🆕')} <b>Премьеры:</b>",
    },
    "serials_empty": {
        "uz": "📭 Seriallar hali qo'shilmagan.",
        "ru": "📭 Сериалы пока не добавлены.",
    },
    "serials_title": {
        "uz": f"{pe('🎞')} <b>Seriallar ({{cnt}} ta):</b>",
        "ru": f"{pe('🎞')} <b>Сериалы ({{cnt}} шт.):</b>",
    },
    "favs_empty": {
        "uz": f"{pe('⭐')} <b>Sevimlilar ro'yxati bo'sh.</b>",
        "ru": f"{pe('⭐')} <b>Список избранного пуст.</b>",
    },
    "favs_title": {
        "uz": f"{pe('⭐')} <b>Sevimlilar ({{cnt}} ta):</b>",
        "ru": f"{pe('⭐')} <b>Избранное ({{cnt}} шт.):</b>",
    },
    "history_title": {
        "uz": "🕓 <b>Oxirgi ko'rilganlar:</b>",
        "ru": "🕓 <b>История просмотра:</b>",
    },
}


def t(key: str, lang: str = "uz", **kwargs) -> str:
    lang = lang if lang in ("uz", "ru") else "uz"
    val = TEXTS.get(key, {}).get(lang) or TEXTS.get(key, {}).get("uz", key)
    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val
