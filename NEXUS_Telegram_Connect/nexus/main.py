
import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager, suppress

from aiogram import Bot, Dispatcher
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from aiogram.types import MenuButtonWebApp, WebAppInfo

from nexus.config import BASE_DIR, settings
from nexus.db import (
    init_db,
    upsert_user,
    get_user,
    get_world_stats,
    collect_crystals,
    COOLDOWN_SECONDS,
)
from nexus.handlers import router
from nexus.security import (
    validate_init_data,
    validate_telegram_login,
    create_browser_session,
    validate_browser_session,
)


# ==========================================
# NEXUS CONFIGURATION
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("NEXUS")

OWNER_ID = int(os.getenv("NEXUS_OWNER_ID", "0") or "0")

# Mini App va Telegram botdagi darajalar bilan bir xil bo‘lishi kerak.
LEVELS = [
    (0, "Novice", "🌱"),
    (100, "Explorer", "🧭"),
    (300, "Apprentice", "🔮"),
    (600, "Warrior", "⚔️"),
    (1000, "Elite", "🔥"),
    (1600, "Master", "🏆"),
    (2400, "Champion", "🪽"),
    (3400, "Legend", "🌌"),
    (4600, "Mythic", "🜲"),
    (6000, "Supreme", "👑"),
]


# ==========================================
# LEVEL SYSTEM
# ==========================================

def get_level(crystals: int) -> dict:
    """Foydalanuvchining darajasi va keyingi bosqichini aniqlaydi."""

    current_level = LEVELS[0]
    next_level = None

    for index, level in enumerate(LEVELS):
        required, name, icon = level

        if crystals >= required:
            current_level = level

            if index + 1 < len(LEVELS):
                next_level = LEVELS[index + 1]
        else:
            break

    required, name, icon = current_level

    if next_level:
        next_required, next_name, next_icon = next_level
        progress = (
            (crystals - required)
            / (next_required - required)
            * 100
        )
        progress = max(0, min(100, progress))
    else:
        next_required = None
        next_name = None
        next_icon = None
        progress = 100

    return {
        "level": name,
        "level_icon": icon,
        "level_required": required,
        "next_level": next_name,
        "next_level_icon": next_icon,
        "next_level_required": next_required,
        "progress": round(progress, 2),
    }


# ==========================================
# TELEGRAM BOT + FASTAPI LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    bot = None
    polling_task = None

    if settings.BOT_TOKEN:
        bot = Bot(token=settings.BOT_TOKEN)

        # Telegram chat menyusiga Mini App tugmasini qo'shish.
        if settings.WEBAPP_URL.startswith("https://"):
            try:
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="🚀 NEXUS",
                        web_app=WebAppInfo(url=settings.WEBAPP_URL),
                    )
                )
                logger.info("Telegram Mini App menyu tugmasi sozlandi.")
            except Exception:
                logger.exception("Mini App menyu tugmasini sozlab bo'lmadi.")

        dp = Dispatcher()
        dp.include_router(router)

        app.state.bot = bot
        app.state.dp = dp

        polling_task = asyncio.create_task(
            dp.start_polling(bot)
        )

        logger.info("Telegram bot ishga tushdi.")
    else:
        logger.warning(
            "BOT_TOKEN topilmadi. Telegram bot ishga tushmadi."
        )

    logger.info("NEXUS server ishga tushdi.")

    try:
        yield
    finally:
        if polling_task:
            polling_task.cancel()

            with suppress(asyncio.CancelledError):
                await polling_task

        if bot:
            await bot.session.close()

        logger.info("NEXUS server to'xtatildi.")


app = FastAPI(
    title="NEXUS API",
    description="NEXUS Telegram bot va Mini App API",
    version="1.0.0",
    lifespan=lifespan,
)


# ==========================================
# BASIC ROUTES
# ==========================================

@app.get("/")
async def home():
    return {
        "project": "NEXUS",
        "status": "online",
        "message": "NEXUS server ishlayapti!",
        "mini_app": "/app/",
        "health": "/health",
        "api_docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "project": "NEXUS",
        "timestamp": int(time.time()),
    }


# ==========================================
# TELEGRAM MINI APP AUTHENTICATION
# ==========================================

async def authenticated_user(
    request: Request,
) -> dict:
    """
    Telegram Mini App initData ma'lumotlarini tekshiradi.
    Oddiy brauzer preview rejimi API orqali mukofot ololmaydi.
    """

    if not settings.BOT_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Bot token serverda sozlanmagan.",
        )

    # Telegram Mini App: Telegram imzosini tekshirish.
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if init_data:
        user = validate_init_data(
            init_data=init_data,
            bot_token=settings.BOT_TOKEN,
        )
        if user:
            try:
                telegram_id = int(user["id"])
            except (KeyError, TypeError, ValueError):
                user = None
            else:
                await upsert_user(user)
                return {**user, "id": telegram_id}

    # Oddiy brauzer: server imzolagan HttpOnly session cookie.
    session = validate_browser_session(
        request.cookies.get("nexus_session", ""),
        bot_token=settings.BOT_TOKEN,
    )
    if session:
        user = await get_user(int(session["id"]))
        if user:
            return {
                "id": int(user["telegram_id"]),
                "first_name": user.get("first_name", ""),
                "username": user.get("username"),
            }

    raise HTTPException(
        status_code=401,
        detail="Telegram bilan tizimga kirish kerak.",
    )


