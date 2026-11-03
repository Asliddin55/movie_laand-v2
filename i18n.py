# ===================== 2 TILLI LOKALIZATSIYA TIZIMI (UZ / RU) =====================

DEFAULT_RULES_UZ = (
    "📜 <b>MOVIE LAND ULTRA — BOT VA GURUH QOIDALARI</b>\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "1️⃣ <b>Hurmat va odob:</b> Mavzuli guruhda so'kinish, haqorat qilish va urush chiqarish qat'iyan taqiqlanadi.\n"
    "2️⃣ <b>Reklama taqiqlanadi:</b> Guruhda va bot orqali begona kanallar, botlar yoki havolalarni tarqatish — umrbod Ban.\n"
    "3️⃣ <b>Bo'limlarga rioya qilish:</b>\n"
    "   • 👑 <b>Чат Muhokama</b> — erkin suhbat va kinolar muhokamasi;\n"
    "   • ⭐ <b>Buyurtmalar</b> — faqat kino so'rovlari uchun;\n"
    "   • 💸 <b>Premium</b> — faqat VIP sotib olgan foydalanuvchilar fikri (otzivlari) uchun.\n"
    "4️⃣ <b>To'lov va Cheklar:</b> Soxta (feyk) to'lov cheki yuborgan foydalanuvchilar botdan va guruhdan bloklanadi.\n"
    "5️⃣ <b>Kontent himoyasi:</b> Botdagi barcha kinolar mualliflik va maxfiylik tizimi bilan himoyalangan.\n\n"
    "📌 <b>Mavzuli guruhdagi qoidalar bo'limi:</b> <a href='https://t.me/movieeland_group/195'>💎 Правила Qoidalar</a>"
)

DEFAULT_RULES_RU = (
    "📜 <b>MOVIE LAND ULTRA — ПРАВИЛА БОТА И ГРУППЫ</b>\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "1️⃣ <b>Уважение и культура:</b> В тематической группе строго запрещены оскорбления, нецензурная лексика и конфликты.\n"
    "2️⃣ <b>Запрет рекламы:</b> Спам, реклама сторонних каналов, ботов или ссылок карается вечным баном.\n"
    "3️⃣ <b>Соблюдение разделов (Топиков):</b>\n"
    "   • 👑 <b>Чат Muhokama</b> — общение и обсуждение фильмов;\n"
    "   • ⭐ <b>Buyurtmalar</b> — только для заказов фильмов;\n"
    "   • 💸 <b>Premium</b> — только для отзывов покупателей VIP.\n"
    "4️⃣ <b>Оплата и чеки:</b> За отправку поддельных (фейковых) чеков оплаты — блокировка в боте и группе.\n"
    "5️⃣ <b>Защита контента:</b> Все фильмы в боте защищены системой анти-пересылки.\n\n"
    "📌 <b>Раздел правил в группе:</b> <a href='https://t.me/movieeland_group/195'>💎 Правила Qoidalar</a>"
)


# User Main Menu Buttons (UZ & RU)
BTN = {
    "search": {"uz": "🔍 Kino qidirish", "ru": "🔍 Поиск фильма"},
    "random": {"uz": "🎲 Tasodifiy kino", "ru": "🎲 Случайный фильм"},
    "top": {"uz": "🔥 Top-10 Kinolar", "ru": "🔥 Топ-10 Фильмов"},
    "new": {"uz": "🆕 Premyeralar", "ru": "🆕 Премьеры"},
    "genres": {"uz": "🎭 Janrlar katalogi", "ru": "🎭 Каталог жанров"},
    "serials": {"uz": "🎞 Seriallar", "ru": "🎞 Сериалы"},
    "earn": {"uz": "🎁 Kunlik Bonus & Pul ishlash", "ru": "🎁 Ежедневный бонус и Заработок"},
    "topic_group": {"uz": "🌐 Mavzuli Guruh", "ru": "🌐 Тематическая группа"},
    "favs": {"uz": "⭐ Sevimlilarim", "ru": "⭐ Избранное"},
    "order": {"uz": "🎬 Kino buyurtma", "ru": "🎬 Заказать фильм"},
    "vip_shop": {"uz": "💎 Premium (VIP) Do'kon", "ru": "💎 Магазин Premium (VIP)"},
    "cabinet": {"uz": "👤 Shaxsiy Kabinet", "ru": "👤 Личный кабинет"},
    "rules": {"uz": "📜 Qoidalar", "ru": "📜 Правила"},
    "lang": {"uz": "🌐 Til / Язык", "ru": "🌐 Язык / Til"},
    "cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена"},
    "user_menu": {"uz": "🏠 Foydalanuvchi menyusi", "ru": "🏠 Меню пользователя"},
}


