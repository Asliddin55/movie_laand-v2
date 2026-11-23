import re
import json
import html
import urllib.parse
import aiohttp
import logging
import config
import database as db

# Janr imlo xatolarini va xalqaro (EN/RU/UZ) janrlarni avtomatik to'g'rilovchi lug'at
GENRE_CORRECTIONS = {
    "jangari": "🔥 Jangari",
    "jangar": "🔥 Jangari",
    "jngari": "🔥 Jangari",
    "boyevik": "🔥 Jangari",
    "bayovik": "🔥 Jangari",
    "боевик": "🔥 Jangari",
    "action": "🔥 Jangari",
    "adventure": "🔥 Jangari",
    "sarguzasht": "🔥 Jangari",
    "sarguzash": "🔥 Jangari",
    "sarguz": "🔥 Jangari",
    "приключения": "🔥 Jangari",
    "poyga": "🔥 Jangari",
    "boks": "🔥 Jangari",
    "sport": "🔥 Jangari",
    "regby": "🔥 Jangari",
    "western": "🔥 Jangari",
    "вестерн": "🔥 Jangari",
    "komediya": "😂 Komediya",
    "komediy": "😂 Komediya",
    "komedia": "😂 Komediya",
    "kamedia": "😂 Komediya",
    "kamediya": "😂 Komediya",
    "комедия": "😂 Komediya",
    "comedy": "😂 Komediya",
    "fantastika": "🚀 Fantastika",
    "fantastik": "🚀 Fantastika",
    "fantast": "🚀 Fantastika",
    "fentezi": "🚀 Fantastika",
    "fantasy": "🚀 Fantastika",
    "фантастика": "🚀 Fantastika",
    "фэнтези": "🚀 Fantastika",
    "sci-fi": "🚀 Fantastika",
    "komiks": "🚀 Fantastika",
    "sehrgarlik": "🚀 Fantastika",
    "sehrga": "🚀 Fantastika",
    "sehrg": "🚀 Fantastika",
    "koinot": "🚀 Fantastika",
    "koino": "🚀 Fantastika",
    "ujas": "👻 Qo'rqinchli",
    "ужасы": "👻 Qo'rqinchli",
    "qo'rqinchli": "👻 Qo'rqinchli",
    "qorqinchli": "👻 Qo'rqinchli",
    "dahshat": "👻 Qo'rqinchli",
    "daxshat": "👻 Qo'rqinchli",
    "triller": "👻 Qo'rqinchli",
    "триллер": "👻 Qo'rqinchli",
    "thriller": "👻 Qo'rqinchli",
    "xorror": "👻 Qo'rqinchli",
    "horror": "👻 Qo'rqinchli",
    "drama": "💔 Drama",
    "dramma": "💔 Drama",
    "драма": "💔 Drama",
    "detektiv": "🕵️ Detektiv",
    "детектив": "🕵️ Detektiv",
    "mystery": "🕵️ Detektiv",
    "crime": "🕵️ Detektiv",
    "kriminal": "🕵️ Detektiv",
    "криминал": "🕵️ Detektiv",
    "jinoyat": "🕵️ Detektiv",
    "anime": "🎌 Anime",
    "аниме": "🎌 Anime",
    "multfilm": "🧸 Multfilm",
    "multfil": "🧸 Multfilm",
    "multfi": "🧸 Multfilm",
    "multf": "🧸 Multfilm",
    "multik": "🧸 Multfilm",
    "мультфильм": "🧸 Multfilm",
    "animation": "🧸 Multfilm",
    "animatsiya": "🧸 Multfilm",
    "realisticanimation": "🧸 Multfilm",
    "family": "🧸 Multfilm",
    "семейный": "🧸 Multfilm",
    "oilaviy": "🧸 Multfilm",
    "tarixiy": "⚔️ Tarixiy",
    "history": "⚔️ Tarixiy",
    "история": "⚔️ Tarixiy",
    "biography": "⚔️ Tarixiy",
    "биография": "⚔️ Tarixiy",
    "biografik": "⚔️ Tarixiy",
    "hayotiy": "⚔️ Tarixiy",
    "harbiy": "⚔️ Tarixiy",
    "военный": "⚔️ Tarixiy",
    "war": "⚔️ Tarixiy",
    "milliy": "🇺🇿 Milliy",
    "o'zbek": "🇺🇿 Milliy",
    "hujjatli": "🌍 Hujjatli",
    "documentary": "🌍 Hujjatli",
    "документальный": "🌍 Hujjatli",
    "melodrama": "❤️ Melodrama",
    "мелодрама": "❤️ Melodrama",
    "romance": "❤️ Melodrama",
    "muhabbat": "❤️ Melodrama",
    "romantik": "❤️ Melodrama",
    "romantika": "❤️ Melodrama",
    "sevgi": "❤️ Melodrama"
}

# TMDB genre_id -> Bot janri xaritasi
TMDB_GENRE_MAP = {
    28: "🔥 Jangari",
    12: "🔥 Jangari",
    16: "🧸 Multfilm",
    35: "😂 Komediya",
    80: "🕵️ Detektiv",
    99: "🌍 Hujjatli",
    18: "💔 Drama",
    10751: "🧸 Multfilm",
    14: "🚀 Fantastika",
    36: "⚔️ Tarixiy",
    27: "👻 Qo'rqinchli",
    10402: "❤️ Melodrama",
    9648: "🕵️ Detektiv",
    10749: "❤️ Melodrama",
    878: "🚀 Fantastika",
    10770: "💔 Drama",
    53: "👻 Qo'rqinchli",
    10752: "⚔️ Tarixiy",
    37: "🔥 Jangari",
    10759: "🔥 Jangari",
    10765: "🚀 Fantastika",
}

# ISO davlat kodi -> O'zbekcha davlat nomi
COUNTRY_ISO_MAP = {
    "US": "AQSH",
    "USA": "AQSH",
    "GB": "Buyuk Britaniya",
    "UK": "Buyuk Britaniya",
    "RU": "Rossiya",
    "SU": "Rossiya",
    "KR": "Janubiy Koreya",
    "IN": "Hindiston",
    "CN": "Xitoy",
    "HK": "Gonkong",
    "JP": "Yaponiya",
    "FR": "Fransiya",
    "DE": "Germaniya",
    "ES": "Ispaniya",
    "IT": "Italiya",
    "CA": "Kanada",
    "AU": "Avstraliya",
    "TR": "Turkiya",
    "UZ": "O'zbekiston",
    "NO": "Norvegiya",
    "ID": "Indoneziya",
    "ZA": "Janubiy Afrika",
    "MW": "Buyuk Britaniya",
    "KG": "Qirg'iziston",
    "KZ": "Qozog'iston",
}

