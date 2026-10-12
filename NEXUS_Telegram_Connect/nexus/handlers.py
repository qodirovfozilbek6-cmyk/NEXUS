
import logging
import os
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from nexus.config import settings

from nexus.db import (
    upsert_user,
    get_user,
    get_world_stats,
    collect_crystals,
    COOLDOWN_SECONDS,
)


router = Router()
logger = logging.getLogger(__name__)

# Asoschining Telegram ID raqami .env ichida saqlanadi.
OWNER_ID = int(os.getenv("NEXUS_OWNER_ID", "0") or "0")


# 10 ta daraja — HTML interfeys bilan mos.
LEVELS = [
    (0, "Novice", "🌱"),
    (100, "Explorer", "🔭"),
    (300, "Apprentice", "📘"),
    (600, "Warrior", "⚔️"),
    (1000, "Elite", "🛡️"),
    (1600, "Master", "🧠"),
    (2400, "Champion", "🏆"),
    (3400, "Legend", "👑"),
    (4600, "Mythic", "🌌"),
    (6000, "Supreme", "💫"),
]


def format_remaining(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours} soat {minutes} daqiqa"
    if minutes:
        return f"{minutes} daqiqa {secs} soniya"
    return f"{secs} soniya"


def get_level(crystals: int):
    current_level = LEVELS[0]
    next_level = None

    for level in LEVELS:
        if crystals >= level[0]:
            current_level = level
        else:
            next_level = level
            break

    return current_level, next_level


@router.message(Command("start"))
async def start_handler(message: Message):
    telegram_user = message.from_user

    if telegram_user is None:
        return

    user_data = {
        "id": telegram_user.id,
        "username": telegram_user.username,
        "first_name": telegram_user.first_name or "",
    }

    try:
        await upsert_user(user_data)
    except Exception:
        logger.exception("Foydalanuvchini saqlashda xato")
        await message.answer(
            "⚠️ Ma'lumotlarni saqlashda xato yuz berdi."
        )
        return

    if telegram_user.id == OWNER_ID and OWNER_ID != 0:
        greeting = (
            "👑 NEXUS YARATUVCHISI, xush kelibsan!\n"
            "Bu olam sening loyihang!"
        )
    else:
        greeting = (
            "🌌 NEXUS olamiga xush kelibsan, "
            f"{telegram_user.first_name or 'sayohatchi'}!"
        )

    keyboard = None
    if settings.WEBAPP_URL.startswith("https://"):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="🚀 NEXUS Mini App'ni ochish",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]]
        )

    await message.answer(
        f"{greeting}\n\n"
        "Sening kosmik sarguzashting shu yerdan boshlanadi.\n\n"
        "👤 /profile — profiling\n"
        "💎 /collect — har 30 daqiqada 10 kristal\n"
        "🌍 /world — olam statistikasi\n"
        "📖 /help — yordam",
        reply_markup=keyboard,
    )