def b_vals(key: str) -> list:
    """Ikkala tildagi tugma matnlarini ro'yxat sifatida qaytaradi (F.text.in_(...) uchun)."""
    item = BTN.get(key, {})
    return list(set(item.values()))


TEXTS = {
    "choose_lang": {
        "uz": (
            "🇺🇿 <b>Assalomu alaykum! Tilni tanlang:</b>\n"
            "🇷🇺 <b>Здравствуйте! Пожалуйста, выберите язык бота:</b>"
        ),
        "ru": (
            "🇷🇺 <b>Здравствуйте! Пожалуйста, выберите язык бота:</b>\n"
            "🇺🇿 <b>Assalomu alaykum! Tilni tanlang:</b>"
        ),
    },
    "lang_saved": {
        "uz": "✅ <b>O'zbek tili tanlandi!</b> Barcha menyular o'zbek tiliga o'tkazildi.",
        "ru": "✅ <b>Выбран русский язык!</b> Все разделы и меню переведены на русский язык.",
    },
    "banned": {
        "uz": "🚫 <b>Siz botdan bloklangansiz!</b>",
        "ru": "🚫 <b>Вы заблокированы в боте!</b>",
    },
    "maintenance": {
        "uz": "🛠 <b>Botda hozir texnik ishlar olib borilmoqda. Tez orada ishga tushadi!</b>",
        "ru": "🛠 <b>В боте ведутся технические работы. Скоро мы снова запустимся!</b>",
    },
    "sub_prompt": {
        "uz": (
            "✦ <b>MOVIE LAND ULTRA</b> ✦\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👋 <b>Assalomu alaykum, {name}!</b>\n\n"
            "<blockquote>🎬 <b>Botdan to'liq foydalanish uchun quyidagi rasmiy kanallarimizga obuna bo'ling:</b></blockquote>"
        ),
        "ru": (
            "✦ <b>MOVIE LAND ULTRA</b> ✦\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👋 <b>Здравствуйте, {name}!</b>\n\n"
            "<blockquote>🎬 <b>Для полного доступа к боту подпишитесь на наши официальные каналы:</b></blockquote>"
        ),
    },
    "sub_not_all": {
        "uz": "❌ <b>Hali barcha kanallarga obuna bo'lmadingiz!</b>\nIltimos, har bir kanalga a'zo bo'ling va qayta tekshiring.",
        "ru": "❌ <b>Вы еще не подписались на все каналы!</b>\nПожалуйста, подпишитесь на каждый канал и проверьте снова.",
    },
    "sub_ok": {
        "uz": "✅ <b>Obuna muvaffaqiyatli tasdiqlandi!</b>\nMarhamat, bot imkoniyatlaridan to'liq foydalanishingiz mumkin.",
        "ru": "✅ <b>Подписка успешно подтверждена!</b>\nДобро пожаловать, вы можете пользоваться ботом без ограничений.",
    },
    "sub_first": {
        "uz": (
            "✦ <b>MOVIE LAND ULTRA</b> ✦\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<blockquote>⚠️ <b>Botdan foydalanishdan avval quyidagi kanallarga a'zo bo'ling!</b>\n\n"
            "🚫 <i>Iltimos, botdan to'g'ri foydalanish uchun kanallardan chiqib ketishga urinmang.</i></blockquote>\n"
            "👇 <i>Kanallarga obuna bo'lib, <b>«✅ Obunani tekshirish»</b> tugmasini bosing:</i>"
        ),
        "ru": (
            "✦ <b>MOVIE LAND ULTRA</b> ✦\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<blockquote>⚠️ <b>Перед использованием бота подпишитесь на каналы ниже!</b>\n\n"
            "🚫 <i>Пожалуйста, не пытайтесь выходить из каналов, чтобы правильно пользоваться ботом.</i></blockquote>\n"
            "👇 <i>Подпишитесь на каналы и нажмите <b>«✅ Проверить подписку»</b>:</i>"
        ),
    },
    "left_channel_warn": {
        "uz": (
            "⚠️ <b>DIQQAT! KANALDAN CHIQISH ANIQLANDI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<blockquote>Siz majburiy obuna kanalimizdan («{title}») chiqib ketdingiz!\n\n"
            "🚫 <b>Iltimos, botdan to'g'ri va uzluksiz foydalanish uchun kanallardan chiqib ketishga urinmang!</b>\n"
            "Aks holda bot xizmatlaridan foydalanish cheklanadi.</blockquote>\n\n"
            "👇 <i>Qayta obuna bo'ling va <b>«✅ Obunani tekshirish»</b> tugmasini bosing:</i>"
        ),
        "ru": (
            "⚠️ <b>ВНИМАНИЕ! ВЫХОД ИЗ КАНАЛА ОБНАРУЖЕН</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<blockquote>Вы покинули наш обязательный канал («{title}»)!\n\n"
            "🚫 <b>Пожалуйста, не пытайтесь выходить из каналов для непрерывной работы бота!</b>\n"
            "При выходе доступ к просмотру фильмов блокируется.</blockquote>\n\n"
            "👇 <i>Подпишитесь заново и нажмите <b>«✅ Проверить подписку»</b>:</i>"
        ),
    },
    "sub_left_reminder": {
        "uz": (
            "⚠️ <b>Siz botdagi majburiy kanallardan chiqib ketgansiz!</b>\n\n"
            "<blockquote>🚫 <i>Iltimos, botdan to'g'ri foydalanish uchun kanallardan chiqib ketishga urinmang!</i></blockquote>\n\n"
            "👇 <i>Qayta a'zo bo'ling va <b>«✅ Obunani tekshirish»</b> tugmasini bosing:</i>"
        ),
        "ru": (
            "⚠️ <b>Вы вышли из обязательных каналов бота!</b>\n\n"
            "<blockquote>🚫 <i>Пожалуйста, не пытайтесь выходить из каналов, чтобы правильно пользоваться ботом!</i></blockquote>\n\n"
            "👇 <i>Подпишитесь заново и нажмите <b>«✅ Проверить подписку»</b>:</i>"
        ),
    },
    "welcome": {
        "uz": (
            "🍿 <b>MOVIE LAND ULTRA</b> ✦ <i>Kino Olami</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ <b>Assalomu alaykum, {name}!</b>\n"
            "Eng sara premyeralar, kino va seriallar platformasiga xush kelibsiz!\n\n"
            "🎖 <b>Maqomingiz:</b> {vip_badge}\n\n"
            "<blockquote>🔢 <b>Kino kodini</b> yuboring (masalan: <code>1</code>)\n"
            "🔤 Yoki kino <b>nomi / kalit so'zini</b> yozib qidiring!</blockquote>\n\n"
            "👇 <i>Quyidagi interaktiv menyudan kerakli bo'limni tanlang:</i>"
        ),
        "ru": (
            "🍿 <b>MOVIE LAND ULTRA</b> ✦ <i>Мир Кино</i>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ <b>Здравствуйте, {name}!</b>\n"
            "Добро пожаловать на платформу кино и сериалов <b>MOVIE LAND ULTRA</b>!\n\n"
            "🎖 <b>Ваш статус:</b> {vip_badge}\n\n"
            "<blockquote>🔢 Отправьте <b>код фильма</b> (например: <code>1</code>)\n"
            "🔤 Или напишите <b>название / ключевое слово</b> для поиска!</blockquote>\n\n"
            "👇 <i>Воспользуйтесь интерактивным меню ниже:</i>"
        ),
    },
    "vip_badge_active": {
        "uz": "💎 <b>PREMIUM VIP [{tag}]</b>",
        "ru": "💎 <b>PREMIUM VIP [{tag}]</b>",
    },
    "vip_badge_free": {
        "uz": "👤 <b>Oddiy foydalanuvchi</b>",
        "ru": "👤 <b>Обычный пользователь</b>",
    },
    "loading_movie": {
        "uz": "🎬 <b>Kino yuklanmoqda...</b> <i>Kuting</i> ⏳",
        "ru": "🎬 <b>Фильм загружается...</b> <i>Подождите</i> ⏳",
    },
    "movie_not_found_code": {
        "uz": (
            "❌ <b>#{code}</b> kodli kino topilmadi!\n\n"
            "<blockquote>💡 <i>Kino nomini yozib qidirib ko'ring yoki <b>🎬 Kino buyurtma</b> bo'limidan so'rov qoldiring.</i></blockquote>"
        ),
        "ru": (
            "❌ Фильм с кодом <b>#{code}</b> не найден!\n\n"
            "<blockquote>💡 <i>Попробуйте найти по названию или оставьте заявку в разделе <b>🎬 Заказать фильм</b>.</i></blockquote>"
        ),
    },
    "movie_not_found_text": {
        "uz": (
            "❌ <b>«{q}»</b> bo'yicha hech narsa topilmadi.\n\n"
            "<blockquote>💡 <i>Kino kodini to'g'ri kiriting yoki <b>«🎬 Kino buyurtma»</b> orqali buyurtma qoldiring!</i></blockquote>"
        ),
        "ru": (
            "❌ По запросу <b>«{q}»</b> фильмы не найдены.\n\n"
            "<blockquote>💡 <i>Проверьте код фильма или оставьте заявку через <b>«🎬 Заказать фильм»</b>!</i></blockquote>"
        ),
    },
    "cancelled": {
        "uz": "✅ Amal bekor qilindi.",
        "ru": "✅ Действие отменено.",
    },
    "search_prompt": {
        "uz": (
            "🔍 <b>AQLLI QIDIRUV TIZIMI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<blockquote>• Kino <b>kodini</b> yuboring (masalan: <code>1</code>)\n"
            "• Yoki kino <b>nomini / so'zini</b> yozib yuboring:</blockquote>"
        ),
        "ru": (
            "🔍 <b>УМНАЯ СИСТЕМА ПОИСКА</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<blockquote>• Отправьте <b>код фильма</b> (например: <code>1</code>)\n"
            "• Или напишите <b>название фильма / ключевое слово</b>:</blockquote>"
        ),
    },
    "search_results": {
        "uz": "🔍 <b>«{q}»</b> bo'yicha topilgan kinolar ({cnt} ta):",
        "ru": "🔍 Найденные фильмы по запросу <b>«{q}»</b> ({cnt} шт.):",
    },
    "choose_movie_above": {
        "uz": "Kerakli kinoni tanlang 👆",
        "ru": "Выберите нужный фильм выше 👆",
    },
    "genres_title": {
        "uz": "🎭 <b>Janrlar katalogi:</b>\nO'zingizga yoqqan janrni tanlang:",
        "ru": "🎭 <b>Каталог жанров:</b>\nВыберите интересующий вас жанр:",
    },
    "genre_empty": {
        "uz": "Hozircha {genre} janrida kinolar yo'q.",
        "ru": "В жанре {genre} пока нет фильмов.",
    },
    "genre_list": {
        "uz": "🎭 <b>{genre}</b> janridagi kinolar ({cnt} ta):",
        "ru": "🎭 Фильмы в жанре <b>{genre}</b> ({cnt} шт.):",
    },
    "db_empty": {
        "uz": "📭 Hozircha bazada kinolar yo'q.",
        "ru": "📭 В базе пока нет фильмов.",
    },
    "top_title": {
        "uz": "🔥 <b>Eng ko'p tomosha qilingan TOP-10 kinolar:</b>",
        "ru": "🔥 <b>ТОП-10 самых просматриваемых фильмов:</b>",
    },
    "new_title": {
        "uz": "🆕 <b>Botga yangi qo'shilgan premyera kinolar:</b>",
        "ru": "🆕 <b>Новые премьеры, добавленные в бот:</b>",
    },
    "serials_empty": {
        "uz": "📭 Hozircha ko'p qismli seriallar qo'shilmagan.",
        "ru": "📭 Многосерийные сериалы пока не добавлены.",
    },
    "serials_title": {
        "uz": "🎞 <b>Ko'p qismli Seriallar katalogi ({cnt} ta):</b>",
        "ru": "🎞 <b>Каталог многосерийных сериалов ({cnt} шт.):</b>",
    },
    "favs_empty": {
        "uz": (
            "⭐ <b>Sizda hali saqlangan kinolar yo'q.</b>\n\n"
            "💡 <i>Kino ostidagi «⭐ Saqlab qo'yish» tugmasini bosib kinolarni shu bo'limga qo'shishingiz mumkin!</i>"
        ),
        "ru": (
            "⭐ <b>У вас пока нет сохраненных фильмов.</b>\n\n"
            "💡 <i>Нажмите кнопку «⭐ Сохранить» под любым фильмом, чтобы добавить его в избранное!</i>"
        ),
    },
    "favs_title": {
        "uz": "⭐ <b>Sevimli kinolaringiz ({cnt} ta):</b>",
        "ru": "⭐ <b>Ваши избранные фильмы ({cnt} шт.):</b>",
    },
    "history_title": {
        "uz": "🕓 <b>Oxirgi ko'rgan kinolaringiz:</b>",
        "ru": "🕓 <b>Последние просмотренные фильмы:</b>",
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
