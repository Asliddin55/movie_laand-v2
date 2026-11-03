import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMINS_RAW = os.getenv("ADMINS", "")

ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_RAW.replace(",", " ").split() if admin_id.strip().isdigit()]

# Boshlang'ich Super Admin paroli
DEFAULT_SUPER_ADMIN_PASSWORD = os.getenv("ADMIN_SECRET_CODE", "asliddin29092006")

# Rasmiy Arxiv Kanal va Asosiy Post Kanali
DEFAULT_ARCHIVE_CHANNEL_ID = "-1003124847141"
DEFAULT_POST_CHANNEL_ID = "@movieee_land"
DEFAULT_POST_CHANNEL_CHAT_ID = "-1003536154725"
DEFAULT_POST_CHANNEL_LINK = "https://t.me/movieee_land"

# Yagona Rasmiy Mavzuli Guruh (Forum) va uning Topic (Bo'lim) ID raqamlari
MAIN_TOPIC_GROUP_ID = "-1002748514315"
MAIN_TOPIC_GROUP_USERNAME = "movieeland_group"
MAIN_TOPIC_GROUP_LINK = "https://t.me/movieeland_group"

TOPIC_PREMIUM_REVIEWS_ID = 190   # 💸 Premium (Otzivlar / Fikrlar)
TOPIC_ORDERS_ID = 193            # ⭐ Задавленный Buyurtmalar
TOPIC_CHAT_ID = 194              # 👑 Чат Muhokama
TOPIC_RULES_ID = 195             # 💎 Правила Qoidalar
TOPIC_ACTIVITY_ID = 196          # ⚡ Активный Faolik (Yangi userlar, VIP xaridlar, To'lov cheklari)

# TheMovieDB (TMDB) API Sozlamalari (Kinolar rasmini avtomatik topish uchun)
TMDB_API_KEY = "7980df6df706978740c974e3ff364ad9"
TMDB_READ_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI3OTgwZGY2ZGY3MDY5Nzg3NDBjOTc0ZTNmZjM2NGFkOSIsInN1YiI6IjY4ZTNkZmRlZmQ2YWRkMzMwNyN2Yi1sInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.UBmZ72TfWVHhp6P9Ob2i1P_OMSMP456KrOJY4yQDI04"

# Iqtisodiyot: Kunlik Bonus, Referal va Premium Narxlari (so'mda — Super Admin paneldan o'zgartiriladi)
DEFAULT_DAILY_REWARD = "1000"
DEFAULT_REF_REWARD = "1500"
DEFAULT_VIP_7_PRICE = "10000"
DEFAULT_VIP_30_PRICE = "25000"
DEFAULT_VIP_90_PRICE = "60000"
DEFAULT_PAYMENT_CARD = "8600 0000 0000 0000 (Admin orqali tasdiqlanadi)"

# Premium foydalanuvchilar uchun maxsus Teglar (Mavzuli kanal/guruhlarda va botda)
VIP_CUSTOM_TAGS = [
    "PREMIUM",
    "VIP KING",
    "KINOQIROL",
    "SPONSOR",
    "LEGEND",
    "MOVIE VIP"
]

GENRES = [
    "🔥 Jangari", "😂 Komediya", "🚀 Fantastika", "👻 Qo'rqinchli",
    "💔 Drama", "🕵️ Detektiv", "🎌 Anime", "🧸 Multfilm",
    "⚔️ Tarixiy", "🇺🇿 Milliy", "🌍 Hujjatli", "❤️ Melodrama"
]

# 3 bosqichli lavozimlar
ROLES = {
    "user": "👤 Oddiy foydalanuvchi",
    "moderator": "🛡 Moderator",
    "admin": "👮 Administrator",
    "superadmin": "👑 Super Administrator"
}

# Granular ruxsatlar
PERMISSIONS = {
    "archive_load": "📥 Bazadan (Arxivdan) Kino va Serial yuklash",
    "add_movie": "🎬 Kino va Serial qo'shish",
    "del_movie": "🗑 Kino o'chirish",
    "autopost": "📢 Kanalga Avto-Post chiqarish",
    "channels": "📡 Majburiy va Mavzuli kanallar",
    "orders": "📩 Kino buyurtmalarni qabul qilish / javob berish",
    "stats": "📊 Statistikani ko'rish",
    "broadcast": "✉️ Xabar tarqatish (Reklama)",
    "users_ban": "🚫 Userlarni qidirish va Ban/Unban",
    "vip_manage": "💎 Premium (VIP) va Balans boshqaruvi",
    "chatid": "🆔 /chatid buyrug'ini ishlatish (Guruh va Botda)"
}

DEFAULT_ROLE_PERMS = {
    "moderator": ["archive_load", "add_movie", "orders", "stats"],
    "admin": ["archive_load", "add_movie", "del_movie", "autopost", "channels", "orders", "stats", "broadcast", "users_ban", "vip_manage", "chatid"],
    "superadmin": list(PERMISSIONS.keys())
}

# TOP 15 KUCHLI AI PROVAYDERLAR RO'YXATI
TOP_15_AI_PROVIDERS = {
    "gemini": {
        "name": "1. Google Gemini 2.5 Pro / Flash",
        "model": "gemini-2.0-flash",
        "type": "gemini"
    },
    "openai": {
        "name": "2. OpenAI (ChatGPT-4o)",
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "type": "openai_compat"
    },
    "claude": {
        "name": "3. Anthropic Claude 3.5 Sonnet",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-3-5-sonnet-20241022",
        "type": "anthropic"
    },
    "deepseek": {
        "name": "4. DeepSeek AI (DeepSeek-V3)",
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "type": "openai_compat"
    },
    "grok": {
        "name": "5. xAI Grok (Grok-2 / Grok-3)",
        "url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-2-latest",
        "type": "openai_compat"
    },
    "groq": {
        "name": "6. Groq Cloud (Llama-3.3 70B Ultra)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "type": "openai_compat"
    },
    "mistral": {
        "name": "7. Mistral AI (Mistral Large)",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "model": "mistral-large-latest",
        "type": "openai_compat"
    },
    "perplexity": {
        "name": "8. Perplexity AI (Sonar Pro)",
        "url": "https://api.perplexity.ai/chat/completions",
        "model": "sonar-pro",
        "type": "openai_compat"
    },
    "cohere": {
        "name": "9. Cohere AI (Command R+)",
        "url": "https://api.cohere.com/v2/chat",
        "model": "command-r-plus",
        "type": "cohere"
    },
    "together": {
        "name": "10. Meta Llama 3.1 (Together AI)",
        "url": "https://api.together.xyz/v1/chat/completions",
        "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "type": "openai_compat"
    },
    "qwen": {
        "name": "11. Alibaba Qwen-2.5 Max",
        "url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-max",
        "type": "openai_compat"
    },
    "fireworks": {
        "name": "12. Fireworks AI (DeepSeek/Llama)",
        "url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "type": "openai_compat"
    },
    "openrouter": {
        "name": "13. OpenRouter (Universal AI)",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openai/gpt-4o-mini",
        "type": "openai_compat"
    },
    "cerebras": {
        "name": "14. Cerebras AI (Ultra-Fast Llama)",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "llama-3.3-70b",
        "type": "openai_compat"
    },
    "huggingface": {
        "name": "15. HuggingFace Inference API",
        "url": "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct/v1/chat/completions",
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "type": "openai_compat"
    }
}