@router.message(Command("profile"))
async def profile_handler(message: Message):
    telegram_user = message.from_user

    if telegram_user is None:
        return

    try:
        user = await get_user(telegram_user.id)
    except Exception:
        logger.exception("Profilni olishda xato")
        await message.answer(
            "⚠️ Profilni yuklashda xato yuz berdi."
        )
        return

    if user is None:
        await message.answer("Avval /start yubor.")
        return

    crystals = int(user["crystals"])
    current_level, next_level = get_level(crystals)

    is_owner = (
        telegram_user.id == OWNER_ID
        and OWNER_ID != 0
    )

    if is_owner:
        rank_text = "👑 NEXUS YARATUVCHISI"
        progress_text = "🏆 Sen ushbu olamning asoschisisan!"
    else:
        rank_text = (
            f"{current_level[2]} "
            f"Level {LEVELS.index(current_level) + 1}"
            f" — {current_level[1]}"
        )

        if next_level:
            needed = next_level[0] - crystals
            progress_text = (
                f"🎯 Keyingi daraja: {next_level[1]}\n"
                f"💠 Yana {needed} kristal kerak"
            )
        else:
            progress_text = (
                "🏆 Sen eng yuqori darajaga yetding!"
            )

    last_collect = int(user["last_collect_at"])
    now = int(time.time())

    if last_collect == 0:
        collect_status = (
            "Hozir kristal yig'ishing mumkin 💎"
        )
    else:
        remaining = last_collect + COOLDOWN_SECONDS - now

        if remaining <= 0:
            collect_status = "Kristal yig'ishga tayyor 💎"
        else:
            collect_status = (
                "Keyingi yig'ishgacha: "
                f"{format_remaining(remaining)}"
            )

    await message.answer(
        "👤 NEXUS PROFILI\n\n"
        f"🪪 Ism: {user['first_name'] or 'Noma’lum'}\n"
        f"🆔 Telegram ID: {user['telegram_id']}\n"
        f"💎 Kristallar: {crystals}\n"
        f"🏅 Daraja: {rank_text}\n"
        f"{progress_text}\n\n"
        f"⏱️ {collect_status}\n"
        f"📅 Ro'yxatdan o'tgan: {user['created_at']}"
    )


@router.message(Command("collect"))
async def collect_handler(message: Message):
    telegram_user = message.from_user

    if telegram_user is None:
        return

    try:
        result = await collect_crystals(telegram_user.id)
    except Exception:
        logger.exception("Kristal yig'ishda xato")
        await message.answer(
            "⚠️ Kristallarni hisoblashda xato yuz berdi."
        )
        return

    if result["status"] == "not_registered":
        await message.answer("Avval /start yubor.")
        return

    if result["status"] == "cooldown":
        await message.answer(
            "⏳ Kristalni allaqachon yig'gansan!\n\n"
            "Keyingi yig'ishgacha: "
            f"{format_remaining(result['remaining'])}\n"
            f"💎 Joriy balans: {result['crystals']}"
        )
        return

    crystals = result["crystals"]
    level, _ = get_level(crystals)

    is_owner = (
        telegram_user.id == OWNER_ID
        and OWNER_ID != 0
    )

    rank_text = (
        "👑 NEXUS YARATUVCHISI"
        if is_owner
        else f"{level[2]} {level[1]}"
    )

    await message.answer(
        "💎 KRISTAL MUVAFFAQIYATLI YIG'ILDI!\n\n"
        f"➕ Mukofot: +{result['reward']} kristal\n"
        f"💰 Joriy balans: {crystals} kristal\n"
        f"🏅 Darajang: {rank_text}\n\n"
        "⏱️ Keyingi yig'ish 30 daqiqadan keyin.\n"
        "Omad, sayohatchi! 🚀"
    )


@router.message(Command("world"))
async def world_handler(message: Message):
    try:
        stats = await get_world_stats()
    except Exception:
        logger.exception("Olam statistikasida xato")
        await message.answer(
            "⚠️ Statistika hozircha mavjud emas."
        )
        return

    await message.answer(
        "🌍 NEXUS OLAMI\n\n"
        f"👥 Sayohatchilar: {stats['players']}\n"
        f"💎 Jami kristallar: {stats['crystals']}\n\n"
        "Yangi sayohatchilarni kutamiz! 🚀"
    )


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "📖 NEXUS — YORDAM\n\n"
        "/start — NEXUS'ni boshlash\n"
        "/profile — shaxsiy profiling\n"
        "/collect — har 30 daqiqada 10 kristal\n"
        "/world — olam statistikasi\n"
        "/help — buyruqlar ro'yxati"
    )


@router.message()
async def unknown_message_handler(message: Message):
    await message.answer(
        "🌌 Bu xabar uchun hali funksiya yo'q.\n"
        "Buyruqlarni ko'rish uchun /help ni yubor."
    )