# ==========================================
# TELEGRAM LOGIN WIDGET (ORDINARY BROWSER)
# ==========================================

@app.post("/api/auth/telegram-login")
async def telegram_browser_login(request: Request):
    if not settings.BOT_TOKEN:
        raise HTTPException(status_code=503, detail="BOT_TOKEN serverda sozlanmagan.")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Login ma'lumotlari noto'g'ri.")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Login ma'lumotlari noto'g'ri.")

    user = validate_telegram_login(payload, settings.BOT_TOKEN)
    if not user:
        raise HTTPException(status_code=401, detail="Telegram login imzosi noto'g'ri yoki muddati o'tgan.")

    await upsert_user(user)
    session_token = create_browser_session(int(user["id"]), settings.BOT_TOKEN)
    response = JSONResponse({"ok": True})
    response.set_cookie(
        key="nexus_session",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@app.post("/api/auth/logout")
async def browser_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(key="nexus_session", path="/", secure=True, httponly=True, samesite="lax")
    return response


# ==========================================
# PROFILE API
# ==========================================

@app.get("/api/me")
async def my_profile(
    telegram_user: dict = Depends(authenticated_user),
):
    telegram_id = int(telegram_user["id"])

    user = await get_user(telegram_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Foydalanuvchi topilmadi.",
        )

    crystals = int(user["crystals"])
    last_collect_at = int(user["last_collect_at"])
    now = int(time.time())

    remaining_seconds = max(
        0,
        last_collect_at + COOLDOWN_SECONDS - now,
    )

    level_data = get_level(crystals)
    is_owner = (
        OWNER_ID != 0 and telegram_id == OWNER_ID
    )

    if is_owner:
        rank = "NEXUS YARATUVCHISI"
        rank_icon = "👑"
    else:
        rank = level_data["level"]
        rank_icon = level_data["level_icon"]

    return {
        "id": telegram_id,
        "first_name": user.get("first_name", ""),
        "username": user.get("username"),
        "crystals": crystals,
        "is_owner": is_owner,
        "rank": rank,
        "rank_icon": rank_icon,
        "level": level_data["level"],
        "level_icon": level_data["level_icon"],
        "level_required": level_data["level_required"],
        "next_level": level_data["next_level"],
        "next_level_icon": level_data["next_level_icon"],
        "next_level_required": (
            level_data["next_level_required"]
        ),
        "progress": level_data["progress"],
        "remaining_seconds": remaining_seconds,
        "created_at": user.get("created_at"),
    }


# ==========================================
# COLLECT CRYSTALS API
# ==========================================

@app.post("/api/collect")
async def collect(
    telegram_user: dict = Depends(authenticated_user),
):
    telegram_id = int(telegram_user["id"])

    result = await collect_crystals(telegram_id)

    if result["status"] == "not_registered":
        raise HTTPException(
            status_code=404,
            detail="Avval /start orqali botni ishga tushir.",
        )

    if result["status"] == "cooldown":
        return {
            "status": "cooldown",
            "message": "Kristal yig'ish uchun hali vaqt bor.",
            "remaining_seconds": result["remaining"],
            "crystals": result["crystals"],
        }

    if result["status"] != "success":
        raise HTTPException(
            status_code=500,
            detail="Kristallarni yig'ishda xatolik yuz berdi.",
        )

    user = await get_user(telegram_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Foydalanuvchi topilmadi.",
        )

    crystals = int(user["crystals"])
    level_data = get_level(crystals)

    is_owner = (
        OWNER_ID != 0 and telegram_id == OWNER_ID
    )

    if is_owner:
        rank = "NEXUS YARATUVCHISI"
        rank_icon = "👑"
    else:
        rank = level_data["level"]
        rank_icon = level_data["level_icon"]

    return {
        "status": "success",
        "message": "Kristallar muvaffaqiyatli yig'ildi!",
        "reward": result["reward"],
        "crystals": crystals,
        "is_owner": is_owner,
        "rank": rank,
        "rank_icon": rank_icon,
        "level": level_data["level"],
        "level_icon": level_data["level_icon"],
        "next_level": level_data["next_level"],
        "next_level_required": (
            level_data["next_level_required"]
        ),
        "progress": level_data["progress"],
        "remaining_seconds": COOLDOWN_SECONDS,
    }


# ==========================================
# WORLD STATISTICS API
# ==========================================

@app.get("/api/world")
async def world_stats(
    telegram_user: dict = Depends(authenticated_user),
):
    stats = await get_world_stats()

    return {
        "project": "NEXUS",
        "players": int(stats["players"]),
        "total_crystals": int(stats["crystals"]),
        "actions": int(stats.get("actions", 0)),
    }


# ==========================================
# MINI APP STATIC FILES
# ==========================================

web_directory = BASE_DIR / "web"

if web_directory.is_dir():
    app.mount(
        "/app",
        StaticFiles(
            directory=str(web_directory),
            html=True,
        ),
        name="mini_app",
    )
else:
    logger.warning(
        "web papkasi topilmadi: %s",
        web_directory,
    )