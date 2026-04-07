"""
Simple localization module supporting English (en), Uzbek (uz), and Russian (ru).
Language preference is stored in Redis per user.
"""
from __future__ import annotations

from backend.app.core.redis_client import get_redis
from backend.app.core.logging_config import get_logger

logger = get_logger(__name__)

LANG_KEY_PREFIX = "lang:"
DEFAULT_LANG = "en"
SUPPORTED_LANGS = {"en", "uz", "ru"}

_STRINGS: dict[str, dict[str, str]] = {
    # ── Welcome & Start ────────────────────────────────────────────────────
    "welcome": {
        "en": (
            "👋 <b>Welcome to LingoGenBot!</b>\n\n"
            "Practice languages with real people — <b>anonymously</b>.\n\n"
            "🗣 Matched randomly with a partner\n"
            "🎯 Each session has a random topic\n"
            "⏱ Sessions last 5 minutes\n"
            "⭐️ Rate your partner at the end\n"
            "🏆 Earn XP, achievements, and climb the leaderboard!\n\n"
            "<b>Tap 🔍 Find Partner to begin!</b>"
        ),
        "uz": (
            "👋 <b>LingoGenBot'ga xush kelibsiz!</b>\n\n"
            "Haqiqiy odamlar bilan til mashq qiling — <b>anonim</b>.\n\n"
            "🗣 Tasodifiy sherik bilan ulanish\n"
            "🎯 Har bir sessiyada tasodifiy mavzu\n"
            "⏱ Sessiya 5 daqiqa davom etadi\n"
            "⭐️ Oxirida sherikingizni baholang\n"
            "🏆 XP va yutuqlar yig'ing!\n\n"
            "<b>Boshlash uchun 🔍 Sherik topish tugmasini bosing!</b>"
        ),
        "ru": (
            "👋 <b>Добро пожаловать в LingoGenBot!</b>\n\n"
            "Практикуйте языки с реальными людьми — <b>анонимно</b>.\n\n"
            "🗣 Случайный подбор партнёра\n"
            "🎯 Случайная тема для каждой сессии\n"
            "⏱ Сессия длится 5 минут\n"
            "⭐️ Оцените партнёра в конце\n"
            "🏆 Зарабатывайте XP и достижения!\n\n"
            "<b>Нажмите 🔍 Найти партнёра, чтобы начать!</b>"
        ),
    },
    "language_set": {
        "en": "✅ Language changed to <b>English</b>.",
        "uz": "✅ Til <b>O'zbek</b> tiliga o'zgartirildi.",
        "ru": "✅ Язык изменён на <b>Русский</b>.",
    },
    "choose_language": {
        "en": "🌐 <b>Choose your language / Tilni tanlang / Выберите язык:</b>",
        "uz": "🌐 <b>Tilni tanlang / Choose your language / Выберите язык:</b>",
        "ru": "🌐 <b>Выберите язык / Choose your language / Tilni tanlang:</b>",
    },
    # ── Messages ────────────────────────────────────────────────────────────
    "no_messages": {
        "en": (
            "📭 <b>No messages yet</b>\n\n"
            "Share your profile link to receive anonymous messages!\n"
            "Use /profile to get your link."
        ),
        "uz": (
            "📭 <b>Hali xabar yo'q</b>\n\n"
            "Anonim xabarlar olish uchun profilingiz havolasini ulashing!\n"
            "Havolani olish uchun /profile dan foydalaning."
        ),
        "ru": (
            "📭 <b>Пока нет сообщений</b>\n\n"
            "Поделитесь ссылкой на профиль, чтобы получать анонимные сообщения!\n"
            "Используйте /profile для получения ссылки."
        ),
    },
    "inbox_header": {
        "en": "📬 <b>Your Messages</b>",
        "uz": "📬 <b>Xabarlaringiz</b>",
        "ru": "📬 <b>Ваши сообщения</b>",
    },
    "mark_all_read_btn": {
        "en": "✅ Mark all read",
        "uz": "✅ Barchasini o'qildi deb belgilash",
        "ru": "✅ Отметить всё прочитанным",
    },
    "next_page_btn": {
        "en": "➡️ Next page",
        "uz": "➡️ Keyingi sahifa",
        "ru": "➡️ Следующая страница",
    },
    "reply_btn": {
        "en": "↩️ Reply to #{}",
        "uz": "↩️ #{} ga javob berish",
        "ru": "↩️ Ответить на #{}",
    },
    "all_marked_read": {
        "en": "✅ All messages marked as read!",
        "uz": "✅ Barcha xabarlar o'qildi deb belgilandi!",
        "ru": "✅ Все сообщения отмечены как прочитанные!",
    },
    "no_more_messages": {
        "en": "No more messages!",
        "uz": "Boshqa xabar yo'q!",
        "ru": "Больше сообщений нет!",
    },
    # ── Session ─────────────────────────────────────────────────────────────
    "session_ended_rate": {
        "en": "🏁 <b>Session ended!</b>\n\nHow was your partner? Please rate the session:",
        "uz": "🏁 <b>Sessiya tugadi!</b>\n\nSherikingiz qanday edi? Iltimos, sessiyani baholang:",
        "ru": "🏁 <b>Сессия завершена!</b>\n\nКак вам партнёр? Пожалуйста, оцените сессию:",
    },
    "partner_ended_rate": {
        "en": "🏁 <b>Your partner has ended the session.</b>\n\nHow was your experience? Please rate:",
        "uz": "🏁 <b>Sherikingiz sessiyani tugatdi.</b>\n\nTajribangiz qanday edi? Baholang:",
        "ru": "🏁 <b>Ваш партнёр завершил сессию.</b>\n\nКак вам опыт? Пожалуйста, оцените:",
    },
    "rating_thanks": {
        "en": "✅ <b>Thanks for rating!</b>\n\nYou gave: {} ({}/5)\n\nPress <b>🔍 Find Partner</b> to start a new session!",
        "uz": "✅ <b>Baholaginiz uchun rahmat!</b>\n\nSiz berdingiz: {} ({}/5)\n\n<b>🔍 Sherik topish</b> tugmasini bosing!",
        "ru": "✅ <b>Спасибо за оценку!</b>\n\nВы поставили: {} ({}/5)\n\nНажмите <b>🔍 Найти партнёра</b>!",
    },
    "not_in_session": {
        "en": "💬 <b>You are not in a session.</b>\nPress <b>🔍 Find Partner</b> to get matched!",
        "uz": "💬 <b>Siz sessiyada emassiz.</b>\nUlanish uchun <b>🔍 Sherik topish</b> tugmasini bosing!",
        "ru": "💬 <b>Вы не в сессии.</b>\nНажмите <b>🔍 Найти партнёра</b>, чтобы найти собеседника!",
    },
    # ── Stats ───────────────────────────────────────────────────────────────
    "stats_header": {
        "en": "📊 <b>Your Statistics</b>",
        "uz": "📊 <b>Statistikangiz</b>",
        "ru": "📊 <b>Ваша статистика</b>",
    },
    # ── Language picker keyboard labels ─────────────────────────────────────
    "lang_en_btn": {"en": "🇬🇧 English", "uz": "🇬🇧 Inglizcha", "ru": "🇬🇧 Английский"},
    "lang_uz_btn": {"en": "🇺🇿 Uzbek", "uz": "🇺🇿 O'zbek", "ru": "🇺🇿 Узбекский"},
    "lang_ru_btn": {"en": "🇷🇺 Russian", "uz": "🇷🇺 Ruscha", "ru": "🇷🇺 Русский"},
}


async def get_user_lang(user_id: int) -> str:
    """Retrieve the stored language for a user from Redis. Defaults to 'en'."""
    try:
        r = await get_redis()
        lang = await r.get(f"{LANG_KEY_PREFIX}{user_id}")
        return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    except Exception:
        return DEFAULT_LANG


async def set_user_lang(user_id: int, lang: str) -> None:
    """Persist the user's language preference to Redis."""
    if lang not in SUPPORTED_LANGS:
        return
    try:
        r = await get_redis()
        await r.set(f"{LANG_KEY_PREFIX}{user_id}", lang, ex=60 * 60 * 24 * 365)
    except Exception as e:
        logger.warning(f"Could not save language preference for {user_id}: {e}")


def t(key: str, lang: str, *args: object) -> str:
    """Translate a key to the given language, formatting with positional args."""
    translations = _STRINGS.get(key, {})
    text = translations.get(lang) or translations.get(DEFAULT_LANG) or key
    if args:
        try:
            text = text.format(*args)
        except (IndexError, KeyError):
            pass
    return text
