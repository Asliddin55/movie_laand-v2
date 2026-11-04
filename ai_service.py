import re
import json
import html
import urllib.parse
import aiohttp
import logging
import config
import database as db

# Janr imlo xatolarini avtomatik to'g'rilovchi lug'at
GENRE_CORRECTIONS = {
    "jangari": "🔥 Jangari",
    "jngari": "🔥 Jangari",
    "boyevik": "🔥 Jangari",
    "bayovik": "🔥 Jangari",
    "боевик": "🔥 Jangari",
    "action": "🔥 Jangari",
    "sarguzasht": "🔥 Jangari",
    "sarguzash": "🔥 Jangari",
    "приключения": "🔥 Jangari",
    "poyga": "🔥 Jangari",
    "boks": "🔥 Jangari",
    "sport": "🔥 Jangari",
    "komediya": "😂 Komediya",
    "komedia": "😂 Komediya",
    "kamedia": "😂 Komediya",
    "kamediya": "😂 Komediya",
    "комедия": "😂 Komediya",
    "fantastika": "🚀 Fantastika",
    "fantastik": "🚀 Fantastika",
    "fentezi": "🚀 Fantastika",
    "fantasy": "🚀 Fantastika",
    "фантастика": "🚀 Fantastika",
    "фэнтези": "🚀 Fantastika",
    "sci-fi": "🚀 Fantastika",
    "komiks": "🚀 Fantastika",
    "sehrgarlik": "🚀 Fantastika",
    "ujas": "👻 Qo'rqinchli",
    "ужасы": "👻 Qo'rqinchli",
    "qo'rqinchli": "👻 Qo'rqinchli",
    "qorqinchli": "👻 Qo'rqinchli",
    "dahshat": "👻 Qo'rqinchli",
    "daxshat": "👻 Qo'rqinchli",
    "triller": "👻 Qo'rqinchli",
    "триллер": "👻 Qo'rqinchli",
    "xorror": "👻 Qo'rqinchli",
    "horror": "👻 Qo'rqinchli",
    "drama": "💔 Drama",
    "dramma": "💔 Drama",
    "драма": "💔 Drama",
    "detektiv": "🕵️ Detektiv",
    "детектив": "🕵️ Detektiv",
    "kriminal": "🕵️ Detektiv",
    "криминал": "🕵️ Detektiv",
    "jinoyat": "🕵️ Detektiv",
    "anime": "🎌 Anime",
    "multfilm": "🧸 Multfilm",
    "multik": "🧸 Multfilm",
    "animatsiya": "🧸 Multfilm",
    "realisticanimation": "🧸 Multfilm",
    "oilaviy": "🧸 Multfilm",
    "tarixiy": "⚔️ Tarixiy",
    "biografik": "⚔️ Tarixiy",
    "hayotiy": "⚔️ Tarixiy",
    "harbiy": "⚔️ Tarixiy",
    "milliy": "🇺🇿 Milliy",
    "o'zbek": "🇺🇿 Milliy",
    "hujjatli": "🌍 Hujjatli",
    "melodrama": "❤️ Melodrama",
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
    """Davlat nomlarini chiroyli o'zbekcha standartga keltirish."""
    if not raw_country:
        return "AQSH"
    c = re.sub(r"[#🌐🌍🌎🌏🇺🇸🇷🇺🇺🇿➺➤➢▪️▫️]", "", raw_country).strip(" -:,.")
    replacements = [
        (r"\bСША\b", "AQSH"),
        (r"\bAmerika\b", "AQSH"),
        (r"\bUSA\b", "AQSH"),
        (r"\bRussia\b", "Rossiya"),
        (r"\bCCCR\b", "Rossiya"),
        (r"\bSSSR\b", "Rossiya"),
        (r"\bUzbekistan\b", "O'zbekiston"),
        (r"\bO`zbekiston\b", "O'zbekiston"),
        (r"\bIndoneyziya\b", "Indoneziya"),
        (r"\bQirg'iz\b", "Qirg'iziston"),
        (r"\bfilmi\b", ""),
    ]
    for pat, rep in replacements:
        c = re.sub(pat, rep, c, flags=re.IGNORECASE)
    c = re.sub(r"\s+", " ", c).strip(" -:,.")
    return c if c else "AQSH"


def normalize_genres(raw_genre: str, movie_name: str = "") -> str:
    """Imlo xatoli janrlarni (masalan 'Komedia, Jngari' yoki 'Fantastik, Ujas') chiroyli standart janrga o'giradi."""
    text = f"{raw_genre} {movie_name}".lower()
    matched = []
    for k, clean_val in GENRE_CORRECTIONS.items():
        if k in text and clean_val not in matched:
            matched.append(clean_val)
    if matched:
        return ", ".join(matched[:3])
    clean_raw = re.sub(r"^[\W_]+", "", (raw_genre or "").strip())
    return clean_raw if clean_raw else "🔥 Jangari"


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

    # SERIAL VA QISM RAQAMINI ANIQLASH
    bt_info = extract_base_title_and_part(name, raw_caption=raw_text, file_name=file_name)
    is_serial = bt_info["is_serial"]
    part_num = bt_info["part_num"]
    base_title = bt_info["base_title"]
    episode_num = part_num
    base_name = base_title if is_serial else name

    genre = normalize_genres(raw_genre, base_name)
    extra_caption = fix_uzbek_typos(" ".join(extra_lines))

    return {
        "name": base_name,
        "base_title": base_title,
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
    Kino faqat nomi yozilganda TMDB API orqali uning aniq Yili, Davlati va Janrini
    topib beruvchi yordamchi funksiya (rasm qo'shmaydi, faqat aniq ma'lumotlarni oladi).
    """
    api_key = await db.get_setting("tmdb_api_key", config.TMDB_API_KEY)
    if not api_key or not name:
        return {}

    clean_title = re.sub(
        r"\b(?:\d+\s*[-–]?\s*(?:qism|seriya|epizod|fasl|sezon)|o['`‘ʻ]?zbek\s*tilida|uzbek\s*tilida|full\s*hd|1080p|720p|4k|premyera|kino|serial)\b",
        "",
        name,
        flags=re.IGNORECASE
    )
    clean_title = re.sub(r"\s+", " ", clean_title).strip(" -–:,.()[]")
    if not clean_title:
        clean_title = name.strip()

    endpoint = "search/tv" if is_serial else "search/movie"
    timeout = aiohttp.ClientTimeout(total=8)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            ru_title = await _translate_query(session, clean_title, "ru")
            en_title = await _translate_query(session, clean_title, "en")

            queries = []
            for q in [clean_title, en_title, ru_title]:
                if q and q not in queries:
                    queries.append(q)

            for q in queries:
                url = f"https://api.themoviedb.org/3/{endpoint}"
                params = {
                    "api_key": api_key,
                    "query": q,
                    "language": "ru-RU",
                    "include_adult": "false"
                }
                if year and re.match(r"^(19\d{2}|20\d{2})$", str(year)):
                    params["year" if endpoint == "search/movie" else "first_air_date_year"] = str(year)

                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results") or []
                        # Faqat nomi haqiqatan mos keladigan natijani qabul qilamiz (noto'g'ri kino ilinib qolmasligi uchun)
                        top = None
                        for cand in results[:6]:
                            cand_titles = [
                                cand.get("title"), cand.get("original_title"),
                                cand.get("name"), cand.get("original_name")
                            ]
                            if any(ct and any(_titles_similar(qv, ct) for qv in queries) for ct in cand_titles):
                                top = cand
                                break
                        if top:
                            rel_date = top.get("release_date") or top.get("first_air_date") or ""
                            found_year = rel_date[:4] if len(rel_date) >= 4 else ""

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
    except Exception as e:
        logging.debug(f"TMDB metadata lookup xatosi ({name}): {e}")
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
    "bravo jamoasi 2024 yilgi konsert dasturi": ("Kevin Hart: Reality Check", "2023", False),
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
}


def extract_base_title_and_part(name: str, raw_caption: str = "", file_name: str = "") -> dict:
    """
    Kino yoki serial nomidan:
    - is_serial: 1 (agar serial bo'lsa, masalan Afsungar Merlin, Envel Qahramonlari) yoki 0 (kino)
    - base_title: Guruhlash uchun asosiy kino/serial nomi (masalan: 'Mumiyo', 'Garri Potter', 'Labirintdagilar')
    - part_num: Qism tartib raqami (1, 2, 3...)
    """
    raw_n = (name or "").strip()
    norm_n = _norm_title(raw_n)
    blob = _norm_title(f"{raw_n} {raw_caption} {file_name}")

    # 1. Haqiqiy seriallarni aniqlash
    if "afsungar merlin" in norm_n or "afsungar merlin" in blob:
        ep_m = re.search(r"\b(\d{1,3})\s*[-–]?\s*qism", raw_n, flags=re.IGNORECASE) or re.search(r"\b(\d{1,3})\s*[-–]?\s*qism", raw_caption, flags=re.IGNORECASE)
        pnum = int(ep_m.group(1)) if ep_m else 1
        return {"is_serial": 1, "base_title": "Afsungar Merlin", "part_num": pnum}

    if "envel qahramonlari" in norm_n or "envel qahramonlari" in blob:
        ep_m = re.search(r"\b(\d{1,3})\s*[-–]?\s*qism", raw_n, flags=re.IGNORECASE) or re.search(r"\b(\d{1,3})\s*[-–]?\s*qism", raw_caption, flags=re.IGNORECASE)
        pnum = int(ep_m.group(1)) if ep_m else 1
        return {"is_serial": 1, "base_title": "Envel Qahramonlari", "part_num": pnum}

    if "iztopar" in norm_n or "iztopar" in blob:
        ep_m = (
            re.search(r"\d+F\d+Q(\d+)Q", file_name) or
            re.search(r"\d+F(\d+)Q", file_name) or
            re.search(r"[sS]\d+[eE](\d+)", file_name) or
            re.search(r"\b(\d{1,3})\s*[-–]?\s*qism", raw_n, flags=re.IGNORECASE) or
            re.search(r"(?:qism|seriya|epizod)[\s:=-]*(\d+)", raw_caption, flags=re.IGNORECASE) or
            re.search(r"(\d+)\s*[-–]?\s*qism", raw_caption, flags=re.IGNORECASE)
        )
        pnum = int(ep_m.group(1)) if ep_m else 1
        return {"is_serial": 1, "base_title": "Iztopar Afsonasi", "part_num": pnum}

    if any(k in norm_n or k in blob for k in ["serial", "seriya", "fasl", "sezon"]):
        ep_m = (
            re.search(r"\d+F\d+Q(\d+)Q", file_name) or
            re.search(r"\d+F(\d+)Q", file_name) or
            re.search(r"[sS]\d+[eE](\d+)", file_name) or
            re.search(r"\b(\d{1,3})\s*[-–]?\s*(?:qism|seriya|epizod)", raw_n, flags=re.IGNORECASE) or
            re.search(r"(?:qism|seriya|epizod)[\s:=-]*(\d+)", raw_caption, flags=re.IGNORECASE) or
            re.search(r"(\d+)\s*[-–]?\s*(?:qism|seriya|epizod)", raw_caption, flags=re.IGNORECASE)
        )
        pnum = int(ep_m.group(1)) if ep_m else 1
        btitle = raw_n
        btitle = re.sub(r"^[\W_]*serial[\W_:]*", "", btitle, flags=re.IGNORECASE).strip()
        btitle = re.sub(r"\b\d{1,3}\s*[-–]?\s*(?:qism|seriya|epizod).*$", "", btitle, flags=re.IGNORECASE).strip(" -–:,.")
        btitle = re.sub(r"^[^\w\s]+", "", btitle).strip()
        return {"is_serial": 1, "base_title": btitle or raw_n, "part_num": pnum}

    # 2. Ko'p qismli mashhur kinolar franshizalarini yagona base_title ostida va to'g'ri 1, 2, 3... tartibda birlashtirish
    if "predator" in norm_n and "xishnik" in norm_n:
        pm = re.search(r"\b([1-9])\s*[-–]?\s*qism", raw_n, flags=re.IGNORECASE)
        return {"is_serial": 0, "base_title": "Predator & Xishnik", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("yomon yigitlar"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Yomon yigitlar", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("mumiya") or norm_n.startswith("mumiyo"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Mumiyo", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("sonic"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Sonic", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("krid"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Krid", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("padington"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Padington", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("garri potter"):
        if "7.1" in raw_n or "7 1" in norm_n:
            pnum = 7
        elif "7.2" in raw_n or "7 2" in norm_n:
            pnum = 8
        else:
            pm = re.search(r"\b([1-8])\b", norm_n)
            pnum = int(pm.group(1)) if pm else 1
        return {"is_serial": 0, "base_title": "Garri Potter", "part_num": pnum}

    if norm_n.startswith("jumanji"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Jumanji", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("ilon hamlasi"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Ilon Hamlasi", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("malikaning kundaligi"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Malikaning kundaligi", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("shahzoda va bori"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Shahzoda va Bo'ri", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("beethoven"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Beethoven", "part_num": int(pm.group(1)) if pm else 1}

    if "masxaraboz" in norm_n and "penni vays" in norm_n:
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Masxaraboz ONO Penni Vays", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("chaqmoq makvin"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Chaqmoq Makvin", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("lara kroft"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Lara Kroft: Dahma talonchisi", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("ip man"):
        if "afsonaning" in norm_n:
            pnum = 4
        else:
            pm = re.search(r"\b([1-9])\b", norm_n)
            pnum = int(pm.group(1)) if pm else 1
        return {"is_serial": 0, "base_title": "Ip Man", "part_num": pnum}

    if norm_n.startswith("polat alximik"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Po'lat alximik", "part_num": int(pm.group(1)) if pm else 1}

    if norm_n.startswith("snayper"):
        if "songgi jang" in norm_n:
            pnum = 9
        else:
            pm = re.search(r"\b([1-9])\b", norm_n)
            pnum = int(pm.group(1)) if pm else 1
        return {"is_serial": 0, "base_title": "Snayper", "part_num": pnum}

    if norm_n.startswith("jodu saltanati"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Jodu saltanati", "part_num": int(pm.group(1)) if pm else 1}

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
        return {"is_serial": 0, "base_title": "O'rgimchak odam", "part_num": pnum}

    if norm_n.startswith("labirintdagilar"):
        pm = re.search(r"\b([1-9])\b", norm_n)
        return {"is_serial": 0, "base_title": "Labirintdagilar", "part_num": int(pm.group(1)) if pm else 1}

    # Umumiy X-qism yozilgan kinolar
    gen_m = re.search(r"^(.*?)\s+(\d)\s*[-–]?\s*qism$", raw_n, flags=re.IGNORECASE)
    if gen_m and len(gen_m.group(1).strip()) >= 3:
        return {"is_serial": 0, "base_title": gen_m.group(1).strip(" -–:,"), "part_num": int(gen_m.group(2))}

    return {"is_serial": 0, "base_title": raw_n, "part_num": 1}


async def _tmdb_search_request(
    session: aiohttp.ClientSession,
    endpoint: str,
    query: str,
    year: str = "",
    lang: str = "ru-RU",
    api_key: str = "",
    read_token: str = "",
    require_similarity: bool = False
) -> str:
    """TMDB API ga so'rov yuborib poster_path yoki backdrop_path qaytaradi."""
    if not query or len(query.strip()) < 2:
        return ""
    url = f"https://api.themoviedb.org/3/{endpoint}"
    params = {
        "api_key": api_key,
        "query": query.strip(),
        "language": lang,
        "include_adult": "false"
    }
    if year and re.match(r"^(19\d{2}|20\d{2})$", str(year).strip()):
        if endpoint == "search/movie":
            params["year"] = str(year).strip()
        elif endpoint == "search/tv":
            params["first_air_date_year"] = str(year).strip()

    headers = {"Accept": "application/json"}
    if read_token:
        headers["Authorization"] = f"Bearer {read_token}"

    try:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results") or []
                for item in results:
                    if require_similarity:
                        cand_titles = [
                            item.get("title"),
                            item.get("original_title"),
                            item.get("name"),
                            item.get("original_name")
                        ]
                        if not any(ct and _titles_similar(query, ct) for ct in cand_titles):
                            continue
                    poster = item.get("poster_path") or item.get("backdrop_path")
                    if poster:
                        return f"https://image.tmdb.org/t/p/w780{poster}"
    except Exception as e:
        logging.debug(f"TMDB qidiruv xatosi ({query}): {e}")
    return ""


_TMDB_POSTER_CACHE: dict = {}

async def find_movie_poster_tmdb(name: str, year: str = "", is_serial: bool = False, force: bool = False) -> str:
    """
    Kino yoki serial nomiga qarab TheMovieDB (themoviedb.org) API orqali
    rasmiy HD Poster (rasm) URL manzilini 100% aniqlik bilan topib qaytaradi!
    1-rasmdagi TMDB API Key va Read Access Token orqali ishlaydi.
    """
    if not force and await db.get_setting("tmdb_auto_poster", "1") != "1":
        return ""
    norm_n = _norm_title(name)
    cache_key = f"{norm_n}:{year}:{int(is_serial)}"
    if cache_key in _TMDB_POSTER_CACHE:
        return _TMDB_POSTER_CACHE[cache_key]

    api_key = await db.get_setting("tmdb_api_key", config.TMDB_API_KEY)
    read_token = await db.get_setting("tmdb_read_token", config.TMDB_READ_TOKEN)
    if not api_key and not read_token:
        return ""

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # 1. EXACT_TMDB_SEARCH_MAP orqali 100% aniq kino posterini olish
        exact_entry = EXACT_TMDB_SEARCH_MAP.get(norm_n)
        if not exact_entry:
            for k_norm, val_tuple in EXACT_TMDB_SEARCH_MAP.items():
                if k_norm in norm_n or norm_n in k_norm:
                    exact_entry = val_tuple
                    break

        if exact_entry:
            ex_query, ex_year, ex_is_tv = exact_entry
            ex_endpoint = "search/tv" if (ex_is_tv or is_serial) else "search/movie"
            use_year = ex_year or str(year or "").strip()
            for lg in ("ru-RU", "en-US"):
                if use_year:
                    poster = await _tmdb_search_request(
                        session, ex_endpoint, ex_query, year=use_year, lang=lg, api_key=api_key, read_token=read_token
                    )
                    if poster:
                        _TMDB_POSTER_CACHE[cache_key] = poster
                        return poster
                poster = await _tmdb_search_request(
                    session, ex_endpoint, ex_query, year="", lang=lg, api_key=api_key, read_token=read_token
                )
                if poster:
                    _TMDB_POSTER_CACHE[cache_key] = poster
                    return poster

        endpoint = "search/tv" if is_serial else "search/movie"
        target_year = str(year or "").strip()
        known = _find_exact_known(name)
        if known and not target_year:
            target_year = str(known.get("year", "")).strip()

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

        # 2. Tarjima va toza nom bo'yicha qidirish
        ru_title = await _translate_query(session, clean_title, "ru")
        en_title = await _translate_query(session, clean_title, "en")

        candidates = []
        for q, lg in [(en_title, "en-US"), (ru_title, "ru-RU"), (clean_title, "ru-RU"), (clean_title, "en-US")]:
            if q and (q, lg) not in candidates:
                candidates.append((q, lg))

        if target_year:
            for q, lg in candidates:
                poster = await _tmdb_search_request(
                    session, endpoint, q, year=target_year, lang=lg, api_key=api_key, read_token=read_token
                )
                if poster:
                    _TMDB_POSTER_CACHE[cache_key] = poster
                    return poster

        for q, lg in candidates:
            poster = await _tmdb_search_request(
                session, endpoint, q, year="", lang=lg, api_key=api_key, read_token=read_token, require_similarity=True
            )
            if poster:
                _TMDB_POSTER_CACHE[cache_key] = poster
                return poster

        for q, lg in candidates[:2]:
            poster = await _tmdb_search_request(
                session, "search/multi", q, year="", lang=lg, api_key=api_key, read_token=read_token
            )
            if poster:
                _TMDB_POSTER_CACHE[cache_key] = poster
                return poster

    return ""