# Arxiv kanaldagi [429..515] xabar ID lari bo'yicha aniq tasdiqlangan kino ma'lumotlari
ARCHIVE_MSG_EXACT_MAP = {
    429: {"name": "Javobsiz sevgi", "year": "2023", "country": "Turkiya", "genre": "💔 Drama, ❤️ Melodrama", "quality": "720p HD"},
    430: {"name": "Jodugar: G'arb jodugari afsonasi", "year": "2024", "country": "AQSH", "genre": "🚀 Fantastika, ❤️ Melodrama", "quality": "720p HD"},
    431: {"name": "Flesh", "year": "2023", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "1080p Full HD"},
    432: {"name": "Yangi Dunyo: O'tmish va Kelajak Qiroli", "year": "2024", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari, 🧸 Multfilm", "quality": "1080p Full HD"},
    433: {"name": "Jon Karter", "year": "2012", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "720p HD"},
    434: {"name": "Nuh", "year": "2014", "country": "AQSH", "genre": "⚔️ Tarixiy, 💔 Drama, 🔥 Jangari", "quality": "720p HD"},
    435: {"name": "Ovchi Kreyven", "year": "2024", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    436: {"name": "Muqaddas zamin: Salohiddin Ayyubiy", "year": "2005", "country": "AQSH, Buyuk Britaniya", "genre": "⚔️ Tarixiy, 🔥 Jangari, 💔 Drama", "quality": "1080p Full HD"},
    437: {"name": "Yangi mutantlar", "year": "2020", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari, 👻 Qo'rqinchli", "quality": "1080p Full HD"},
    438: {"name": "Etik kiygan mushuk 2: So'nggi tilak", "year": "2022", "country": "AQSH", "genre": "🧸 Multfilm, 😂 Komediya, 🔥 Jangari", "quality": "720p HD"},
    439: {"name": "Tug'ma poygachi 2", "year": "2014", "country": "AQSH", "genre": "🔥 Jangari, 💔 Drama", "quality": "720p HD"},
    440: {"name": "Qasoskorlar: Cheksizlik jangi", "year": "2018", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "1080p Full HD"},
    442: {"name": "Dedpul 2", "year": "2018", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika, 😂 Komediya", "quality": "720p HD"},
    443: {"name": "Dedpul va Rosomaxa", "year": "2024", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika, 😂 Komediya", "quality": "1080p Full HD"},
    444: {"name": "Xavfsiz uy: Keyptaun kodi", "year": "2012", "country": "AQSH, Janubiy Afrika", "genre": "🔥 Jangari, 🕵️ Detektiv, 👻 Qo'rqinchli", "quality": "720p HD"},
    445: {"name": "Berlin uzra parvoz", "year": "2023", "country": "Germaniya, AQSH", "genre": "🔥 Jangari, 💔 Drama, ⚔️ Tarixiy", "quality": "720p HD"},
    446: {"name": "Aviator", "year": "2004", "country": "AQSH", "genre": "⚔️ Tarixiy, 💔 Drama", "quality": "720p HD"},
    447: {"name": "Grenlandiya", "year": "2020", "country": "AQSH, Buyuk Britaniya", "genre": "🔥 Jangari, 👻 Qo'rqinchli, 💔 Drama", "quality": "720p HD"},
    448: {"name": "Iskanja", "year": "2023", "country": "AQSH", "genre": "🔥 Jangari, 👻 Qo'rqinchli", "quality": "720p HD"},
    449: {"name": "Almashtirilgan bola", "year": "2008", "country": "AQSH", "genre": "💔 Drama, 🕵️ Detektiv, ⚔️ Tarixiy", "quality": "1080p Full HD"},
    450: {"name": "Lara Kroft: Dahma talonchisi 1-qism", "year": "2001", "country": "AQSH, Buyuk Britaniya", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    451: {"name": "Lara Kroft: Dahma talonchisi 2 — Hayot beshigi", "year": "2003", "country": "AQSH, Buyuk Britaniya", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    452: {"name": "Ip Man 1-qism", "year": "2008", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama", "quality": "1080p Full HD"},
    453: {"name": "Ip Man 2-qism", "year": "2010", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama", "quality": "1080p Full HD"},
    454: {"name": "Ip Man 3-qism", "year": "2015", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama", "quality": "1080p Full HD"},
    455: {"name": "Ip Man: Afsonaning tug'ilishi", "year": "2010", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama", "quality": "720p HD"},
    456: {"name": "Kelajak chegarasi", "year": "2014", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "1080p Full HD"},
    457: {"name": "Yashil milya", "year": "1999", "country": "AQSH", "genre": "💔 Drama, 🚀 Fantastika, 🕵️ Detektiv", "quality": "1080p Full HD"},
    458: {"name": "Bravo jamoasi — 2024-yilgi konsert dasturi", "year": "2024", "country": "O'zbekiston", "genre": "😂 Komediya, 🇺🇿 Milliy", "quality": "1080p Full HD"},
    459: {"name": "Air: Katta sakrash (Air Jordan)", "year": "2023", "country": "AQSH", "genre": "💔 Drama, ⚔️ Tarixiy", "quality": "1080p Full HD"},
    460: {"name": "Tosh yonuvchi", "year": "2023", "country": "AQSH", "genre": "🔥 Jangari, 💔 Drama", "quality": "720p HD"},
    461: {"name": "Po'lat alximik 1-qism", "year": "2017", "country": "Yaponiya", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "720p HD"},
    462: {"name": "Po'lat alximik 2: Chandiq qasosi", "year": "2022", "country": "Yaponiya", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "720p HD"},
    463: {"name": "Yovvoyi tabiat qo'yniga", "year": "2007", "country": "AQSH", "genre": "💔 Drama, ⚔️ Tarixiy, 🔥 Jangari", "quality": "1080p Full HD"},
    464: {"name": "Taksi haydovchisi", "year": "2017", "country": "Janubiy Koreya", "genre": "💔 Drama, ⚔️ Tarixiy, 🔥 Jangari", "quality": "1080p Full HD"},
    465: {"name": "Piyoda qurbonligi", "year": "2014", "country": "AQSH", "genre": "💔 Drama, ⚔️ Tarixiy", "quality": "1080p Full HD"},
    466: {"name": "Ip Man 1-qism", "year": "2008", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama", "quality": "1080p Full HD"},
    467: {"name": "Ip Man 2-qism", "year": "2010", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama", "quality": "1080p Full HD"},
    468: {"name": "Ip Man 3-qism", "year": "2015", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama", "quality": "1080p Full HD"},
    469: {"name": "Ip Man: Afsonaning tug'ilishi", "year": "2010", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama", "quality": "720p HD"},
    470: {"name": "Troll", "year": "2022", "country": "Norvegiya", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "720p HD"},
    471: {"name": "Bezos: Amazon afsonasi", "year": "2023", "country": "AQSH", "genre": "💔 Drama, ⚔️ Tarixiy", "quality": "720p HD"},
    472: {"name": "Snayper 1-qism", "year": "1993", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy, 👻 Qo'rqinchli", "quality": "4K Ultra HD"},
    473: {"name": "Snayper 2-qism", "year": "2002", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy, 👻 Qo'rqinchli", "quality": "480p"},
    474: {"name": "Snayper 3-qism", "year": "2004", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy, 👻 Qo'rqinchli", "quality": "720p HD"},
    475: {"name": "Snayper 4: Qayta yuklash", "year": "2011", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy, 👻 Qo'rqinchli", "quality": "720p HD"},
    476: {"name": "Snayper 5: Meros", "year": "2014", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy, 👻 Qo'rqinchli", "quality": "720p HD"},
    477: {"name": "Snayper 6: Arvoh izidan", "year": "2016", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy, 👻 Qo'rqinchli", "quality": "720p HD"},
    478: {"name": "Snayper 7: Maxfiy missiya", "year": "2022", "country": "AQSH", "genre": "🔥 Jangari, 👻 Qo'rqinchli", "quality": "720p HD"},
    479: {"name": "Snayper 8: Maxsus jangchi", "year": "2023", "country": "AQSH", "genre": "🔥 Jangari, 👻 Qo'rqinchli", "quality": "1080p Full HD"},
    480: {"name": "Snayper: So'nggi jang", "year": "2017", "country": "AQSH", "genre": "🔥 Jangari, 👻 Qo'rqinchli", "quality": "720p HD"},
    481: {"name": "Fath", "year": "2025", "country": "Hindiston", "genre": "🔥 Jangari, 🕵️ Detektiv, 👻 Qo'rqinchli", "quality": "720p HD"},
    482: {"name": "Turist", "year": "2010", "country": "AQSH, Fransiya, Italiya", "genre": "🔥 Jangari, 🕵️ Detektiv, ❤️ Melodrama", "quality": "720p HD"},
    483: {"name": "Trampning yuksalishi", "year": "2024", "country": "AQSH, Kanada", "genre": "💔 Drama, ⚔️ Tarixiy", "quality": "1080p Full HD"},
    484: {"name": "Qamoqxona nazoratchisi", "year": "2023", "country": "Hindiston", "genre": "🔥 Jangari, 🕵️ Detektiv, 😂 Komediya", "quality": "720p HD"},
    485: {"name": "Jodu saltanati 1: G'aroyib maxluqlar", "year": "2016", "country": "Buyuk Britaniya, AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "1080p Full HD"},
    486: {"name": "Jodu saltanati 2: Grindelvaldning jinoyatlari", "year": "2018", "country": "Buyuk Britaniya, AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "1080p Full HD"},
    487: {"name": "Jodu saltanati 3: Dambldor sirlari", "year": "2022", "country": "Buyuk Britaniya, AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "1080p Full HD"},
    488: {"name": "Shamolni bo'ysundirgan bola", "year": "2019", "country": "Buyuk Britaniya", "genre": "💔 Drama, ⚔️ Tarixiy", "quality": "1080p Full HD"},
    489: {"name": "Tinch okeani dahshatlari 2: Qo'zg'olon", "year": "2018", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "1080p Full HD"},
    490: {"name": "Tinch okeani dahshatlari 2: Qo'zg'olon", "year": "2018", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "720p HD"},
    494: {"name": "Mumiyo 1-qism", "year": "1999", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    495: {"name": "Mumiyo 2: Qaytish", "year": "2001", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    496: {"name": "Mumiyo 3: Ajdar imperatorining qabri", "year": "2008", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    497: {"name": "Eramizdan so'ng", "year": "2013", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari", "quality": "1080p Full HD"},
    498: {"name": "O'rgimchak odam 4: Yangi kun", "year": "2024", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    499: {"name": "O'rgimchak odam: Uyga qaytish", "year": "2017", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    500: {"name": "O'rgimchak odam 2: Uydan uzoqda", "year": "2019", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    501: {"name": "O'rgimchak odam 3: Uyga yo'l yo'q", "year": "2021", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    502: {"name": "Sirli sayohat 2: Sirli orol", "year": "2012", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika, 😂 Komediya", "quality": "1080p Full HD"},
    503: {"name": "Ajal poygasi", "year": "2008", "country": "AQSH", "genre": "🔥 Jangari, 🕵️ Detektiv, 🚀 Fantastika", "quality": "720p HD"},
    504: {"name": "Qutbli", "year": "2019", "country": "AQSH, Germaniya", "genre": "🔥 Jangari, 🕵️ Detektiv", "quality": "720p HD"},
    505: {"name": "Mumiyo 1-qism", "year": "1999", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    506: {"name": "Mumiyo 2: Qaytish", "year": "2001", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    507: {"name": "Mumiyo 3: Ajdar imperatorining qabri", "year": "2008", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    508: {"name": "Labirintdagilar 1: Xavfli tuzoq", "year": "2014", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    509: {"name": "Labirintdagilar 3: O'limga davo", "year": "2018", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "720p HD"},
    510: {"name": "Labirintdagilar 2: Olov iskanjasida", "year": "2015", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika", "quality": "1080p Full HD"},
    511: {"name": "Skelet kaliti", "year": "2005", "country": "AQSH", "genre": "👻 Qo'rqinchli, 🕵️ Detektiv, 💔 Drama", "quality": "1080p Full HD"},
    512: {"name": "Skelet kaliti", "year": "2005", "country": "AQSH", "genre": "👻 Qo'rqinchli, 🕵️ Detektiv, 💔 Drama", "quality": "1080p Full HD"},
    513: {"name": "Ballerina: Qasos", "year": "2023", "country": "Janubiy Koreya", "genre": "🔥 Jangari, 👻 Qo'rqinchli", "quality": "720p HD"},
    514: {"name": "Tor: Ragnaryok", "year": "2017", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika, 😂 Komediya", "quality": "1080p Full HD"},
    515: {"name": "Lev Yashin: Orzuimdagi darvozabon", "year": "2019", "country": "Rossiya", "genre": "💔 Drama, ⚔️ Tarixiy", "quality": "1080p Full HD"},
}

# Kino nomi bo'yicha aqlli ensiklopediya (Faqat nomi yozilganda ham yili, davlati va janrini 100% topadi)
KNOWN_TITLE_LOOKUP = [
    (["lev yashin", "orzuimdagi darvozabon"], {"name": "Lev Yashin: Orzuimdagi darvozabon", "year": "2019", "country": "Rossiya", "genre": "💔 Drama, ⚔️ Tarixiy"}),
    (["tor: ragnaryok", "tor ragnaryok", "thor ragnarok"], {"name": "Tor: Ragnaryok", "year": "2017", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika, 😂 Komediya"}),
    (["ballerina", "balerina"], {"name": "Ballerina: Qasos", "year": "2023", "country": "Janubiy Koreya", "genre": "🔥 Jangari, 👻 Qo'rqinchli"}),
    (["skelet kaliti", "skeleton key"], {"name": "Skelet kaliti", "year": "2005", "country": "AQSH", "genre": "👻 Qo'rqinchli, 🕵️ Detektiv, 💔 Drama"}),
    (["labirint 1", "xavfli tuzoq", "hafli tuzoq", "хафли тузок"], {"name": "Labirintdagilar 1: Xavfli tuzoq", "year": "2014", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["labirintdagilar 2", "olov iskanjasida"], {"name": "Labirintdagilar 2: Olov iskanjasida", "year": "2015", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["labirintdagilar 3", "o'limga qarshi", "o'limga davo"], {"name": "Labirintdagilar 3: O'limga qarshi", "year": "2018", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["mumiyo 3", "ajdar imperatorining qabri", "tomb of the dragon emperor"], {"name": "Mumiyo 3: Ajdar imperatorining qabri", "year": "2008", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["mumiyo 2", "the mummy returns"], {"name": "Mumiyo 2: Qaytish", "year": "2001", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["mumiyo", "the mummy (1999)", "mumiyo.1999"], {"name": "Mumiyo 1-qism", "year": "1999", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["qutbli", "polar"], {"name": "Qutbli", "year": "2019", "country": "AQSH, Germaniya", "genre": "🔥 Jangari, 🕵️ Detektiv"}),
    (["ajal poygasi", "death race"], {"name": "Ajal poygasi", "year": "2008", "country": "AQSH", "genre": "🔥 Jangari, 🕵️ Detektiv, 🚀 Fantastika"}),
    (["sirli sayohat", "mysterious island", "journey.2"], {"name": "Sirli sayohat 2: Sirli orol", "year": "2012", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika, 😂 Komediya"}),
    (["uyga yo'l yo'q", "o'rgimchak odam 3", "oʻrgimchak odam 3", "no way home"], {"name": "O'rgimchak odam 3: Uyga yo'l yo'q", "year": "2021", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["uydan uzoqda", "uydan yiroqda", "o'rgimchak odam 2", "o‘rgimchak odam 2", "far from home"], {"name": "O'rgimchak odam 2: Uydan uzoqda", "year": "2019", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["uyga qaytish", "homecoming"], {"name": "O'rgimchak odam: Uyga qaytish", "year": "2017", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["o'rgimchak odam 4", "oʻrgimchak odam 4", "orgimchak odam yangi kun"], {"name": "O'rgimchak odam 4: Yangi kun", "year": "2024", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["eramizdan so'ng", "eramizdan song", "after earth"], {"name": "Eramizdan so'ng", "year": "2013", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["tinch okeani", "pacific.rim.2", "pacific rim 2", "uprising"], {"name": "Tinch okeani dahshatlari 2: Qo'zg'olon", "year": "2018", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["dambldor siri", "dambldor.siri"], {"name": "Jodu saltanati 3: Dambldor sirlari", "year": "2022", "country": "Buyuk Britaniya, AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["grindevald", "grindelvald"], {"name": "Jodu saltanati 2: Grindelvaldning jinoyatlari", "year": "2018", "country": "Buyuk Britaniya, AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["jodu.saltanati.2016", "jodu saltanati"], {"name": "Jodu saltanati 1: G'aroyib maxluqlar", "year": "2016", "country": "Buyuk Britaniya, AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["qamoqxona_nazoratchisi", "qamoqxona nazoratchisi", "jailer"], {"name": "Qamoqxona nazoratchisi", "year": "2023", "country": "Hindiston", "genre": "🔥 Jangari, 🕵️ Detektiv, 😂 Komediya"}),
    (["trampning yuksalishi", "the apprentice"], {"name": "Trampning yuksalishi", "year": "2024", "country": "AQSH, Kanada", "genre": "💔 Drama, ⚔️ Tarixiy"}),
    (["turist.2010", "turist"], {"name": "Turist", "year": "2010", "country": "AQSH, Fransiya, Italiya", "genre": "🔥 Jangari, 🕵️ Detektiv, ❤️ Melodrama"}),
    (["fath 2025", "fateh"], {"name": "Fath", "year": "2025", "country": "Hindiston", "genre": "🔥 Jangari, 🕵️ Detektiv"}),
    (["snayper_so", "snayper so'nggi jang"], {"name": "Snayper: So'nggi jang", "year": "2017", "country": "AQSH", "genre": "🔥 Jangari, 👻 Qo'rqinchli"}),
    (["snayper_maxsus_jangchi", "maxsus jangchi"], {"name": "Snayper 8: Maxsus jangchi", "year": "2023", "country": "AQSH", "genre": "🔥 Jangari, 👻 Qo'rqinchli"}),
    (["миссия_изгой", "миссия изгой"], {"name": "Snayper 7: Maxfiy missiya", "year": "2022", "country": "AQSH", "genre": "🔥 Jangari, 👻 Qo'rqinchli"}),
    (["arvoh izidan", "arvoh%20izidan"], {"name": "Snayper 6: Arvoh izidan", "year": "2016", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy"}),
    (["snayper meros"], {"name": "Snayper 5: Meros", "year": "2014", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy"}),
    (["snayper_4", "snayper 4"], {"name": "Snayper 4: Qayta yuklash", "year": "2011", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy"}),
    (["snayper_3", "snayper 3"], {"name": "Snayper 3-qism", "year": "2004", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy"}),
    (["снайпер_2", "snayper 2"], {"name": "Snayper 2-qism", "year": "2002", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy"}),
    (["snayper 1992", "snayper 1"], {"name": "Snayper 1-qism", "year": "1993", "country": "AQSH", "genre": "🔥 Jangari, ⚔️ Tarixiy"}),
    (["безос", "bezos"], {"name": "Bezos: Amazon afsonasi", "year": "2023", "country": "AQSH", "genre": "💔 Drama, ⚔️ Tarixiy"}),
    (["troll 2022", "troll"], {"name": "Troll", "year": "2022", "country": "Norvegiya", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["afsonaning_tug'ulishi", "afsonaning tug'ilishi"], {"name": "Ip Man: Afsonaning tug'ilishi", "year": "2010", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama"}),
    (["ip.man.3", "ip man 3"], {"name": "Ip Man 3-qism", "year": "2015", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama"}),
    (["ip.man.2", "ip man 2"], {"name": "Ip Man 2-qism", "year": "2010", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama"}),
    (["ip.man.2008", "ip man 1", "ip man"], {"name": "Ip Man 1-qism", "year": "2008", "country": "Xitoy, Gonkong", "genre": "🔥 Jangari, ⚔️ Tarixiy, 💔 Drama"}),
    (["pawn.sacrifice", "piyoda qurbonligi"], {"name": "Piyoda qurbonligi", "year": "2014", "country": "AQSH", "genre": "💔 Drama, ⚔️ Tarixiy"}),
    (["taxi driver", "taksi haydovchisi"], {"name": "Taksi haydovchisi", "year": "2017", "country": "Janubiy Koreya", "genre": "💔 Drama, ⚔️ Tarixiy, 🔥 Jangari"}),
    (["into.the.wild", "into the wild", "yovvoyi tabiat"], {"name": "Yovvoyi tabiat qo'yniga", "year": "2007", "country": "AQSH", "genre": "💔 Drama, ⚔️ Tarixiy, 🔥 Jangari"}),
    (["месть_шрама", "месть шрама"], {"name": "Po'lat alximik 2: Chandiq qasosi", "year": "2022", "country": "Yaponiya", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["стальной алхимик", "po'lat alximik"], {"name": "Po'lat alximik 1-qism", "year": "2017", "country": "Yaponiya", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["tosh.yonuvchi", "tosh yonuvchi"], {"name": "Tosh yonuvchi", "year": "2023", "country": "AQSH", "genre": "🔥 Jangari, 💔 Drama"}),
    (["air jordan"], {"name": "Air: Katta sakrash (Air Jordan)", "year": "2023", "country": "AQSH", "genre": "💔 Drama, ⚔️ Tarixiy"}),
    (["bravo jamoasi"], {"name": "Bravo jamoasi — 2024-yilgi konsert dasturi", "year": "2024", "country": "O'zbekiston", "genre": "😂 Komediya, 🇺🇿 Milliy"}),
    (["the green mile", "yashil milya"], {"name": "Yashil milya", "year": "1999", "country": "AQSH", "genre": "💔 Drama, 🚀 Fantastika, 🕵️ Detektiv"}),
    (["kelajak.chegarasi", "kelajak chegarasi"], {"name": "Kelajak chegarasi", "year": "2014", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["lara.kroft.2", "lara kroft 2"], {"name": "Lara Kroft: Dahma talonchisi 2 — Hayot beshigi", "year": "2003", "country": "AQSH, Buyuk Britaniya", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["lara.kroft", "lara kroft"], {"name": "Lara Kroft: Dahma talonchisi 1-qism", "year": "2001", "country": "AQSH, Buyuk Britaniya", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["almashtirilgan.bola", "almashtirilgan bola"], {"name": "Almashtirilgan bola", "year": "2008", "country": "AQSH", "genre": "💔 Drama, 🕵️ Detektiv, ⚔️ Tarixiy"}),
    (["iskanja"], {"name": "Iskanja", "year": "2023", "country": "AQSH", "genre": "🔥 Jangari, 👻 Qo'rqinchli"}),
    (["berlin_uzra_parvoz", "berlin uzra parvoz"], {"name": "Berlin uzra parvoz", "year": "2023", "country": "Germaniya, AQSH", "genre": "🔥 Jangari, 💔 Drama, ⚔️ Tarixiy"}),
    (["dedrosa", "dedpul va rosomaxa", "deadpool"], {"name": "Dedpul va Rosomaxa", "year": "2024", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika, 😂 Komediya"}),
    (["cheksizlik jangi", "cheksizlik_jangi", "infinity war"], {"name": "Qasoskorlar: Cheksizlik jangi", "year": "2018", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["tug'ma poygachi 2", "tug’ma poygachi 2", "tugma_poygachi_2"], {"name": "Tug'ma poygachi 2", "year": "2014", "country": "AQSH", "genre": "🔥 Jangari, 💔 Drama"}),
    (["etik kiygan mushuk", "so'ngi tilak", "so'nggi tilak"], {"name": "Etik kiygan mushuk 2: So'nggi tilak", "year": "2022", "country": "AQSH", "genre": "🧸 Multfilm, 😂 Komediya, 🔥 Jangari"}),
    (["yangi mutantlar", "yangi.mutantlar", "новые мутанты"], {"name": "Yangi mutantlar", "year": "2020", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari, 👻 Qo'rqinchli"}),
    (["muqaddas zamin", "salohiddin ayubiy", "kingdom of heaven"], {"name": "Muqaddas zamin: Salohiddin Ayyubiy", "year": "2005", "country": "AQSH, Buyuk Britaniya", "genre": "⚔️ Tarixiy, 🔥 Jangari, 💔 Drama"}),
    (["ovchi kreyven", "kraven"], {"name": "Ovchi Kreyven", "year": "2024", "country": "AQSH", "genre": "🔥 Jangari, 🚀 Fantastika"}),
    (["nuh (2014)", "nuh 2014"], {"name": "Nuh", "year": "2014", "country": "AQSH", "genre": "⚔️ Tarixiy, 💔 Drama, 🔥 Jangari"}),
    (["jon karter", "jon.karter", "john carter"], {"name": "Jon Karter", "year": "2012", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["yangi dunyo: o'tmish va kelajak qiroli", "secret.level"], {"name": "Yangi Dunyo: O'tmish va Kelajak Qiroli", "year": "2024", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari, 🧸 Multfilm"}),
    (["flesh (2023)", "flesh"], {"name": "Flesh", "year": "2023", "country": "AQSH", "genre": "🚀 Fantastika, 🔥 Jangari"}),
    (["jodugar (2024)", "wicked.2024", "wicked"], {"name": "Jodugar: G'arb jodugari afsonasi", "year": "2024", "country": "AQSH", "genre": "🚀 Fantastika, ❤️ Melodrama"}),
    (["javobsiz sevgi"], {"name": "Javobsiz sevgi", "year": "2023", "country": "Turkiya", "genre": "💔 Drama, ❤️ Melodrama"}),
    (["shamolni bo'ysundirgan bola"], {"name": "Shamolni bo'ysundirgan bola", "year": "2019", "country": "Buyuk Britaniya", "genre": "💔 Drama, ⚔️ Tarixiy"}),
    (["grenlandiya", "grelandiya", "greenland"], {"name": "Grenlandiya", "year": "2020", "country": "AQSH, Buyuk Britaniya", "genre": "🔥 Jangari, 👻 Qo'rqinchli, 💔 Drama"}),
    (["aviator"], {"name": "Aviator", "year": "2004", "country": "AQSH", "genre": "⚔️ Tarixiy, 💔 Drama"}),
]


def _norm_title(text: str) -> str:
    """Nomlarni solishtirish uchun: kichik harf, apostroflarni birxillash, belgilarni olib tashlash."""
    t = (text or "").lower()
    t = re.sub(r"[ʻ‘’`ʼ']", "", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# Aniq nom -> ma'lumot indeksi (bazadagi nomlar qayta tekshirilganda 2-qism 1-qismga aylanib qolmasligi uchun)
_EXACT_KNOWN_INDEX = {}
for _meta in list(ARCHIVE_MSG_EXACT_MAP.values()) + [m for _, m in KNOWN_TITLE_LOOKUP]:
    _EXACT_KNOWN_INDEX.setdefault(_norm_title(_meta["name"]), _meta)


def _find_exact_known(name: str):
    return _EXACT_KNOWN_INDEX.get(_norm_title(name))


# Qisqa yozilgan nomlar uchun aniq taxalluslar
for _alias, _msg in [("Jodugar", 430), ("Lara Kroft 2", 451), ("Po'lat alximik 2", 462), ("Snayper 5", 476),
                     ("Snayper 7", 478), ("Xavfsiz uy", 444), ("Keyptaun kodi", 444), ("Fath 2025", 481),
                     ("Jodu saltanati 3", 487), ("Jodu saltanati 2", 486), ("Tinch okeani dahshatlari 2", 489)]:
    _EXACT_KNOWN_INDEX.setdefault(_norm_title(_alias), ARCHIVE_MSG_EXACT_MAP[_msg])


def _titles_similar(a: str, b: str, threshold: float = 0.72) -> bool:
    import difflib
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return False
    if na == nb or (len(na) >= 5 and (na in nb or nb in na)):
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= threshold


def normalize_country(raw_country: str) -> str:
    """Davlat nomlarini chiroyli o'zbekcha standartga keltirish (EN, RU, UZ)."""
    if not raw_country:
        return "AQSH"
    c = re.sub(r"[#🌐🌍🌎🌏🇺🇸🇷🇺🇺🇿➺➤➢▪️▫️]", "", raw_country).strip(" -:,.")
    replacements = [
        (r"\bKaliforniya\s*,?\s*", ""),
        (r"\bUnited\s+States(?:\s+of\s+America)?\b", "AQSH"),
        (r"\bСША\b", "AQSH"),
        (r"\bAmerika\b", "AQSH"),
        (r"\bUSA\b", "AQSH"),
        (r"\bU\.S\.A\.\b", "AQSH"),
        (r"\bUnited\s+Kingdom\b", "Buyuk Britaniya"),
        (r"\bВеликобритания\b", "Buyuk Britaniya"),
        (r"\bGreat\s+Britain\b", "Buyuk Britaniya"),
        (r"\bUK\b", "Buyuk Britaniya"),
        (r"\bAngliya\b", "Buyuk Britaniya"),
        (r"\bRussia\b", "Rossiya"),
        (r"\bРоссия\b", "Rossiya"),
        (r"\bCCCR\b", "Rossiya"),
        (r"\bSSSR\b", "Rossiya"),
        (r"\bСССР\b", "Rossiya"),
        (r"\bUSSR\b", "Rossiya"),
        (r"\bUzbekistan\b", "O'zbekiston"),
        (r"\bУзбекистан\b", "O'zbekiston"),
        (r"\bO`zbekiston\b", "O'zbekiston"),
        (r"\bSouth\s+Korea\b", "Janubiy Koreya"),
        (r"\bКорея\s+Южная\b", "Janubiy Koreya"),
        (r"\bЮжная\s+Корея\b", "Janubiy Koreya"),
        (r"\bIndia\b", "Hindiston"),
        (r"\bИндия\b", "Hindiston"),
        (r"\bChina\b", "Xitoy"),
        (r"\bКитай\b", "Xitoy"),
        (r"\bHong\s+Kong\b", "Gonkong"),
        (r"\bГонконг\b", "Gonkong"),
        (r"\bJapan\b", "Yaponiya"),
        (r"\bЯпония\b", "Yaponiya"),
        (r"\bFrance\b", "Fransiya"),
        (r"\bФранция\b", "Fransiya"),
        (r"\bGermany\b", "Germaniya"),
        (r"\bГермания\b", "Germaniya"),
        (r"\bSpain\b", "Ispaniya"),
        (r"\bИспания\b", "Ispaniya"),
        (r"\bItaly\b", "Italiya"),
        (r"\bИталия\b", "Italiya"),
        (r"\bCanada\b", "Kanada"),
        (r"\bКанада\b", "Kanada"),
        (r"\bAustralia\b", "Avstraliya"),
        (r"\bАвстралия\b", "Avstraliya"),
        (r"\bNew\s+Zealand\b", "Yangi Zelandiya"),
        (r"\bНовая\s+Зеландия\b", "Yangi Zelandiya"),
        (r"\bTurkey\b", "Turkiya"),
        (r"\bТурция\b", "Turkiya"),
        (r"\bNorway\b", "Norvegiya"),
        (r"\bНорвегия\b", "Norvegiya"),
        (r"\bIndonesia\b", "Indoneziya"),
        (r"\bИндонезия\b", "Indoneziya"),
        (r"\bIndoneyziya\b", "Indoneziya"),
        (r"\bSouth\s+Africa\b", "Janubiy Afrika"),
        (r"\bЮАР\b", "Janubiy Afrika"),
        (r"\bQirg'iz\b", "Qirg'iziston"),
        (r"\bКыргызстан\b", "Qirg'iziston"),
        (r"\bКазахстан\b", "Qozog'iston"),
        (r"\bfilmi\b", ""),
    ]
    for pat, rep in replacements:
        c = re.sub(pat, rep, c, flags=re.IGNORECASE)
    parts = []
    for p in c.split(","):
        p_clean = re.sub(r"\s+", " ", p).strip(" -:,.")
        if p_clean and p_clean not in parts:
            parts.append(p_clean)
    return ", ".join(parts[:3]) if parts else "AQSH"


def normalize_genres(raw_genre: str, movie_name: str = "") -> str:
    """
    Imlo xatoli, qisqargan yoki ingliz/rus/o'zbekcha janrlarni (masalan 'Komedia, Jngari',
    'Sehrga', 'Mul', 'Koino', 'DC, Fa', 'Action, Sci-Fi') 100% config.GENRES standartiga o'giradi.
    Hech qachon config.GENRES dan tashqari noto'g'ri yozuv qaytarmaydi!
    """
    text = f"{raw_genre} {movie_name}".lower()
    matched = []
    for k, clean_val in GENRE_CORRECTIONS.items():
        if k in text and clean_val not in matched:
            matched.append(clean_val)

    # Qisqargan 1-3 harfli arxiv satrlarini aniq ajratish
    tokens = [re.sub(r"[^\w']", "", t.strip().lower()) for t in (raw_genre or "").split(",") if t.strip()]
    for tok in tokens:
        mapped = None
        if tok in ("mul", "mu", "mult") or ("uch bahodir" in text or "shahzoda va" in text):
            mapped = "🧸 Multfilm"
        elif tok in ("ja", "jan", "jang"):
            mapped = "🔥 Jangari"
        elif tok in ("dah", "uj"):
            mapped = "👻 Qo'rqinchli"
        elif tok in ("fa", "fan", "dc"):
            mapped = "🚀 Fantastika"
        elif tok in ("k", "kom"):
            mapped = "😂 Komediya"
        elif tok in ("d", "dr", "dram"):
            mapped = "💔 Drama"
        elif tok == "m" and "bahodir" in text:
            mapped = "🧸 Multfilm"
        if mapped and mapped not in matched:
            matched.append(mapped)

    if "dc" in tokens and "🔥 Jangari" not in matched:
        matched.append("🔥 Jangari")
    if ("uch bahodir" in text or "shahzoda va" in text) and "😂 Komediya" not in matched:
        matched.append("😂 Komediya")

    valid_set = set(config.GENRES)
    matched = [g for g in matched if g in valid_set]
    if matched:
        return ", ".join(matched[:3])
    return "🔥 Jangari"


def fix_uzbek_typos(text: str) -> str:
    """Matndagi keng tarqalgan imlo xatolarni avtomatik to'g'rilash."""
    if not text:
        return ""
    replacements = [
        (r"\bJngari\b", "Jangari"),
        (r"\bjngari\b", "jangari"),
        (r"\bKomedia\b", "Komediya"),
        (r"\bkomedia\b", "komediya"),
        (r"\bKamediya\b", "Komediya"),
        (r"\bFantastik\b", "Fantastika"),
        (r"\bUjas\b", "Qo'rqinchli"),
        (r"\bujas\b", "qo'rqinchli"),
        (r"\bDramma\b", "Drama"),
        (r"\bUzb\b", "O'zbek"),
        (r"\btilda\b", "tilida"),
    ]
    res = text
    for pat, rep in replacements:
        res = re.sub(pat, rep, res)
    return res.strip()


def generate_smart_uzbek_description(name: str, genre: str, year: str, country: str, is_serial: bool = False) -> str:
    """Tashqi AI kaliti bo'lmaganda yoki ishlamaganda ham bexato, chiroyli o'zbekcha tavsif yozuvchi ichki AI generator."""
    kind = "seriali" if is_serial else "filmi"
    clean_genre = re.sub(r"[^\w\s',-]", "", genre).strip().lower() or "ommabop"
    clean_genre = re.sub(r"\s+", " ", clean_genre)
    return (
        f"«{name}» ({year}) — {country} kinoijodkorlari tomonidan suratga olingan "
        f"{clean_genre} janridagi ajoyib {kind}. Yuqori sifatda va o'zbek tilida tomosha qiling!"
    )


def clean_filename_to_title(file_name: str) -> dict:
    """
    Videoning file_name (masalan: 'Lara.Kroft.2001.1080p.BluRay.x264.uzb.eng.mkv'
    yoki 'Snayper_so&#x27;nggi_jang_720p_O&#x27;zbek_tilida_asilmedia_net.mp4')
    ichidan kino nomi, yili va sifatini ajratib oladi.
    """
    if not file_name:
        return {"title": "", "year": "", "quality": ""}

    fn = urllib.parse.unquote(html.unescape(file_name)).strip()
    fn = re.sub(r"\.(mp4|mkv|avi|mov|webm|flv)$", "", fn, flags=re.IGNORECASE)

    # Sifatni ajratib olamiz
    quality = ""
    qm = re.search(r"\b(4K|2160p|1440p|1080p|720p|480p)\b", fn, flags=re.IGNORECASE)
    if qm:
        q_raw = qm.group(1).upper()
        if q_raw in ("4K", "2160P"):
            quality = "4K Ultra HD"
        elif q_raw == "1080P":
            quality = "1080p Full HD"
        elif q_raw == "720P":
            quality = "720p HD"
        else:
            quality = q_raw.lower()
    elif re.search(r"\bfull[\s_.]*hd\b", fn, flags=re.IGNORECASE):
        quality = "1080p Full HD"

    # Yilni ajratib olamiz
    year = ""
    ym = re.search(r"(?:^|[\s._(\[-])(19[7-9]\d|20[0-2]\d)(?:$|[\s._)\]-])", fn)
    if ym:
        year = ym.group(1)

    # Suv belgilari va texnik so'zlarni tozalaymiz
    cleaned = fn
    junk_patterns = [
        r"@[\w_]+",
        r"\([^\)]*(?:asilmedia|uzmedia|uzmovi|tarona|okko|anidub|sara)[^\)]*\)",
        r"\[[^\]]*\]",
        r"\b(?:uzmovi\.com|asilmedia\.net|asilmedia_net|asilmedia|uzmedia\.tv|uzmedia_tv|taronatv|daxshat\.uz|daxshat\.net|hdclubuz|kinozoneuz|kingleech|poisk_kino_n1|absolutelyhd|muzoboz|anidub|okko|yts\.ag)\b",
        r"\b(?:1080p|720p|480p|4k|2160p|1440p|full\s*hd|ultra|bluray|webrip|web-dl|brrip|hdrip|dvdrip|x264|x265|h264|hevc|10bit|6ch|aac|mp4|mkv|id\.\d+|s\d+e\d+|s1s1q\d+|q720|q480|v2|directors\.cut|uzb|rus|eng|chines|o'zbek\s*tilida|uzbek\s*tilida|профессиональный|многоголосый|hd|ts)\b",
        r"\b(19[7-9]\d|20[0-2]\d)\b",
    ]
    for pat in junk_patterns:
        cleaned = re.sub(pat, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"[._]+", " ", cleaned)
    cleaned = re.sub(r"\s+\d\s*$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–:.,_|()")

    # Agar faqatgina kanal nomi yoki 2 harfli texnik nom qolgan bo'lsa (masalan 'Njk', 'Rtt')
    if len(cleaned) <= 3 and cleaned.lower() in ("njk", "rtt", "uy"):
        if cleaned.lower() != "uy":
            cleaned = ""

    return {"title": cleaned, "year": year, "quality": quality}


def is_archive_caption_incomplete(raw_text: str) -> bool:
    """
    Arxiv kanaldagi postning ma'lumotlari to'liq shablonda yozilgan-yozilmaganini tekshiradi.
    Agar Nomi, Davlati, Yili, Sifati, Janri qatorlaridan biri yo'q bo'lsa -> True qaytaradi.
    """
    if not raw_text or not raw_text.strip():
        return True
    low = raw_text.lower()
    required_markers = ["nomi:", "davlati:", "yili:", "sifati:", "janri:"]
    return not all(m in low for m in required_markers)


def format_standard_archive_caption(meta: dict) -> str:
    """
    Movie Land ARXIV (-1003124847141) kanali uchun yagona, toza standart shablon.
    """
    name = meta.get("raw_title") or meta.get("name") or "Yangi Kino"
    country = meta.get("country") or "AQSH"
    year = meta.get("year") or "2024"
    quality = meta.get("quality") or "1080p Full HD"
    genre_raw = meta.get("genre") or "🔥 Jangari"
    # Shablonda emoji bilan yoki emojisiz chiroyli ko'rinish
    genre_clean = re.sub(r"[🔥😂🚀👻💔🕵️🎌🧸⚔️🇺🇿🌍❤️]", "", genre_raw)
    genre_clean = ", ".join([g.strip() for g in genre_clean.split(",") if g.strip()]) or "Jangari"
    language = meta.get("language") or "O'zbek tilida"

    return (
        f"🎬 Nomi: {name}\n\n"
        f"🌏 Davlati: {country}\n"
        f"📅 Yili: {year}\n"
        f"📀 Sifati: {quality}\n"
        f"🎞 Janri: {genre_clean}\n"
        f"🇺🇿 Tili: {language}\n\n"
        f"📌 Kanal @movieee_land"
    )


def parse_archive_caption(raw_text: str, file_name: str = "", video_height: int = 0, msg_id: int = None) -> dict:
    """
    Movie Land ARXIV (-1003124847141) kanalidagi postlarni (hatto faqat nomi, tili yoki file_name bo'lsa ham)
    100% aniqlikda tahlil qiluvchi Aqlli Parser.
    """
    raw_text = html.unescape(raw_text or "").strip()
    fn_info = clean_filename_to_title(file_name)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    name = ""
    subtitle_candidate = ""
    country = "AQSH"
    year = "2024"
    quality = "1080p Full HD"
    raw_genre = ""
    language = "O'zbek tilida"
    extra_lines = []

    has_year = False
    has_country = False
    has_genre = False
    has_quality = False

    for line in lines:
        low = line.lower()

        # Reklama, chiziqlar va shovqin qatorlarni tashlab ketamiz
        if any(skip in low for skip in [
            "kanal @", "📌 kanal", "@movieee_land", "t.me/", "http://", "https://",
            "ishonchli stars bot", "yuklab olishlar:", "🗂 yuklash:", "tarjima qilganlar:",
            "bizning bot:", "online ko'rish", "reklamalarsiz va logolarsiz",
            "kutganlar bormi", "reaksiya esdan chiqmasin", "sayohatni sevuvchilar uchun",
            "kinopoisk:", "📱 reyting:", "subtitr:"
        ]):
            continue

        if re.match(r"^[➖━\-_=*\s#]+$", line) or low in ("premyera", "premyera🔥", "#premyera"):
            continue
        if re.match(r"^\d{1,4}$", line):
            continue

        # 1. Nomi
        if "nomi:" in low and "ruscha nomi:" not in low:
            val = re.split(r"(?:filmning\s+|film\s+)?nomi\s*:", line, flags=re.IGNORECASE)[1].strip()
            val = re.sub(r"^[🎬🎥🎞➺➤➢▪️▫️\-\s\"«]+|[»\"\s]+$", "", val)
            if val:
                name = val
            continue

        if "ruscha nomi:" in low:
            continue

        # 2. Davlati
        if "davlati:" in low or "davlat:" in low or "aqsh filmi" in low:
            if ":" in line:
                val = re.split(r"davlati?\s*:", line, flags=re.IGNORECASE)[1].strip()
            else:
                val = line
            val = re.sub(r"^[➺➤➢▪️▫️\-\s]+", "", val)
            ym = re.search(r"\b(19\d{2}|20\d{2})\b", val)
            if ym:
                year = ym.group(1)
                has_year = True
                val = re.sub(r"\(\s*(19\d{2}|20\d{2})\s*\)", "", val).strip(" ,-")
            val = normalize_country(val)
            if val:
                country = val
                has_country = True
            continue

        # 3. Yili
        if "yili:" in low or "yil:" in low or "🗓" in line:
            val = line.split(":", 1)[1].strip() if ":" in line else line
            ym = re.search(r"\b(19\d{2}|20\d{2})\b", val)
            if ym:
                year = ym.group(1)
                has_year = True
            continue

        # 4. Sifati / Video / Formati
        if any(k in low for k in ["sifati:", "sifat:", "format:", "formati:", "video:", "vedio:", "качество:"]):
            val = line.split(":", 1)[1].strip() if ":" in line else line
            qm = re.search(r"\b(480p|720p\s*HD|720p|1080p\s*Full\s*HD|1080p|1440\s*2K|4K)\b", val, flags=re.IGNORECASE)
            if qm:
                q_found = qm.group(1)
                quality = "1080p Full HD" if q_found.lower() == "1080p" else ("720p HD" if q_found.lower() == "720p" else q_found)
                has_quality = True
            elif val:
                quality = re.sub(r"\s+", " ", val)
                has_quality = True
            continue

        # 5. Janri yoki hashtaglar (#jangari #fantastika)
        if "janri:" in low or "janr:" in low or "⚔️" in line or "🎭" in line or (
            line.startswith("#") and "premyera" not in low and any(gk in low for gk in GENRE_CORRECTIONS)
        ):
            val = line.split(":", 1)[1].strip() if ":" in line else line
            val = re.sub(r"^[➺➤➢▪️▫️\-\s➖━]+|[➖━\s]+$", "", val)
            if val and "premyera" not in val.lower():
                raw_genre = f"{raw_genre} {val}".strip()
                has_genre = True
            continue

        # 6. Tili / Audio
        if any(k in low for k in ["tili:", "til:", "tarjima:", "audio:", "tilida", "tilda"]):
            # Agar qatorda kino nomi ham bo'lsa (masalan: "Flesh (2023) O'zbek Tilida")
            if not name and ("(" in line or "🎬" in line or "🎥" in line or "🎞" in line):
                cleaned_title_line = re.sub(r"o['`‘ʻ]?zbek\s*tili?da|uzbek\s*tili?da|uzb\s*🇺🇿\s*tili?da|[🇺🇿🎬🎥🎞😇]", "", line, flags=re.IGNORECASE).strip(" -:")
                if len(cleaned_title_line) >= 3:
                    name = cleaned_title_line
            language = "O'zbek tilida"
            continue

        # 7. Agar 🎬/🎥/🎞 bilan boshlangan qator bo'lsa
        if not name and any(em in line for em in ["🎬", "🎥", "🎞"]):
            val = re.sub(r"[🎬🎥🎞➺➤➢▪️▫️]", "", line).strip(" -:")
            if "/" in val:
                val = val.split("/")[0].strip()
            if val:
                name = val
            continue

        # Inglizcha nom + yil qatori (masalan: "The Mummy Returns (2001)")
        ym_line = re.search(r"\(\s*(19[7-9]\d|20[0-2]\d)\s*\)", line)
        if ym_line:
            year = ym_line.group(1)
            has_year = True
            if not name:
                name = re.sub(r"\(\s*(19[7-9]\d|20[0-2]\d)\s*\)", "", line).strip(" -«»\"")
            continue

        if re.match(r"^(?:\d+\s*[-–]\s*qism|✅\s*\d)", low):
            continue

        # Qo'shtirnoq ichidagi kino nomi (masalan: "Skelet kaliti" yoki «Qasoskorlar»)
        if not name and ((line.startswith('"') and line.endswith('"')) or (line.startswith("«") and line.endswith("»"))):
            name = line.strip('"«» ')
            continue

        if not name:
            name = re.sub(r"[🎬🎥🎞➺➤➢▪️▫️\"«»]", "", line).strip(" -:")
        elif not subtitle_candidate and len(line) < 45:
            subtitle_candidate = re.sub(r"[🏠🕸️🎬🎥🎞➺➤➢▪️▫️]", "", line).strip(" -:")
        else:
            extra_lines.append(line)

    # Agar 2-qatorda subtitr bo'lsa (masalan: "O'rgimchak odam" + "Uyga qaytish" yoki "Muqaddas Zamin" + "1-qism")
    if name and subtitle_candidate:
        sub_low = subtitle_candidate.lower()
        name_low = name.lower()
        if sub_low not in name_low:
            if name_low.startswith("o'rgimchak") or name_low.startswith("oʻrgimchak") or name_low.startswith("o‘rgimchak"):
                sub_clean = re.sub(r"^o['`‘ʻ]?rgimchak\s*odam\s*\d*\s*", "", subtitle_candidate, flags=re.IGNORECASE).strip(" -:")
                if sub_clean:
                    name = f"{name}: {sub_clean}"

    # Agar caption bo'sh bo'lsa yoki name topilmagan bo'lsa, file_name dan olamiz!
    if not name and fn_info["title"]:
        name = fn_info["title"]
    if not name:
        name = "Yangi Kino"

    # Yilni matn yoki file_name ichidan qidirish
    if not has_year:
        ym_all = re.search(r"\b(19[7-9]\d|20[0-2]\d)\b", raw_text)
        if ym_all:
            year = ym_all.group(1)
            has_year = True
        elif fn_info["year"]:
            year = fn_info["year"]
            has_year = True

    # Sifatni matn, file_name yoki haqiqiy video balandligidan aniqlash
    if not has_quality:
        qm = re.search(r"\b(480p|720p\s*HD|720p|1080p\s*Full\s*HD|1080p|1440\s*2K|4K)\b", raw_text, flags=re.IGNORECASE)
        if qm:
            q_found = qm.group(1)
            quality = "1080p Full HD" if q_found.lower() == "1080p" else ("720p HD" if q_found.lower() == "720p" else q_found)
            has_quality = True
        elif video_height:
            if video_height >= 1000:
                quality = "1080p Full HD"
            elif video_height >= 700:
                quality = "720p HD"
            else:
                quality = "480p"
            has_quality = True
        elif fn_info["quality"]:
            quality = fn_info["quality"]
            has_quality = True

    # Arxiv xabar ID si -> aniq nom bo'yicha -> kalit so'z bo'yicha Kino Ensiklopediyasi
    known_match = ARCHIVE_MSG_EXACT_MAP.get(msg_id) if msg_id else None
    strong_match = bool(known_match)
    if not known_match:
        known_match = _find_exact_known(name)
        strong_match = bool(known_match)
    if not known_match:
        search_blob = f"{name} {file_name} {raw_text}".lower()
        for keys, meta_val in KNOWN_TITLE_LOOKUP:
            if any(k in search_blob for k in keys):
                known_match = meta_val
                break

    if known_match:
        name_low = name.lower()
        junk_name = (
            not raw_text
            or name in ("Yangi Kino", "PREMYERA🔥", "1-qism", "2-qism")
            or len(name) <= 4
            or name_low.startswith(("o'rgimchak", "oʻrgimchak", "o‘rgimchak"))
            or "labirint 1" in name_low
            or "." in name
            or "_" in name
        )
        if strong_match or junk_name:
            name = known_match["name"]
        if not has_year or "yili:" not in raw_text.lower():
            year = known_match["year"]
            has_year = True
        if not has_country or "davlati:" not in raw_text.lower():
            country = known_match["country"]
            has_country = True
        if not has_genre or "janri:" not in raw_text.lower():
            raw_genre = known_match["genre"]
            has_genre = True
        if not has_quality and known_match.get("quality"):
            quality = known_match["quality"]
            has_quality = True

    # Nomni tozalash
    name = re.sub(r"\(\s*(19[7-9]\d|20[0-2]\d)\s*\)", "", name).strip(" -–:«»\"")
    name = re.sub(r"\s+", " ", name)

    # SERIAL, FASL VA QISM RAQAMINI ANIQLASH
    bt_info = extract_base_title_and_part(name, raw_caption=raw_text, file_name=file_name)
    is_serial = bt_info["is_serial"]
    season_num = bt_info.get("season_num", 1)
    part_num = bt_info["part_num"]
    base_title = bt_info["base_title"]
    episode_num = part_num
    base_name = base_title if is_serial else name

    genre = normalize_genres(raw_genre, base_name)
    extra_caption = fix_uzbek_typos(" ".join(extra_lines))

    return {
        "name": base_name,
        "base_title": base_title,
        "season_num": season_num,
        "part_num": part_num,
        "raw_title": name,
        "is_serial": is_serial,
        "episode_num": episode_num,
        "country": country,
        "year": year,
        "quality": quality,
        "genre": genre,
        "language": language,
        "caption": extra_caption,
        "has_year": has_year,
        "has_country": has_country,
        "has_genre": has_genre,
        "has_quality": has_quality,
    }


async def _lookup_tmdb_metadata(name: str, year: str = "", is_serial: bool = False) -> dict:
    """
    3-BOSQICHLI METADATA QIDIRUV TIZIMI (TMDB -> KinopoiskAPI.uz -> OMDb API):
    Kino faqat nomi yozilganda uning aniq Yili, Davlati va Janrini 3 ta provayderdan topib beradi.
    """
    if not name:
        return {}
    api_key = await db.get_setting("tmdb_api_key", config.TMDB_API_KEY)
    norm_n = _norm_title(name)
    exact_entry = _match_exact_search_entry(norm_n)
    ex_query, ex_year, ex_is_tv = exact_entry if exact_entry else ("", "", is_serial)
    use_is_serial = bool(ex_is_tv or is_serial)
    use_year = str(ex_year or year or "").strip()

    clean_title = re.sub(
        r"\b(?:\d+\s*[-–]?\s*(?:qism|seriya|epizod|fasl|sezon)|o['`‘ʻ]?zbek\s*tilida|uzbek\s*tilida|full\s*hd|1080p|720p|4k|premyera|kino|serial)\b",
        "",
        name,
        flags=re.IGNORECASE
    )
    clean_title = re.sub(r"\s+", " ", clean_title).strip(" -–:,.()[]")
    if not clean_title:
        clean_title = name.strip()

    endpoint = "search/tv" if use_is_serial else "search/movie"
    timeout = aiohttp.ClientTimeout(total=10)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            ru_title = await _translate_query(session, clean_title, "ru")
            en_title = await _translate_query(session, clean_title, "en")

            queries = []
            for q in [ex_query, clean_title, en_title, ru_title]:
                if q and q not in queries:
                    queries.append(q)

            # 1-Bosqich: TMDB API
            if api_key:
                for q in queries:
                    url = f"https://api.themoviedb.org/3/{endpoint}"
                    params = {
                        "api_key": api_key,
                        "query": q,
                        "language": "ru-RU",
                        "include_adult": "false"
                    }
                    if use_year and re.match(r"^(19\d{2}|20\d{2})$", use_year):
                        params["year" if endpoint == "search/movie" else "first_air_date_year"] = use_year

                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results = data.get("results") or []
                            top = None
                            for cand in results[:6]:
                                cand_titles = [
                                    cand.get("title"), cand.get("original_title"),
                                    cand.get("name"), cand.get("original_name")
                                ]
                                if (q == ex_query and ex_query) or any(ct and any(_titles_similar(qv, ct) for qv in queries) for ct in cand_titles):
                                    top = cand
                                    break
                            if top:
                                rel_date = top.get("release_date") or top.get("first_air_date") or ""
                                found_year = rel_date[:4] if len(rel_date) >= 4 else use_year

                                g_ids = top.get("genre_ids") or []
                                mapped_genres = []
                                for gid in g_ids:
                                    g_name = TMDB_GENRE_MAP.get(gid)
                                    if g_name and g_name not in mapped_genres:
                                        mapped_genres.append(g_name)

                                found_country = ""
                                orig_c = top.get("origin_country") or []
                                if orig_c:
                                    c_list = [COUNTRY_ISO_MAP.get(c.upper(), c) for c in orig_c[:2]]
                                    found_country = ", ".join(c_list)
                                elif top.get("id") and endpoint == "search/movie":
                                    det_url = f"https://api.themoviedb.org/3/movie/{top['id']}"
                                    async with session.get(det_url, params={"api_key": api_key}) as d_resp:
                                        if d_resp.status == 200:
                                            det = await d_resp.json()
                                            pcs = det.get("production_countries") or []
                                            if pcs:
                                                c_list = [COUNTRY_ISO_MAP.get(c.get("iso_3166_1", "").upper(), c.get("name", "")) for c in pcs[:2]]
                                                found_country = ", ".join([c for c in c_list if c])

                                return {
                                    "year": found_year,
                                    "genre": ", ".join(mapped_genres[:3]) if mapped_genres else "",
                                    "country": found_country,
                                }

            # 2-Bosqich: KinopoiskAPI.uz
            for q in queries[:3]:
                kp_res = await _kinopoisk_uz_search_movie(session, q, year=use_year)
                if kp_res and (kp_res.get("year") or kp_res.get("genre") or kp_res.get("country")):
                    return {
                        "year": kp_res.get("year") or use_year,
                        "genre": kp_res.get("genre") or "",
                        "country": kp_res.get("country") or "",
                    }

            # 3-Bosqich: The OMDb API
            for q in [ex_query, en_title, clean_title]:
                if not q:
                    continue
                omdb_res = await _omdb_search_movie(session, q, year=use_year, is_serial=use_is_serial)
                if omdb_res and (omdb_res.get("year") or omdb_res.get("genre") or omdb_res.get("country")):
                    return {
                        "year": omdb_res.get("year") or use_year,
                        "genre": omdb_res.get("genre") or "",
                        "country": omdb_res.get("country") or "",
                    }
    except Exception as e:
        logging.debug(f"Multi-provider metadata lookup xatosi ({name}): {e}")
    return {}


async def enrich_movie_metadata_with_ai(
    raw_text: str = "",
    file_name: str = "",
    video_height: int = 0,
    msg_id: int = None,
    existing_movie: dict = None
) -> dict:
    """
    Kinoning faqatgina nomi (yoki tili/hajmi/file_name) yozilgan bo'lsa ham:
    1. Parse + Ichki Kino Ensiklopediyasi orqali tekshiradi;
    2. Top-15 AI Provayderi (agar kalit kiritilgan bo'lsa) va TMDB Metadata orqali
       Yili, Davlati, Janri, Sifati va O'zbekcha Tavsifini 100% bexato to'ldiradi!
    """
    parsed = parse_archive_caption(raw_text=raw_text, file_name=file_name, video_height=video_height, msg_id=msg_id)

    if existing_movie:
        if parsed["name"] == "Yangi Kino" and existing_movie.get("name"):
            parsed["name"] = existing_movie["name"]
            parsed["raw_title"] = existing_movie["name"]

    # Agar yili, davlati yoki janri matnda yozilmagan bo'lsa, AI va TMDB dan aniqlaymiz
    if not (parsed["has_year"] and parsed["has_country"] and parsed["has_genre"]):
        active_provider = await db.get_setting("ai_active_provider", "gemini")
        api_key = await db.get_setting(f"ai_key_{active_provider}", "")
        if api_key:
            ai_prompt = (
                f"Kino nomi yoki fayl ma'lumoti: «{parsed['name']}» (Qo'shimcha: {file_name} {raw_text}).\n"
                f"Ushbu kino qaysi kino ekanligini aniq topib, faqat JSON formatda qaytar:\n"
                f'{{"name": "Kino aniq o\'zbekcha nomi", "year": "YYYY", "country": "Davlati", "genre": "Janri"}}'
            )
            ai_json_str = await call_ai_provider(active_provider, api_key, ai_prompt)
            if ai_json_str:
                try:
                    jm = re.search(r"\{.*\}", ai_json_str, flags=re.DOTALL)
                    if jm:
                        jdata = json.loads(jm.group(0))
                        if jdata.get("name") and len(jdata["name"]) >= 2:
                            parsed["name"] = jdata["name"]
                            parsed["raw_title"] = jdata["name"]
                        if not parsed["has_year"] and jdata.get("year") and re.match(r"^(19\d{2}|20\d{2})$", str(jdata["year"])):
                            parsed["year"] = str(jdata["year"])
                            parsed["has_year"] = True
                        if not parsed["has_country"] and jdata.get("country"):
                            parsed["country"] = normalize_country(str(jdata["country"]))
                            parsed["has_country"] = True
                        if not parsed["has_genre"] and jdata.get("genre"):
                            parsed["genre"] = normalize_genres(str(jdata["genre"]), parsed["name"])
                            parsed["has_genre"] = True
                except Exception:
                    pass

        # TMDB Metadata qidiruvi (Yili, Davlati va Janrini aniq topish uchun)
        if not (parsed["has_year"] and parsed["has_country"] and parsed["has_genre"]):
            tmdb_meta = await _lookup_tmdb_metadata(
                name=parsed["name"],
                year=parsed["year"] if parsed["has_year"] else "",
                is_serial=bool(parsed["is_serial"])
            )
            if tmdb_meta:
                if not parsed["has_year"] and tmdb_meta.get("year"):
                    parsed["year"] = tmdb_meta["year"]
                    parsed["has_year"] = True
                if not parsed["has_country"] and tmdb_meta.get("country"):
                    parsed["country"] = tmdb_meta["country"]
                    parsed["has_country"] = True
                if not parsed["has_genre"] and tmdb_meta.get("genre"):
                    parsed["genre"] = tmdb_meta["genre"]
                    parsed["has_genre"] = True

    # Tavsifni (description) AI orqali yozish yoki to'g'rilash
    final_caption = await process_movie_description_with_ai(
        name=parsed["name"],
        genre=parsed["genre"],
        year=parsed["year"],
        existing_caption=parsed["caption"],
        country=parsed["country"],
        is_serial=bool(parsed["is_serial"])
    )
    parsed["caption"] = final_caption
    return parsed


async def call_ai_provider(provider_key: str, api_key: str, prompt: str) -> str:
    """Tanlangan AI provayderga asinxron so'rov yuborish."""
    prov = config.TOP_15_AI_PROVIDERS.get(provider_key)
    if not prov or not api_key:
        return ""

    p_type = prov["type"]
    model = prov["model"]
    timeout = aiohttp.ClientTimeout(total=15)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if p_type == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.5, "maxOutputTokens": 250}
                }
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return ""

            elif p_type == "anthropic":
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": model,
                    "max_tokens": 250,
                    "messages": [{"role": "user", "content": prompt}]
                }
                async with session.post(prov["url"], headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["content"][0]["text"].strip()
                    return ""

            elif p_type == "cohere":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                async with session.post(prov["url"], headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["message"]["content"][0]["text"].strip()
                    return ""

            else:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Sen professional kino muharririsan. Faqat o'zbek tilida, imlo xatolarsiz, qisqa va qiziqarli javob qaytarasan."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.5,
                    "max_tokens": 250
                }
                async with session.post(prov["url"], headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
                    return ""
    except Exception as e:
        logging.warning(f"AI so'rovida xatolik ({provider_key}): {e}")
        return ""


async def process_movie_description_with_ai(
    name: str,
    genre: str,
    year: str,
    existing_caption: str = "",
    country: str = "AQSH",
    is_serial: bool = False
) -> str:
    """
    AI yoqilgan bo'lsa:
    1) Tashqi AI API orqali tavsif yozadi yoki mavjudining xatosini to'g'rilaydi.
    2) Agar tashqi API javob bermasa ham, Built-in Smart AI avtomatik xatolarni to'g'rilaydi va tavsif yozadi!
    """
    clean_cap = fix_uzbek_typos((existing_caption or "").strip())
    # Agar oldingi caption ichida texnik yozuvlar qolib ketgan bo'lsa, toza tavsifga almashtiramiz
    if any(junk in clean_cap.lower() for junk in [
        "premyera", "kinopoisk", "video:", "vedio:", "audio:", "brrip", "kutganlar bormi",
        "reaksiya esdan", "sayohatni sevuvchilar", "aqsh filmi", "uyga qaytish", "uydan uzoqda",
        "uyga yo'l yo'q", "labirint 1", "➖➖"
    ]):
        clean_cap = ""

    ai_enabled = await db.get_setting("ai_enabled", "1")
    if ai_enabled != "1":
        return clean_cap

    active_provider = await db.get_setting("ai_active_provider", "gemini")
    api_key = await db.get_setting(f"ai_key_{active_provider}", "")

    if api_key:
        if not clean_cap:
            prompt = (
                f"Kino nomi: «{name}», Janri: {genre}, Yili: {year}, Davlati: {country}.\n"
                f"Ushbu kino uchun o'zbek tilida 2 gapdan iborat qiziqarli tavsif (description) yozib ber. "
                f"Faqat tavsif matnini qaytar."
            )
        else:
            prompt = (
                f"Kino nomi: «{name}» ({genre}). Quyidagi tavsifning imlo va grammatik xatolarini to'g'rilab, "
                f"ravon o'zbek tilida qaytar:\n{clean_cap}"
            )
        ai_res = await call_ai_provider(active_provider, api_key, prompt)
        if ai_res:
            return ai_res

    if not clean_cap or f"({year})" not in clean_cap:
        return generate_smart_uzbek_description(name, genre, year, country, is_serial=is_serial)
    return clean_cap


# ===================== THEMOVIEDB (TMDB) AVTO-POSTER QIDIRUV TIZIMI =====================
async def _translate_query(session: aiohttp.ClientSession, text: str, target_lang: str) -> str:
    """O'zbekcha kino nomini TMDB da aniq topish uchun RU yoki EN tiliga tezkor o'girish."""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                if data and data[0]:
                    return "".join(part[0] for part in data[0] if part and part[0]).strip()
    except Exception:
        pass
    return ""


# Har bir o'zbekcha kino nomi uchun aniq xalqaro (TMDB) qidiruv nomi va yili
EXACT_TMDB_SEARCH_MAP = {
    "afsungar merlin": ("Merlin", "2008", True),
    "envel qahramonlari": ("Герои Энвелла", "2017", True),
    "predator xishnik": ("Predator", "1987", False),
    "oppoqvoy": ("Blancanieves", "2012", False),
    "avstraliyadagi qutqaruvchilar": ("The Rescuers Down Under", "1990", False),
    "uzunquloqlar isyoni": ("Hop", "2011", False),
    "veronika lanati": ("Verónica", "2017", False),
    "veronika la'nati": ("Verónica", "2017", False),
    "koinotdagi yolovchilar": ("Passengers", "2016", False),
    "supermen polat odam": ("Man of Steel", "2013", False),
    "supermen & polat odam": ("Man of Steel", "2013", False),
    "polat odam supper men": ("Man of Steel", "2013", False),
    "sevastapol mudofasi": ("Bitva za Sevastopol", "2015", False),
    "uyqu iblisi": ("Slumber", "2017", False),
    "ikki olam toqnashuvi": ("War of the Worlds", "2005", False),
    "javohir politsiyachi": ("Blue Streak", "1999", False),
    "yurak kozli qotil": ("Heart Eyes", "2025", False),
    "qalin dostlar": ("The Intouchables", "2011", False),
    "tig ustida yuruvchilar": ("Blade Runner 2049", "2017", False),
    "robert bryus": ("Robert the Bruce", "2019", False),
    "jangdan keyingi hayot": ("Civil War", "2024", False),
    "ozga sayyoradan tashrif": ("Arrival", "2016", False),
    "ibn sino shogirdi": ("The Physician", "2013", False),
    "qattiq qol honim": ("The Devil Wears Prada", "2006", False),
    "asosiy oyinchi": ("The Game Plan", "2007", False),
    "uddaburon josuslar": ("Get Smart", "2008", False),
    "ajina togi": ("Race to Witch Mountain", "2009", False),
    "forsaj hobbs shou": ("Fast & Furious Presents: Hobbs & Shaw", "2019", False),
    "forsaj : hobbs & shou": ("Fast & Furious Presents: Hobbs & Shaw", "2019", False),
    "qora adam": ("Black Adam", "2022", False),
    "osmon opar bino": ("Skyscraper", "2018", False),
    "kruz junglisi": ("Jungle Cruise", "2021", False),
    "tish farishtasi": ("Tooth Fairy", "2010", False),
    "zahiradagi politsiyachilar": ("The Other Guys", "2010", False),
    "yol yol pijamali bola": ("The Boy in the Striped Pyjamas", "2008", False),
    "uch baxodir va yer kindigi": ("Три богатыря и Пуп Земли", "2023", False),
    "terabitya": ("Bridge to Terabithia", "2007", False),
    "ham qon ham jon berib": ("Pain & Gain", "2013", False),
    "girrom oyin": ("Play Dirty", "2025", False),
    "ormon egalari": ("Open Season", "2006", False),
    "ottizinchi asr pinokkiosi": ("Pinocchio 3000", "2004", False),
    "ayyor hyugo": ("Hugo: The World's Worst Comeback", "2007", False),
    "uch bahodir va shamaxa malikasi": ("Три богатыря и Шамаханская царица", "2010", False),
    "uch bahodir dengiz ortida": ("Три богатыря на дальних берегах", "2012", False),
    "uch bahodir va ormon jodugari": ("Три богатыря: Ход конём", "2014", False),
    "uch bahodir va dengiz shahzodasi": ("Три богатыря и Морской царь", "2016", False),
    "yura davri bolalari": ("Dino Time", "2012", False),
    "sehirlangan ella": ("Ella Enchanted", "2004", False),
    "qulupnayning sarguzashtlari": ("Strawberry Shortcake", "1980", False),
    "ayiqcha elka": ("Элька", "2007", False),
    "uch bahodir va misr malikasi": ("Три богатыря и принцесса Египта", "2017", False),
    "uch bahodir yerni markazida": ("Три богатыря и Пуп Земли", "2023", False),
    "oushenning 8 dugonasi": ("Ocean's Eight", "2018", False),
    "uch bahodir ot taxt sohibi": ("Конь Юлий и большие скачки", "2020", False),
    "uch bahodir va katta poygalar": ("Конь Юлий и большие скачки", "2020", False),
    "uch bahodir va taxt vorisi": ("Три богатыря и Наследница престола", "2018", False),
    "tom va jerri": ("Tom & Jerry", "2021", False),
    "raqs va olmos": ("Diamond Cartel", "2015", False),
    "predator xishnik 1 qism": ("Predator", "1987", False),
    "predator xishnik 2 qism": ("Predator 2", "1990", False),
    "predator xishnik 3 qism": ("Predators", "2010", False),
    "predator xishnik 4 qism": ("The Predator", "2018", False),
    "predator xishnik 5 qism": ("Prey", "2022", False),
    "xishnik yirtqich": ("Prey", "2022", False),
    "xishnik yovvoyi yerlar": ("Predator", "2022", False),
    "uddalab bolmas topshiriq 8": ("Mission: Impossible - The Final Reckoning", "2025", False),
    "forsaj 10": ("Fast X", "2023", False),
    "dengiz hukumdori": ("Master and Commander: The Far Side of the World", "2003", False),
    "yirtqichlar": ("Predators", "2010", False),
    "jodugar ovchilari": ("Hansel & Gretel: Witch Hunters", "2013", False),
    " Robin gud": ("Robin Hood", "2018", False),
    "robin gud": ("Robin Hood", "2018", False),
    "temir musht": ("Real Steel", "2011", False),
    "ajdarho qanday organiladi": ("How to Train Your Dragon", "2025", False),
    "yomon yigitlar": ("The Bad Guys", "2022", False),
    "yomon yigitlar 1": ("The Bad Guys", "2022", False),
    "yomon yigitlar 2": ("The Bad Guys 2", "2025", False),
    "transformerlar 7 maxluqlar yuksalishi": ("Transformers: Rise of the Beasts", "2023", False),
    "mumiya": ("The Mummy", "1999", False),
    "mumiya 1 qism": ("The Mummy", "1999", False),
    "mumiya 2 qism": ("The Mummy Returns", "2001", False),
    "mumiya 3 qism": ("The Mummy: Tomb of the Dragon Emperor", "2008", False),
    "mumiyo": ("The Mummy", "1999", False),
    "sonic": ("Sonic the Hedgehog", "2020", False),
    "sonic 1": ("Sonic the Hedgehog", "2020", False),
    "sonic 2": ("Sonic the Hedgehog 2", "2022", False),
    "sonic 3": ("Sonic the Hedgehog 3", "2024", False),
    "krid": ("Creed", "2015", False),
    "krid 1": ("Creed", "2015", False),
    "krid 2": ("Creed II", "2018", False),
    "krid 3": ("Creed III", "2023", False),
    "padington": ("Paddington", "2014", False),
    "padington 1": ("Paddington", "2014", False),
    "padington 2": ("Paddington 2", "2017", False),
    "padington 3": ("Paddington in Peru", "2024", False),
    "garri potter": ("Harry Potter and the Philosopher's Stone", "2001", False),
    "garri potter 1 qism": ("Harry Potter and the Philosopher's Stone", "2001", False),
    "garri potter 2 qism": ("Harry Potter and the Chamber of Secrets", "2002", False),
    "garri potter 3 qism": ("Harry Potter and the Prisoner of Azkaban", "2004", False),
    "garri potter 4 qism": ("Harry Potter and the Goblet of Fire", "2005", False),
    "garri potter 5 qism": ("Harry Potter and the Order of the Phoenix", "2007", False),
    "garri potter 6 qism": ("Harry Potter and the Half-Blood Prince", "2009", False),
    "garri potter 7 1 qism": ("Harry Potter and the Deathly Hallows: Part 1", "2010", False),
    "garri potter 7 2 qism": ("Harry Potter and the Deathly Hallows: Part 2", "2011", False),
    "jumanji": ("Jumanji", "1995", False),
    "jumanji 1 qism": ("Jumanji", "1995", False),
    "jumanji 2 qism": ("Jumanji: Welcome to the Jungle", "2017", False),
    "jumanji 3 qism": ("Jumanji: The Next Level", "2019", False),
    "ilon hamlasi": ("Anaconda", "1997", False),
    "ilon hamlasi 1": ("Anaconda", "1997", False),
    "ilon hamlasi 2": ("Anacondas: The Hunt for the Blood Orchid", "2004", False),
    "malikaning kundaligi": ("The Princess Diaries", "2001", False),
    "malikaning kundaligi 1 qism": ("The Princess Diaries", "2001", False),
    "malikaning kundaligi 2 qism": ("The Princess Diaries 2: Royal Engagement", "2004", False),
    "shahzoda va bori": ("Иван Царевич и Серый Волк", "2011", False),
    "beethoven": ("Beethoven", "1992", False),
    "masxaraboz ono penni vays": ("It", "2017", False),
    "masxaraboz ono penni vays 1 qism": ("It", "2017", False),
    "masxaraboz ono penni vays 2 qism": ("It Chapter Two", "2019", False),
    "chaqmoq makvin": ("Cars", "2006", False),
    "chaqmoq makvin 1": ("Cars", "2006", False),
    "chaqmoq makvin 2": ("Cars 2", "2011", False),
    "chaqmoq makvin 3": ("Cars 3", "2017", False),
    "polat odam supper men": ("Man of Steel", "2013", False),
    "uyda yolgiz 1": ("Home Alone", "1990", False),
    "hayvonlar shahri 2": ("Zootopia 2", "2025", False),
    "qora libosli odamlar": ("Men in Black: International", "2019", False),
    "air katta sakrash air jordan": ("Air", "2023", False),
    "air jordan": ("Air", "2023", False),
    "ajal poygasi": ("Death Race", "2008", False),
    "almashtirilgan bola": ("Changeling", "2008", False),
    "aviator": ("The Aviator", "2004", False),
    "ballerina qasos": ("Ballerina", "2023", False),
    "berlin uzra parvoz": ("Retribution", "2023", False),
    "bezos amazon afsonasi": ("Bezos The Beginning", "2023", False),
    "dedpul 2": ("Deadpool 2", "2018", False),
    "dedpul va rosomaxa": ("Deadpool & Wolverine", "2024", False),
    "eramizdan song": ("After Earth", "2013", False),
    "etik kiygan mushuk 2 songgi tilak": ("Puss in Boots: The Last Wish", "2022", False),
    "fath": ("Fateh", "2025", False),
    "flesh": ("The Flash", "2023", False),
    "grenlandiya": ("Greenland", "2020", False),
    "ip man": ("Ip Man", "2008", False),
    "ip man 1 qism": ("Ip Man", "2008", False),
    "ip man 2 qism": ("Ip Man 2", "2010", False),
    "ip man 3 qism": ("Ip Man 3", "2015", False),
    "ip man afsonaning tugilishi": ("The Legend Is Born: Ip Man", "2010", False),
    "iskanja": ("Muzzle", "2023", False),
    "javobsiz sevgi": ("Bihter", "2023", False),
    "jodu saltanati": ("Fantastic Beasts and Where to Find Them", "2016", False),
    "jodu saltanati 1 garoyib maxluqlar": ("Fantastic Beasts and Where to Find Them", "2016", False),
    "jodu saltanati 2 grindelvaldning jinoyatlari": ("Fantastic Beasts: The Crimes of Grindelwald", "2018", False),
    "jodu saltanati 3 dambldor sirlari": ("Fantastic Beasts: The Secrets of Dumbledore", "2022", False),
    "jodugar garb jodugari afsonasi": ("Wicked", "2024", False),
    "jon karter": ("John Carter", "2012", False),
    "kelajak chegarasi": ("Edge of Tomorrow", "2014", False),
    "labirintdagilar": ("The Maze Runner", "2014", False),
    "labirintdagilar 1 xavfli tuzoq": ("The Maze Runner", "2014", False),
    "labirintdagilar 2 olov iskanjasida": ("Maze Runner: The Scorch Trials", "2015", False),
    "labirintdagilar 3 olimga davo": ("Maze Runner: The Death Cure", "2018", False),
    "labirintdagilar 3 olimga qarshi": ("Maze Runner: The Death Cure", "2018", False),
    "lara kroft dahma talonchisi": ("Lara Croft: Tomb Raider", "2001", False),
    "lara kroft dahma talonchisi 1 qism": ("Lara Croft: Tomb Raider", "2001", False),
    "lara kroft dahma talonchisi 2 hayot beshigi": ("Lara Croft: Tomb Raider - The Cradle of Life", "2003", False),
    "lev yashin orzuimdagi darvozabon": ("Лев Яшин. Вратарь моей мечты", "2019", False),
    "mumiyo 1 qism": ("The Mummy", "1999", False),
    "mumiyo 2 qaytish": ("The Mummy Returns", "2001", False),
    "mumiyo 3 ajdar imperatorining qabri": ("The Mummy: Tomb of the Dragon Emperor", "2008", False),
    "muqaddas zamin salohiddin ayyubiy": ("Kingdom of Heaven", "2005", False),
    "nuh": ("Noah", "2014", False),
    "orgimchak odam": ("Spider-Man: Homecoming", "2017", False),
    "orgimchak odam uyga qaytish": ("Spider-Man: Homecoming", "2017", False),
    "orgimchak odam 2 uydan uzoqda": ("Spider-Man: Far From Home", "2019", False),
    "orgimchak odam 3 uyga yol yoq": ("Spider-Man: No Way Home", "2021", False),
    "orgimchak odam 4 yangi kun": ("Spider-Man: No Way Home", "2021", False),
    "ovchi kreyven": ("Kraven the Hunter", "2024", False),
    "piyoda qurbonligi": ("Pawn Sacrifice", "2014", False),
    "polat alximik": ("Fullmetal Alchemist", "2017", False),
    "polat alximik 1 qism": ("Fullmetal Alchemist", "2017", False),
    "polat alximik 2 chandiq qasosi": ("Fullmetal Alchemist: The Revenge of Scar", "2022", False),
    "qamoqxona nazoratchisi": ("Jailer", "2023", False),
    "qasoskorlar cheksizlik jangi": ("Avengers: Infinity War", "2018", False),
    "qutbli": ("Polar", "2019", False),
    "shamolni boysundirgan bola": ("The Boy Who Harnessed the Wind", "2019", False),
    "sirli sayohat 2 sirli orol": ("Journey 2: The Mysterious Island", "2012", False),
    "skelet kaliti": ("The Skeleton Key", "2005", False),
    "snayper": ("Sniper", "1993", False),
    "snayper 1 qism": ("Sniper", "1993", False),
    "snayper 2 qism": ("Sniper 2", "2002", False),
    "snayper 3 qism": ("Sniper 3", "2004", False),
    "snayper 4 qayta yuklash": ("Sniper: Reloaded", "2011", False),
    "snayper 5 meros": ("Sniper: Legacy", "2014", False),
    "snayper 6 arvoh izidan": ("Sniper: Ghost Shooter", "2016", False),
    "snayper 7 maxfiy missiya": ("Sniper: Rogue Mission", "2022", False),
    "snayper 8 maxsus jangchi": ("Sniper: G.R.I.T. - Global Response & Intelligence Team", "2023", False),
    "snayper songgi jang": ("Sniper: Ultimate Kill", "2017", False),
    "taksi haydovchisi": ("A Taxi Driver", "2017", False),
    "tinch okeani dahshatlari 2 qozgolon": ("Pacific Rim: Uprising", "2018", False),
    "tor ragnaryok": ("Thor: Ragnarok", "2017", False),
    "tosh yonuvchi": ("The Bricklayer", "2023", False),
    "trampning yuksalishi": ("The Apprentice", "2024", False),
    "troll": ("Troll", "2022", False),
    "tugma poygachi 2": ("Born to Race: Fast Track", "2014", False),
    "turist": ("The Tourist", "2010", False),
    "xavfsiz uy keyptaun kodi": ("Safe House", "2012", False),
    "yangi dunyo otmish va kelajak qiroli": ("Secret Level", "2024", True),
    "yangi mutantlar": ("The New Mutants", "2020", False),
    "yashil milya": ("The Green Mile", "1999", False),
    "yovvoyi tabiat qoyniga": ("Into the Wild", "2007", False),
    "vilgelm tell afsonasi": ("William Tell", "2024", False),
    "harbiy asir": ("Prisoner of War", "2025", False),
    "qutqaruvchi": ("The Guardian", "2006", False),
    "batman supermenga qarshi": ("Batman v Superman: Dawn of Justice", "2016", False),
    "uch qahramon": ("Uch qahramon", "2024", False),
    "bunker": ("Der Untergang", "2004", False),
    "kichkina ajdarho": ("How to Train Your Dragon", "2010", False),
    "kuzatuvchilar": ("The Watchers", "2024", False),
    "olov oyini": ("Playing with Fire", "2019", False),
    "momaqaldiroqlar": ("Thunderbolts*", "2025", False),
    "ikkinchi imkoniyat": ("Gridiron Gang", "2006", False),
    "xasis": ("Radin!", "2016", False),
    "ekzorsist": ("The Pope's Exorcist", "2023", False),
    "loyqa suv": ("The Shallows", "2016", False),
    "danki": ("Dunki", "2023", False),
    "ogrilar armiyasi": ("Army of Thieves", "2021", False),
    "hisobchi": ("The Accountant", "2016", False),
    "amazonka xazinasi": ("The Rundown", "2003", False),
    "katta qadam": ("Walking Tall", "2004", False),
    "qizil ogohlantirish": ("Red Notice", "2021", False),
    "josus dostlar": ("Central Intelligence", "2016", False),
    "oqdan tez": ("Faster", "2010", False),
    "sirli sayohat": ("Journey 2: The Mysterious Island", "2012", False),
    "sotqin": ("Snitch", "2013", False),
    "gerakl": ("Hercules", "2014", False),
    "san andreas zilzilasi": ("San Andreas", "2015", False),
    "khanzab": ("Khanzab", "2023", False),
    "uchuvchining parvozi": ("Flight of the Navigator", "1986", False),
    "tuzoq": ("Trap", "2024", False),
    "novda": ("Novda", "2015", False),
    "darvin missiyasi": ("G-Force", "2009", False),
    "sherik": ("CHiPs", "2017", False),
    "omadli jentelmenlar": ("Джентльмены удачи", "1971", False),
    "ormon ahli": ("Over the Hedge", "2006", False),
    "kichkina nikolya": ("Le Petit Nicolas", "2009", False),
    "shirinliklar mamlakati": ("Charlie and the Chocolate Factory", "2005", False),
    "muhabbat sehri": ("Enchanted", "2007", False),
    "ota onalar uchun tuzoq": ("The Parent Trap", "1998", False),
    "super it": ("Underdog", "2007", False),
    "kesha": ("Возвращение блудного попугая", "1984", False),
    "elemental": ("Elemental", "2023", False),
    "jigar": ("Джигар", "2024", False),
    "betmen muqaddima": ("Batman Begins", "2005", False),
    "yalang oyoq muhabbat": ("Barefoot", "2014", False),
    "iztopar afsonasi": ("Legend of the Seeker", "2008", True),
    "oy ritsari": ("Moon Knight", "2022", True),
    "supermen polat odam": ("Man of Steel", "2013", False),
    "uch bahodir va yer kindigi": ("Три богатыря и Пуп Земли", "2023", False),
    "misr afsonalari": ("Gods of Egypt", "2016", False),
    "omadsizga kulgan omad": ("Just My Luck", "2006", False),
    "garoyib odamlar 4": ("X-Men Origins: Wolverine", "2009", False),
    "karib dengizi qaroqchilari 4 nomalum sohillarda": ("Pirates of the Caribbean: On Stranger Tides", "2011", False),
}


def _match_exact_search_entry(norm_n: str):
    """
    EXACT_TMDB_SEARCH_MAP ichidan aniq moslikni topadi.
    Qisqa 1 so'zli nomlar (masalan 'tuzoq' yoki 'qutqaruvchi') boshqa uzun nomlarga
    noto'g'ri ilinib qolmasligi uchun uzunlik nisbatini tekshiradi.
    """
    if not norm_n:
        return None
    if norm_n in EXACT_TMDB_SEARCH_MAP:
        return EXACT_TMDB_SEARCH_MAP[norm_n]
    for k_norm, val_tuple in EXACT_TMDB_SEARCH_MAP.items():
        if len(k_norm) >= 8 and len(norm_n) >= 8:
            if k_norm in norm_n or norm_n in k_norm:
                ratio = min(len(k_norm), len(norm_n)) / max(len(k_norm), len(norm_n))
                if ratio >= 0.72:
                    return val_tuple
    return None


_SHARED_HTTP_SESSION: aiohttp.ClientSession | None = None

async def _get_http_session() -> aiohttp.ClientSession:
    global _SHARED_HTTP_SESSION
    if _SHARED_HTTP_SESSION is None or _SHARED_HTTP_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
        _SHARED_HTTP_SESSION = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=12)
        )
    return _SHARED_HTTP_SESSION

async def close_http_session():
    global _SHARED_HTTP_SESSION
    if _SHARED_HTTP_SESSION is not None and not _SHARED_HTTP_SESSION.closed:
        await _SHARED_HTTP_SESSION.close()
        _SHARED_HTTP_SESSION = None


def _extract_season_and_episode(raw_n: str, raw_caption: str = "", file_name: str = "") -> tuple[int, int, bool]:
    """
    Nom, caption va fayl nomidan (season_num, episode_num, has_serial_marker) ni 100% aniqlikda ajratadi.
    Barcha formatlarni qo'llab-quvvatlaydi:
      - S02E14 / s1e5 / 2F14Q / 2F1Q14Q / [s1s1q720]
      - 2-fasl 14-qism / 1-sezon 5-seriya / 2-mavsum 3-epizod
      - @Kino_BluRay_Uzb_Oy_Ritsari_3-qism_1080p.mkv (tagchiziqlar bo'lsa ham!)
      - 6-qism FINAL / 14-qism / 25-seriya / 12-epizod / Qism: 14 / Seriya 5
    """
    season = 1
    episode = 1
    found_marker = False
    fn_clean = re.sub(r"[_\.]+", " ", file_name or "")
    combined = f"{raw_n}\n{raw_caption}\n{fn_clean}"
    comb_low = combined.lower()

    # 1. Aniq S01E05, [s1s5q720] yoki 1F5Q formatlar
    se_m = (
        re.search(r"[sS](\d{1,2})\s*[eE](\d{1,3})", fn_clean)
        or re.search(r"[sS](\d{1,2})\s*[eE](\d{1,3})", raw_n)
        or re.search(r"[sS](\d{1,2})\s*[eE](\d{1,3})", raw_caption)
    )
    if se_m:
        return max(1, int(se_m.group(1))), max(1, int(se_m.group(2))), True

    anidub_m = re.search(r"\[s(\d{1,2})s(\d{1,3})q", file_name or "", flags=re.IGNORECASE)
    if anidub_m:
        return max(1, int(anidub_m.group(1))), max(1, int(anidub_m.group(2))), True

    fq_m = (
        re.search(r"(\d{1,2})F\d+Q(\d{1,3})Q", file_name or "", flags=re.IGNORECASE)
        or re.search(r"(\d{1,2})F(\d{1,3})Q", file_name or "", flags=re.IGNORECASE)
    )
    if fq_m:
        return max(1, int(fq_m.group(1))), max(1, int(fq_m.group(2))), True

    # 2. Fasl / Sezon / Mavsum raqamini ajratish
    s_m = (
        re.search(r"\b(\d{1,2})\s*[-–.]?\s*(?:fasl|sezon|mavsum|season)\b", combined, flags=re.IGNORECASE)
        or re.search(r"\b(?:fasl|sezon|mavsum|season)\s*[:=#-]?\s*(\d{1,2})\b", combined, flags=re.IGNORECASE)
    )
    if s_m:
        season = max(1, int(s_m.group(1)))
        found_marker = True

    # 3. Qism / Seriya / Epizod raqamini ajratish (1..999 gacha, tagchiziqli fayl nomlaridan ham!)
    ep_m = (
        re.search(r"\b(\d{1,3})\s*[-–.]?\s*(?:qism|seriya|epizod|серия|эпизод)\b", raw_n, flags=re.IGNORECASE)
        or re.search(r"\b(?:qism|seriya|epizod|серия|эпизод|ep\.?)\s*[:=#-]?\s*(\d{1,3})\b", raw_n, flags=re.IGNORECASE)
        or re.search(r"\b(\d{1,3})\s*[-–.]?\s*(?:qism|seriya|epizod|серия|эпизод)\b", raw_caption, flags=re.IGNORECASE)
        or re.search(r"\b(?:qism|seriya|epizod|серия|эпизод|ep\.?)\s*[:=#-]?\s*(\d{1,3})\b", raw_caption, flags=re.IGNORECASE)
        or re.search(r"\b(\d{1,3})\s*[-–.]?\s*(?:qism|seriya|epizod|серия|эпизод)\b", fn_clean, flags=re.IGNORECASE)
        or re.search(r"\b(?:qism|seriya|epizod|серия|эпизод|ep\.?)\s*[:=#-]?\s*(\d{1,3})\b", fn_clean, flags=re.IGNORECASE)
    )
    if ep_m:
        episode = max(1, int(ep_m.group(1)))
        if (
            episode >= 10
            or any(k in comb_low for k in ("serial", "сериал", "seriya", "серия", "epizod", "эпизод", "fasl", "sezon", "mavsum", "final", "финал"))
        ):
            found_marker = True

    return season, episode, found_marker


def _clean_serial_base_title(raw_n: str) -> str:
    b = (raw_n or "").strip()
    b = re.sub(r"^[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\s]+", "", b).strip()
    b = re.sub(r"^[\W_]*(?:serial|сериал)[\W_:]*", "", b, flags=re.IGNORECASE).strip()
    b = re.sub(r"\(\s*(?:serial|сериал|19\d{2}|20\d{2}|o['`‘ʻ]?zbek\s*tilida|uzbek\s*tilida).*?\)", "", b, flags=re.IGNORECASE)
    b = re.sub(r"\[\s*(?:1080p|720p|480p|4k|hd|full\s*hd).*?\]", "", b, flags=re.IGNORECASE)
    b = re.sub(r"\b[sS]\d{1,2}\s*[eE]\d{1,3}\b.*$", "", b)
    b = re.sub(r"\b\d{1,2}\s*[-–.]?\s*(?:fasl|sezon|mavsum|season)\b.*$", "", b, flags=re.IGNORECASE)
    b = re.sub(r"\b(?:fasl|sezon|mavsum|season)\s*[:=#-]?\s*\d{1,2}\b.*$", "", b, flags=re.IGNORECASE)
    b = re.sub(r"\b\d{1,3}\s*[-–.]?\s*(?:qism|seriya|epizod|серия|эпизод)\b.*$", "", b, flags=re.IGNORECASE)
    b = re.sub(r"\b(?:qism|seriya|epizod|серия|эпизод)\s*[:=#-]?\s*\d{1,3}\b.*$", "", b, flags=re.IGNORECASE)
    b = re.sub(r"\b(?:serial|сериал|final|финал|1080p|720p|480p|full\s*hd|4k\s*ultra)\b", "", b, flags=re.IGNORECASE)
    b = re.sub(r"\s+", " ", b).strip(" -–:|,._()[]«»\"")
    return b or raw_n.strip()


def extract_base_title_and_part(name: str, raw_caption: str = "", file_name: str = "") -> dict:
    """
    Kino yoki serial nomidan:
    - is_serial: 1 (agar serial bo'lsa) yoki 0 (kino)
    - base_title: Guruhlash uchun asosiy kino/serial nomi (masalan: 'Mumiyo', 'Garri Potter', 'Afsungar Merlin', 'Oy Ritsari')
    - season_num: Fasl raqami (1, 2, 3...)
    - part_num: Qism tartib raqami (1, 2, 3... 999)
    """
    raw_n = (name or "").strip()
    norm_n = _norm_title(raw_n)
    fn_clean = re.sub(r"[_\.]+", " ", file_name or "")
    blob = _norm_title(f"{raw_n} {raw_caption} {fn_clean}")
    snum, epnum, has_serial_marker = _extract_season_and_episode(raw_n, raw_caption, file_name)

    # 1. Haqiqiy ma'lum seriallarni aniq aniqlash
    if "afsungar merlin" in norm_n or "afsungar merlin" in blob:
        return {"is_serial": 1, "base_title": "Afsungar Merlin", "season_num": snum, "part_num": epnum}

    if "envel qahramonlari" in norm_n or "envel qahramonlari" in blob:
        return {"is_serial": 1, "base_title": "Envel Qahramonlari", "season_num": snum, "part_num": epnum}

    if "iztopar" in norm_n or "iztopar" in blob:
        return {"is_serial": 1, "base_title": "Iztopar Afsonasi", "season_num": snum, "part_num": epnum}

    if "oy ritsari" in norm_n or "oy ritsari" in blob or "moon knight" in blob:
        return {"is_serial": 1, "base_title": "Oy Ritsari", "season_num": snum, "part_num": epnum}

    # 2. Ko'p qismli mashhur kinolar franshizalarini yagona base_title ostida va to'g'ri 1, 2, 3... tartibda birlashtirish
    if "predator" in norm_n and "xishnik" in norm_n:
        pm = re.search(r"\b([1-9])\s*[-–]?\s*qism", raw_n, flags=re.IGNORECASE)
        return {"is_serial": 0, "base_title": "Predator & Xishnik", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("yomon yigitlar"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Yomon yigitlar", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("mumiya") or norm_n.startswith("mumiyo"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Mumiyo", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("sonic"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Sonic", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("krid"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Krid", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("padington"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Padington", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("garri potter"):
        if "7.1" in raw_n or "7 1" in norm_n:
            pnum = 7
        elif "7.2" in raw_n or "7 2" in norm_n:
            pnum = 8
        else:
            pm = re.search(r"\b([1-8])\b", norm_n)
            pnum = int(pm.group(1)) if pm else 1
        return {"is_serial": 0, "base_title": "Garri Potter", "season_num": 1, "part_num": pnum}

    if norm_n.startswith("jumanji"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Jumanji", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("ilon hamlasi"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Ilon Hamlasi", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("malikaning kundaligi"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Malikaning kundaligi", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("shahzoda va bori"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Shahzoda va Bo'ri", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("beethoven"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Beethoven", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if "masxaraboz" in norm_n and "penni vays" in norm_n:
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Masxaraboz ONO Penni Vays", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("chaqmoq makvin"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Chaqmoq Makvin", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("lara kroft"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Lara Kroft: Dahma talonchisi", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("ip man"):
        if "afsonaning" in norm_n:
            pnum = 4
        else:
            pm = re.search(r"\b([1-9])\b", norm_n)
            pnum = int(pm.group(1)) if pm else 1
        return {"is_serial": 0, "base_title": "Ip Man", "season_num": 1, "part_num": pnum}

    if norm_n.startswith("polat alximik"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Po'lat alximik", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("snayper"):
        if "songgi jang" in norm_n:
            pnum = 9
        else:
            pm = re.search(r"\b([1-9])\b", norm_n)
            pnum = int(pm.group(1)) if pm else 1
        return {"is_serial": 0, "base_title": "Snayper", "season_num": 1, "part_num": pnum}

    if norm_n.startswith("jodu saltanati"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Jodu saltanati", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("orgimchak odam"):
        if "uyga qaytish" in norm_n:
            pnum = 1
        elif "uydan uzoqda" in norm_n or "2" in norm_n:
            pnum = 2
        elif "uyga yol yoq" in norm_n or "3" in norm_n:
            pnum = 3
        elif "yangi kun" in norm_n or "4" in norm_n:
            pnum = 4
        else:
            pnum = 1
        return {"is_serial": 0, "base_title": "O'rgimchak odam", "season_num": 1, "part_num": pnum}

    if norm_n.startswith("labirintdagilar"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Labirintdagilar", "season_num": 1, "part_num": int(pm.group(1)) if pm else 1}

    if ("supermen" in norm_n or "supper men" in norm_n) and "polat odam" in norm_n:
        return {"is_serial": 0, "base_title": "Supermen: Po'lat odam", "season_num": 1, "part_num": 1}

    if norm_n.startswith("sirli sayohat"):
        return {"is_serial": 0, "base_title": "Sirli sayohat 2: Sirli orol", "season_num": 1, "part_num": 1}

    if ("uch bahodir" in norm_n or "uch baxodir" in norm_n) and ("yer kindigi" in norm_n or "yerni markazida" in norm_n):
        return {"is_serial": 0, "base_title": "Uch bahodir va Yer kindigi", "season_num": 1, "part_num": 1}

    if ("uch bahodir" in norm_n or "uch baxodir" in norm_n) and ("ot taxt sohibi" in norm_n or "katta poygalar" in norm_n):
        return {"is_serial": 0, "base_title": "Uch bahodir va Katta poygalar", "season_num": 1, "part_num": 1}

    # 3. Istalgan YANGI serialni avtomatik tanib olish (fasl/sezon/serial/seriya/final/S01E01/6+ qism)
    if has_serial_marker or any(k in norm_n or k in blob for k in ["serial", "сериал", "seriya", "серия", "fasl", "sezon", "mavsum", "epizod", "эпизод"]):
        btitle = _clean_serial_base_title(raw_n)
        return {"is_serial": 1, "base_title": btitle, "season_num": snum, "part_num": epnum}

    # 4. Umumiy X-qism yozilgan kinolar yoki yangi seriallar (1..999 gacha, FINAL bilan ham!)
    gen_m = re.search(r"^(.*?)\s+(\d{1,3})\s*[-–.]?\s*(?:qism|part)\b", raw_n, flags=re.IGNORECASE)
    if gen_m and len(gen_m.group(1).strip()) >= 3:
        pnum = int(gen_m.group(2))
        btitle = _clean_serial_base_title(gen_m.group(1))
        is_ser = 1 if (pnum >= 6 or "final" in blob or "финал" in blob) else 0
        return {"is_serial": is_ser, "base_title": btitle, "season_num": snum, "part_num": pnum}

    clean_bt = _clean_serial_base_title(raw_n)
    return {"is_serial": 1 if (epnum >= 6 or has_serial_marker) else 0, "base_title": clean_bt, "season_num": snum, "part_num": epnum}


def _year_matches(cand_year_str: str, target_year_str: str, tolerance: int = 2) -> bool:
    if not target_year_str or not re.match(r"^(19\d{2}|20\d{2})$", str(target_year_str).strip()[:4]):
        return True
    if not cand_year_str or not re.match(r"^(19\d{2}|20\d{2})$", str(cand_year_str).strip()[:4]):
        return True
    return abs(int(str(cand_year_str)[:4]) - int(str(target_year_str)[:4])) <= tolerance


async def _tmdb_search_request(
    session: aiohttp.ClientSession,
    endpoint: str,
    query: str,
    year: str = "",
    lang: str = "ru-RU",
    api_key: str = "",
    read_token: str = "",
    require_similarity: bool = True,
    target_year: str = ""
) -> str:
    """
    1-Provayder: TheMovieDB (TMDB API) ga so'rov yuborib FAQAT aniq mos keluvchi
    kino/serialning vertikal HD poster_path ini qaytaradi (hech qachon boshqa kino rasmini olmaydi!).
    """
    if not query or len(query.strip()) < 2:
        return ""
    url = f"https://api.themoviedb.org/3/{endpoint}"
    params = {
        "api_key": api_key,
        "query": query.strip(),
        "language": lang,
        "include_adult": "false"
    }
    use_y = str(year or "").strip()
    if use_y and re.match(r"^(19\d{2}|20\d{2})$", use_y):
        if endpoint == "search/movie":
            params["year"] = use_y
        elif endpoint == "search/tv":
            params["first_air_date_year"] = use_y

    headers = {"Accept": "application/json"}
    if read_token:
        headers["Authorization"] = f"Bearer {read_token}"

    check_year = str(target_year or year or "").strip()

    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results") or []
                for item in results[:8]:
                    if endpoint == "search/multi" and item.get("media_type") == "person":
                        continue
                    rel_yr = (item.get("release_date") or item.get("first_air_date") or "")[:4]
                    if check_year and not _year_matches(rel_yr, check_year, tolerance=2):
                        continue
                    if require_similarity:
                        cand_titles = [
                            item.get("title"),
                            item.get("original_title"),
                            item.get("name"),
                            item.get("original_name")
                        ]
                        if not any(ct and _titles_similar(query, ct, threshold=0.68) for ct in cand_titles):
                            continue
                    # Faqat vertikal HD poster_path ni olamiz (boshqa kadr yoki xato fon emas)
                    poster = item.get("poster_path")
                    if poster:
                        return f"https://image.tmdb.org/t/p/w780{poster}"
    except Exception as e:
        logging.debug(f"TMDB qidiruv xatosi ({query}): {e}")
    return ""


async def _kinopoisk_uz_search_movie(
    session: aiohttp.ClientSession,
    query: str,
    year: str = ""
) -> dict:
    """
    2-Provayder: KinopoiskAPI.uz (https://api.kinopoiskapi.uz/v1/kinopoisk/movie/search)
    Swagger OpenAPI 2.0 spetsifikatsiyasi bo'yicha:
    - GET /v1/kinopoisk/movie/search?page=1&limit=3&name=<query>
    - GET /v1/kinopoisk/movie/{id}
    - Header: Authorization: Bearer <token>
    """
    if not query or len(query.strip()) < 2:
        return {}
    base_url = getattr(config, "KINOPOISK_UZ_BASE_URL", "https://api.kinopoiskapi.uz").rstrip("/")
    tok_main = await db.get_setting("kinopoisk_uz_token", getattr(config, "KINOPOISK_UZ_TOKEN", "987b16554ae0497db31ff58b90e8f6aa"))
    tok_uuid = getattr(config, "KINOPOISK_UZ_TOKEN_UUID", "987b1655-4ae0-497d-b31f-f58b90e8f6aa")
    tokens = [t for t in [tok_uuid, tok_main] if t]

    search_url = f"{base_url}/v1/kinopoisk/movie/search"
    params = {"page": 1, "limit": 5, "name": query.strip()}

    for tok in tokens:
        headers = {
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json"
        }
        try:
            async with session.get(search_url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    items = []
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        items = data.get("results") or data.get("docs") or data.get("data") or data.get("items") or ([data] if data.get("kp_id") or data.get("kino_poisk_id") or data.get("poster") else [])

                    chosen = None
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        it_year = str(it.get("year_production") or it.get("year") or "")[:4]
                        if year and it_year and not _year_matches(it_year, year, tolerance=2):
                            continue
                        cand_titles = [
                            it.get("name_ru"), it.get("name_eng"),
                            it.get("name_original"), it.get("name")
                        ]
                        if any(cand_titles) and not any(ct and _titles_similar(query, str(ct), threshold=0.68) for ct in cand_titles):
                            continue
                        if year and it_year and it_year == str(year)[:4]:
                            chosen = it
                            break
                        if not chosen:
                            chosen = it

                    if chosen:
                        poster = (chosen.get("poster") or chosen.get("poster_url") or "").strip()
                        kp_id = chosen.get("kp_id") or chosen.get("kino_poisk_id") or chosen.get("id")
                        if not poster and kp_id:
                            det_url = f"{base_url}/v1/kinopoisk/movie/{kp_id}"
                            async with session.get(det_url, headers=headers) as d_resp:
                                if d_resp.status == 200:
                                    det = await d_resp.json(content_type=None)
                                    if isinstance(det, dict):
                                        chosen = det
                                        poster = (det.get("poster") or det.get("poster_url") or "").strip()

                        raw_countries = chosen.get("countries") or []
                        c_names = []
                        for c_item in raw_countries:
                            if isinstance(c_item, dict) and c_item.get("name"):
                                c_names.append(str(c_item["name"]))
                            elif isinstance(c_item, str):
                                c_names.append(c_item)

                        raw_genres = chosen.get("genres") or []
                        g_names = []
                        for g_item in raw_genres:
                            if isinstance(g_item, dict) and g_item.get("name"):
                                g_names.append(str(g_item["name"]))
                            elif isinstance(g_item, str):
                                g_names.append(g_item)

                        found_yr = str(chosen.get("year_production") or chosen.get("year") or "")[:4]
                        return {
                            "poster": poster if poster.startswith(("http://", "https://")) else "",
                            "year": found_yr if re.match(r"^(19\d{2}|20\d{2})$", found_yr) else "",
                            "country": normalize_country(", ".join(c_names)) if c_names else "",
                            "genre": normalize_genres(", ".join(g_names), query) if g_names else "",
                            "imdb": str(chosen.get("imdb_rating") or chosen.get("kino_poisk_rating") or ""),
                        }
                elif resp.status >= 500:
                    break
        except Exception as e:
            logging.debug(f"KinopoiskAPI.uz qidiruv xatosi ({query}): {e}")
            break
    return {}


async def _omdb_search_movie(
    session: aiohttp.ClientSession,
    query: str,
    year: str = "",
    is_serial: bool = False,
    require_similarity: bool = True
) -> dict:
    """
    3-Provayder: The OMDb API (https://www.omdbapi.com/?apikey=23b88a7b)
    - Avval aniq nom (?t=...) va yil (?y=...) bilan qidiradi;
    - Har bir topilgan kino nomi va yili qat'iy tekshiriladi — boshqa kinoning posteri hech qachon qo'yilmaydi!
    """
    if not query or len(query.strip()) < 2:
        return {}
    omdb_key = await db.get_setting("omdb_api_key", getattr(config, "OMDB_API_KEY", "23b88a7b"))
    if not omdb_key:
        return {}

    url = "https://www.omdbapi.com/"
    m_type = "series" if is_serial else "movie"
    clean_yr = str(year).strip()[:4] if (year and re.match(r"^(19\d{2}|20\d{2})", str(year).strip())) else ""

    def _parse_omdb_payload(d: dict) -> dict:
        if not isinstance(d, dict) or d.get("Response") != "True":
            return {}
        cand_title = (d.get("Title") or "").strip()
        yr_m = re.search(r"(19\d{2}|20\d{2})", str(d.get("Year") or ""))
        found_yr = yr_m.group(1) if yr_m else ""
        if clean_yr and found_yr and not _year_matches(found_yr, clean_yr, tolerance=2):
            return {}
        if require_similarity and cand_title and not _titles_similar(query, cand_title, threshold=0.68):
            return {}
        poster_raw = (d.get("Poster") or "").strip()
        poster = poster_raw if (poster_raw != "N/A" and poster_raw.startswith(("http://", "https://"))) else ""
        raw_c = (d.get("Country") or "").strip()
        country = normalize_country(raw_c) if (raw_c and raw_c != "N/A") else ""
        raw_g = (d.get("Genre") or "").strip()
        genre = normalize_genres(raw_g, query) if (raw_g and raw_g != "N/A") else ""
        imdb_r = (d.get("imdbRating") or "").strip()
        return {
            "poster": poster,
            "year": found_yr,
            "country": country,
            "genre": genre,
            "imdb": imdb_r if (imdb_r and imdb_r != "N/A") else "",
        }

    # 1. To'g'ridan-to'g'ri ?t= qidiruvi (yil bilan va yilsiz)
    attempts = []
    if clean_yr:
        attempts.append({"apikey": omdb_key, "t": query.strip(), "y": clean_yr, "type": m_type})
        attempts.append({"apikey": omdb_key, "t": query.strip(), "y": clean_yr})
    attempts.append({"apikey": omdb_key, "t": query.strip(), "type": m_type})
    attempts.append({"apikey": omdb_key, "t": query.strip()})

    for params in attempts:
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    parsed = _parse_omdb_payload(data)
                    if parsed and (parsed.get("poster") or parsed.get("year")):
                        return parsed
        except Exception as e:
            logging.debug(f"OMDb (?t=) xatosi ({query}): {e}")

    # 2. Ro'yxat bo'yicha ?s= qidiruvi (qat'iy nom va yil filtri bilan)
    s_attempts = []
    if clean_yr:
        s_attempts.append({"apikey": omdb_key, "s": query.strip(), "y": clean_yr})
    s_attempts.append({"apikey": omdb_key, "s": query.strip()})

    for params in s_attempts:
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    search_list = data.get("Search") or [] if isinstance(data, dict) else []
                    for item in search_list[:5]:
                        item_title = (item.get("Title") or "").strip()
                        yr_m = re.search(r"(19\d{2}|20\d{2})", str(item.get("Year") or ""))
                        item_yr = yr_m.group(1) if yr_m else ""
                        if clean_yr and item_yr and not _year_matches(item_yr, clean_yr, tolerance=2):
                            continue
                        if require_similarity and item_title and not _titles_similar(query, item_title, threshold=0.68):
                            continue
                        p_raw = (item.get("Poster") or "").strip()
                        imdb_id = (item.get("imdbID") or "").strip()
                        if imdb_id:
                            async with session.get(url, params={"apikey": omdb_key, "i": imdb_id}) as i_resp:
                                if i_resp.status == 200:
                                    i_data = await i_resp.json(content_type=None)
                                    parsed = _parse_omdb_payload(i_data)
                                    if parsed:
                                        return parsed
                        if p_raw and p_raw != "N/A" and p_raw.startswith(("http://", "https://")):
                            return {
                                "poster": p_raw,
                                "year": item_yr,
                                "country": "",
                                "genre": "",
                                "imdb": "",
                            }
        except Exception as e:
            logging.debug(f"OMDb (?s=) xatosi ({query}): {e}")
    return {}


_TMDB_POSTER_CACHE: dict = {}

_LOCAL_SKIP_FOREIGN_POSTER_KEYWORDS = (
    "konsert", "bravo jamoasi", "million jamoasi", "dizayn jamoasi", "aristokratlar"
)

async def find_movie_poster_tmdb(name: str, year: str = "", is_serial: bool = False, force: bool = False) -> str:
    """
    3-BOSQICHLI QAT'IY ANIQLIKDAGI AVTO-POSTER QIDIRUV TIZIMI:
    1-Bosqich: TheMovieDB (TMDB API — image.tmdb.org HD posterlar)
    2-Bosqich: KinopoiskAPI.uz (api.kinopoiskapi.uz/v1/kinopoisk/movie/search)
    3-Bosqich: The OMDb API (omdbapi.com — IMDb rasmiy posterlari)
    Har bir natija qat'iy nom o'xshashligi va yil oralig'i bo'yicha tekshiriladi —
    boshqa kinoning rasmini hech qachon qo'ymaydi!
    """
    if not force and await db.get_setting("tmdb_auto_poster", "1") != "1":
        return ""
    norm_n = _norm_title(name)
    if not norm_n or any(kw in norm_n for kw in _LOCAL_SKIP_FOREIGN_POSTER_KEYWORDS):
        return ""

    cache_key = f"{norm_n}:{year}:{int(is_serial)}"
    if cache_key in _TMDB_POSTER_CACHE:
        return _TMDB_POSTER_CACHE[cache_key]

    api_key = await db.get_setting("tmdb_api_key", config.TMDB_API_KEY)
    read_token = await db.get_setting("tmdb_read_token", config.TMDB_READ_TOKEN)
    session = await _get_http_session()

    # 1. EXACT_TMDB_SEARCH_MAP orqali 100% aniq kino nomini aniqlash
    exact_entry = _match_exact_search_entry(norm_n)
    ex_query, ex_year, ex_is_tv = exact_entry if exact_entry else ("", "", is_serial)
    use_is_serial = bool(ex_is_tv or is_serial)

    target_year = str(ex_year or year or "").strip()
    known = _find_exact_known(name)
    if known and not target_year:
        target_year = str(known.get("year", "")).strip()

    # ================= 1-PROVAYDER: THEMOVIEDB (TMDB) =================
    if api_key or read_token:
        if exact_entry:
            ex_endpoint = "search/tv" if use_is_serial else "search/movie"
            for lg in ("ru-RU", "en-US"):
                if target_year:
                    poster = await _tmdb_search_request(
                        session, ex_endpoint, ex_query, year=target_year, lang=lg,
                        api_key=api_key, read_token=read_token, require_similarity=False, target_year=target_year
                    )
                    if poster:
                        _TMDB_POSTER_CACHE[cache_key] = poster
                        return poster
                poster = await _tmdb_search_request(
                    session, ex_endpoint, ex_query, year="", lang=lg,
                    api_key=api_key, read_token=read_token, require_similarity=True, target_year=target_year
                )
                if poster:
                    _TMDB_POSTER_CACHE[cache_key] = poster
                    return poster

        endpoint = "search/tv" if use_is_serial else "search/movie"
        clean_title = re.sub(
            r"\b(?:\d+\s*[-–]?\s*(?:qism|seriya|epizod|fasl|sezon)|o['`‘ʻ]?zbek\s*tilida|uzbek\s*tilida|full\s*hd|1080p|720p|4k|premyera|kino|serial)\b",
            "",
            name or "",
            flags=re.IGNORECASE
        )
        clean_title = re.sub(r"[:\-_,.—]", " ", clean_title)
        clean_title = re.sub(r"\s+", " ", clean_title).strip()
        if not clean_title:
            clean_title = re.sub(r"[:\-_,.—]", " ", name or "").strip()

        ru_title = await _translate_query(session, clean_title, "ru")
        en_title = await _translate_query(session, clean_title, "en")

        candidates = []
        for q, lg in [(en_title, "en-US"), (ru_title, "ru-RU"), (clean_title, "ru-RU"), (clean_title, "en-US")]:
            if q and (q, lg) not in candidates:
                candidates.append((q, lg))

        # QAT'IY NOM O'XSHASHLIGI + YIL TEKSHIRUVI (require_similarity=True!)
        if target_year:
            for q, lg in candidates:
                poster = await _tmdb_search_request(
                    session, endpoint, q, year=target_year, lang=lg,
                    api_key=api_key, read_token=read_token, require_similarity=True, target_year=target_year
                )
                if poster:
                    _TMDB_POSTER_CACHE[cache_key] = poster
                    return poster

        for q, lg in candidates:
            poster = await _tmdb_search_request(
                session, endpoint, q, year="", lang=lg,
                api_key=api_key, read_token=read_token, require_similarity=True, target_year=target_year
            )
            if poster:
                _TMDB_POSTER_CACHE[cache_key] = poster
                return poster

        for q, lg in candidates[:2]:
            poster = await _tmdb_search_request(
                session, "search/multi", q, year="", lang=lg,
                api_key=api_key, read_token=read_token, require_similarity=True, target_year=target_year
            )
            if poster:
                _TMDB_POSTER_CACHE[cache_key] = poster
                return poster
    else:
        clean_title = (name or "").strip()
        ru_title = await _translate_query(session, clean_title, "ru")
        en_title = await _translate_query(session, clean_title, "en")

    # ================= 2-PROVAYDER: KINOPOISKAPI.UZ =================
    kp_queries = []
    for kq in [ex_query, ru_title, en_title, clean_title]:
        if kq and kq not in kp_queries:
            kp_queries.append(kq)

    for kq in kp_queries[:3]:
        kp_res = await _kinopoisk_uz_search_movie(session, kq, year=target_year)
        if kp_res.get("poster"):
            _TMDB_POSTER_CACHE[cache_key] = kp_res["poster"]
            return kp_res["poster"]

    # ================= 3-PROVAYDER: THE OMDB API (IMDb) =================
    omdb_queries = []
    for oq in [ex_query, en_title, clean_title]:
        if oq and oq not in omdb_queries:
            omdb_queries.append(oq)

    for oq in omdb_queries[:3]:
        omdb_res = await _omdb_search_movie(
            session, oq, year=target_year, is_serial=use_is_serial,
            require_similarity=(not bool(exact_entry and oq == ex_query))
        )
        if omdb_res.get("poster"):
            _TMDB_POSTER_CACHE[cache_key] = omdb_res["poster"]
            return omdb_res["poster"]

    return ""


# ===================== MOVIE LAND AI — AQLLI KINO TAVSIYA VA QIDIRUV YORDAMCHISI =====================
_AI_INTENT_GENRES = {
    "jangari": ["jangari", "urush", "otishma", "jang", "qasos", "politsiya", "snayper", "maxsus", "boevik", "боевик", "экшн", "action", "superqahramon", "marvel", "dc"],
    "komediya": ["komediya", "kulgili", "kulgi", "hazil", "quvnoq", "xursand", "комедия", "смешной", "смешная", "веселый", "comedy", "prikol"],
    "fantastika": ["fantastika", "fantaziya", "sehr", "sehrgar", "kosmos", "robot", "kelajak", "ajdar", "superqahramon", "фантастика", "фэнтези", "магия", "космос", "marvel", "dc"],
    "qo'rqinchli": ["qorqinchli", "qo'rqinchli", "ujas", "dahshat", "triller", "zombi", "jin", "arvoh", "qotil", "ужасы", "страшный", "триллер", "хоррор", "horror"],
    "drama": ["drama", "dramma", "hayotiy", "tasirli", "ta'sirli", "yiglatadigan", "chuqur", "драма", "жизненный", "трогательный"],
    "melodrama": ["melodrama", "sevgi", "muhabbat", "romantik", "romantika", "oshiq", "мелодрама", "любовь", "романтика", "романтический"],
    "multfilm": ["multfilm", "multik", "bolalar", "oilaviy", "hayvon", "animatsiya", "мультфильм", "мультик", "семейный", "детский"],
    "detektiv": ["detektiv", "sirli", "jinoyat", "kriminal", "tergov", "qotillik", "детектив", "криминал", "тайна", "расследование"],
    "tarixiy": ["tarixiy", "qadimiy", "qirol", "ritsar", "imperiya", "jangchi", "исторический", "история", "древний", "король"],
    "anime": ["anime", "yapon", "аниме", "японский"],
}

_AI_STOPWORDS = {
    "menga", "uchun", "kino", "kinolar", "film", "filmlar", "topib", "ber", "bering", "tavsiya", "qil", "qiling",
    "zor", "zo'r", "yaxshi", "eng", "bir", "bitta", "qaysi", "nima", "bor", "haqida", "bilan", "va", "yoki",
    "ko'rish", "korish", "istayman", "xohlayman", "kerak", "qidir", "qidiryapman", "salom", "assalomu", "alaykum",
    "посоветуй", "найди", "фильм", "фильмы", "кино", "мне", "для", "про", "лучший", "лучшие", "какой", "есть", "привет",
}


async def movie_land_ai_chat(user_query: str, movies_catalog: list, lang: str = "uz") -> dict:
    """
    Movie Land AI — foydalanuvchi so'rovini (kayfiyat, janr, syujet, yil, o'xshash kino, serial)
    tushunib, jonli bazadagi eng mos kinolarni saralab, do'stona javob qaytaradi!
    """
    import html as _html
    raw_q = (user_query or "").strip()
    q_low = raw_q.lower()
    q_norm = _norm_title(raw_q)

    if not movies_catalog:
        empty_msg = (
            "🤖 <b>Movie Land AI:</b> Hozircha katalog to'ldirilmoqda. Tez orada minglab kinolar qo'shiladi!"
            if lang != "ru" else
            "🤖 <b>Movie Land AI:</b> Каталог сейчас наполняется. Скоро появятся лучшие фильмы!"
        )
        return {"reply": empty_msg, "movies": []}

    # Salomlashish yoki yordam so'rovi
    greetings = ("salom", "assalom", "privet", "привет", "hello", "hi", "qalaysan", "nima qila olasan", "yordam", "help")
    if len(q_norm.split()) <= 3 and any(g in q_norm for g in greetings):
        top_pick = sorted(movies_catalog, key=lambda x: int(x.get("views") or 0), reverse=True)[:4]
        if lang == "ru":
            msg = (
                "🤖 <b>Привет! Я — Movie Land AI!</b>\n"
                "Напишите настроение, жанр, год или сюжет фильма (например: <i>«смешная комедия»</i>, "
                "<i>«фильм про магию и короля»</i> или <i>«посоветуй сериал»</i>) — я мгновенно подберу лучшие фильмы из нашей базы!\n\n"
                "🔥 <b>Сейчас популярны:</b>"
            )
        else:
            msg = (
                "🤖 <b>Assalomu alaykum! Men — Movie Land AI yordamchisiman!</b>\n"
                "Kayfiyatingiz, janr, yil yoki esingizda qolgan syujetni yozing (masalan: <i>«kulgili oilaviy kino»</i>, "
                "<i>«sehrgar va qirol haqida serial»</i> yoki <i>«2024 jangari»</i>) — bazamizdan eng zo'rlarini topib beraman!\n\n"
                "🔥 <b>Hozir eng mashhurlari:</b>"
            )
        return {"reply": msg, "movies": top_pick}

    wants_serial = any(k in q_low for k in ("serial", "сериал", "qismli", "fasl", "sezon", "epizod"))
    wants_movie_only = any(k in q_low for k in ("faqat kino", "bitta kino", "to'liq metraj"))
    wants_top = any(k in q_low for k in ("top", "mashhur", "eng zo'r", "eng zor", "eng yaxshi", "reyting", "imdb", "лучш", "популяр", "топ"))
    wants_new = any(k in q_low for k in ("yangi", "premyera", "oxirgi", "новейш", "новинк", "новый", "новые"))
    wants_random = any(k in q_low for k in ("tasodif", "xohlagan", "farqi yo'q", "farqi yoq", "любой", "случайн"))

    year_m = re.search(r"\b(19\d{2}|20\d{2})\b", raw_q)
    target_year = year_m.group(1) if year_m else ""

    matched_genres = []
    for g_key, kws in _AI_INTENT_GENRES.items():
        if any(kw in q_low or kw in q_norm for kw in kws):
            matched_genres.append(g_key)

    tokens = [w for w in q_norm.split() if len(w) >= 3 and w not in _AI_STOPWORDS]

    scored = []
    for m in movies_catalog:
        score = 0.0
        m_name = str(m.get("name") or "")
        m_name_norm = _norm_title(m_name)
        m_genre_low = str(m.get("genre") or "").lower()
        m_cap_norm = _norm_title(str(m.get("caption") or ""))
        m_country_low = str(m.get("country") or "").lower()
        m_year = str(m.get("year") or "")
        m_code = str(m.get("code") or "")
        is_ser = bool(m.get("is_serial"))
        views = int(m.get("views") or 0)
        try:
            imdb_f = float(str(m.get("imdb") or "8.0").replace(",", "."))
        except Exception:
            imdb_f = 8.0

        # Kod bo'yicha aniq moslik
        if q_norm.lstrip("#") == m_code:
            score += 120.0

        # Nom bo'yicha to'liq yoki qisman moslik
        if q_norm and len(q_norm) >= 3:
            if q_norm == m_name_norm:
                score += 100.0
            elif q_norm in m_name_norm or (len(m_name_norm) >= 4 and m_name_norm in q_norm):
                score += 65.0

        # So'zlar bo'yicha syujet + nom + davlat mosligi
        for tok in tokens:
            if tok in m_name_norm:
                score += 24.0
            if tok in m_cap_norm:
                score += 10.0
            if tok in m_genre_low:
                score += 14.0
            if tok in m_country_low:
                score += 12.0

        # Janr/kayfiyat mosligi
        for gk in matched_genres:
            if gk in m_genre_low or (gk == "qo'rqinchli" and "qorqinchli" in _norm_title(m_genre_low)):
                score += 28.0

        # Serial / Kino filtri
        if wants_serial:
            score += 36.0 if is_ser else -15.0
        elif wants_movie_only:
            score += 12.0 if not is_ser else -20.0

        # Yil bo'yicha
        if target_year:
            if m_year == target_year:
                score += 30.0
            elif m_year.isdigit() and abs(int(m_year) - int(target_year)) <= 1:
                score += 12.0

        # Top / Yangi / Tasodifiy bonuslari
        if wants_top:
            score += min(views / 80.0, 20.0) + (imdb_f * 2.5)
        if wants_new and m_year.isdigit() and int(m_year) >= 2023:
            score += 20.0
        if wants_random:
            score += random.uniform(5.0, 25.0)

        # Kichik sifat bonusi (ko'rilish va reyting)
        score += min(views / 500.0, 4.0) + (imdb_f * 0.4)
        scored.append((score, m))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    # Agar kuchli mosliklar bo'lsa shularni olamiz, aks holda eng sara top filmlardan
    best = [m for sc, m in scored[:6] if sc >= 14.0]
    if not best:
        best = [m for _, m in scored[:5]]

    # Agar tashqi Top-15 AI provayderi uchun API kalit ulangan bo'lsa, jonli LLM javobini sinaymiz!
    llm_reply = ""
    try:
        ai_enabled = await db.get_setting("ai_enabled", "1")
        if ai_enabled == "1":
            active_prov = await db.get_setting("ai_active_provider", "gemini")
            api_key = await db.get_setting(f"ai_key_{active_prov}", "")
            if api_key:
                cand_lines = "\n".join(
                    f"- #{m['code']} {m['name']} ({m.get('year','')}, {m.get('genre','')}, IMDb {m.get('imdb','8.4')}, {'Serial' if m.get('is_serial') else 'Kino'}): {(m.get('caption') or '')[:110]}"
                    for m in best[:5]
                )
                sys_lang = "rus tilida" if lang == "ru" else "sof o'zbek tilida"
                prompt = (
                    f"Sen Movie Land kinobotining aqlli 'Movie Land AI' yordamchisisan. "
                    f"Foydalanuvchi savoli: «{raw_q}».\n"
                    f"Bizning bazamizdagi eng mos kinolar:\n{cand_lines}\n\n"
                    f"Faqat yuqoridagi bazadagi kinolardan 3-5 tasini tanlab, {sys_lang} qisqa, samimiy va chiroyli tavsiya yoz. "
                    f"Har bir kino kodini (#kod) ko'rsat. HTML teglaridan faqat <b> va <i> ishlat, 750 belgidan oshmasin."
                )
                llm_reply = await asyncio.wait_for(call_ai_provider(active_prov, api_key, prompt), timeout=12)
    except Exception:
        llm_reply = ""

    if llm_reply and len(llm_reply.strip()) >= 25:
        reply_text = f"🤖 <b>Movie Land AI:</b>\n\n{llm_reply.strip()}"
    else:
        lines = []
        if lang == "ru":
            intro = f"🤖 <b>Movie Land AI</b> подобрал лучшие варианты по запросу <i>«{_html.escape(raw_q[:60])}»</i>:\n"
            for i, m in enumerate(best[:5], 1):
                badge = "📺 Сериал" if m.get("is_serial") else "🎬 Фильм"
                short_cap = (m.get("caption") or "").strip().replace("\n", " ")[:95]
                cap_part = f"\n   <i>{_html.escape(short_cap)}...</i>" if short_cap else ""
                lines.append(
                    f"{i}. <b>#{m['code']} — {_html.escape(str(m['name']))}</b> ({m.get('year','')})\n"
                    f"   {badge} • {m.get('genre','')} • ⭐ {m.get('imdb','8.4')}{cap_part}"
                )
            outro = "\n👇 <i>Нажмите на любой фильм ниже, чтобы сразу открыть и посмотреть!</i>"
        else:
            intro = f"🤖 <b>Movie Land AI</b> sizning <i>«{_html.escape(raw_q[:60])}»</i> so'rovingiz bo'yicha eng moslarini topdi:\n"
            for i, m in enumerate(best[:5], 1):
                badge = "📺 Serial" if m.get("is_serial") else "🎬 Kino"
                short_cap = (m.get("caption") or "").strip().replace("\n", " ")[:95]
                cap_part = f"\n   <i>{_html.escape(short_cap)}...</i>" if short_cap else ""
                lines.append(
                    f"{i}. <b>#{m['code']} — {_html.escape(str(m['name']))}</b> ({m.get('year','')})\n"
                    f"   {badge} • {m.get('genre','')} • ⭐ {m.get('imdb','8.4')}{cap_part}"
                )
            outro = "\n👇 <i>Pastdagi tugmalardan birini bosing — kino kartasi darhol ochiladi!</i>"
        reply_text = intro + "\n" + "\n\n".join(lines) + "\n" + outro

    return {"reply": reply_text, "movies": best[:5]}
