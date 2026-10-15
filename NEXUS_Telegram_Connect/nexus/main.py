
import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager, suppress

from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonWebApp, WebAppInfo
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from nexus.config import BASE_DIR, settings
from nexus.db import (
    init_db,
    close_db,
    upsert_user,
    get_user,
    get_world_stats,
    collect_crystals,
    COOLDOWN_SECONDS,
    get_shop_items,
    get_inventory,
    buy_shop_item,
)
from nexus.handlers import router
from nexus.security import (
    validate_init_data,
    validate_telegram_login,
    create_browser_session,
    validate_browser_session,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NEXUS")

OWNER_ID = int(os.getenv("NEXUS_OWNER_ID", "0") or "0")

LEVELS = [
    (0, "Novice", "🌱"),
    (100, "Explorer", "🧭"),
    (300, "Apprentice", "⚡"),
    (600, "Warrior", "⚔️"),
    (1000, "Elite", "🛡️"),
    (1600, "Master", "💎"),
    (2400, "Champion", "🏆"),
    (3400, "Legend", "🌌"),
    (4600, "Mythic", "🔮"),
    (6000, "Supreme", "👑"),
]


def get_level(crystals: int) -> dict:
    crystals = max(0, int(crystals))
    current_index = 0

    for index, (threshold, _, _) in enumerate(LEVELS):
        if crystals >= threshold:
            current_index = index
        else:
            break

    threshold, name, icon = LEVELS[current_index]

    if current_index + 1 < len(LEVELS):
        next_threshold, next_name, _ = LEVELS[current_index + 1]
    else:
        next_threshold = threshold
        next_name = name

    if next_threshold > threshold:
        progress = min(
            100,
            int(
                (crystals - threshold)
                / (next_threshold - threshold)
                * 100
            ),
        )
    else:
        progress = 100

    return {
        "level": current_index + 1,
        "name": name,
        "icon": icon,
        "threshold": threshold,
        "next_threshold": next_threshold,
        "next_level": next_name,
        "progress": progress,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("NEXUS PostgreSQL bazasi ishga tushdi.")

    bot = None
    dispatcher = None
    polling_task = None

    try:
        if settings.BOT_TOKEN:
            bot = Bot(token=settings.BOT_TOKEN)
            dispatcher = Dispatcher()
            dispatcher.include_router(router)

            if (
                settings.WEBAPP_URL
                and settings.WEBAPP_URL.startswith("https://")
            ):
                with suppress(Exception):
                    await bot.set_chat_menu_button(
                        menu_button=MenuButtonWebApp(
                            text="NEXUS",
                            web_app=WebAppInfo(
                                url=settings.WEBAPP_URL
                            ),
                        )
                    )

            polling_task = asyncio.create_task(
                dispatcher.start_polling(bot)
            )
            logger.info("NEXUS Telegram bot ishga tushdi.")
        else:
            logger.warning(
                "BOT_TOKEN sozlanmagan. Bot polling ishga tushmadi."
            )

        yield

    finally:
        if polling_task:
            polling_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await polling_task

        if bot:
            with suppress(Exception):
                await bot.session.close()

        await close_db()
        logger.info("NEXUS yopildi.")


app = FastAPI(
    title="NEXUS API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "name": "NEXUS",
        "status": "online",
        "app": "/app/",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


async def authenticated_user(request: Request) -> dict:
    """
    Telegram Mini App initData yoki browser session orqali
    foydalanuvchini aniqlaydi.
    """
    init_data = request.headers.get(
        "X-Telegram-Init-Data", ""
    ).strip()

    if init_data:
        if not settings.BOT_TOKEN:
            raise HTTPException(
                status_code=503,
                detail="Telegram bot sozlanmagan.",
            )

        try:
            telegram_user = validate_init_data(
                init_data,
                settings.BOT_TOKEN,
            )
        except Exception:
            telegram_user = None

        if telegram_user:
            await upsert_user(telegram_user)

            user_id = int(
                telegram_user.get("id")
                or telegram_user.get("telegram_id")
            )

            db_user = await get_user(user_id)

            if db_user:
                return db_user

    session_token = request.cookies.get("nexus_session")

    if session_token:
        try:
            session_user = validate_browser_session(
                session_token
            )
        except Exception:
            session_user = None

        if session_user:
            if isinstance(session_user, dict):
                session_id = (
                    session_user.get("id")
                    or session_user.get("telegram_id")
                )
            else:
                session_id = session_user

            if session_id:
                db_user = await get_user(int(session_id))

                if db_user:
                    return db_user

    raise HTTPException(
        status_code=401,
        detail="Avval Telegram orqali tizimga kiring.",
    )


@app.post("/api/auth/telegram-login")
async def telegram_login(request: Request):
    if not settings.BOT_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Telegram bot sozlanmagan.",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Noto'g'ri JSON ma'lumot.",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Noto'g'ri so'rov.",
        )

    try:
        telegram_user = validate_telegram_login(
            payload,
            settings.BOT_TOKEN,
        )
    except Exception:
        telegram_user = None

    if not telegram_user:
        raise HTTPException(
            status_code=401,
            detail="Telegram login tekshiruvidan o'tmadi.",
        )

    await upsert_user(telegram_user)

    user_id = int(
        telegram_user.get("id")
        or telegram_user.get("telegram_id")
    )

    session_token = create_browser_session(user_id)
    is_owner = OWNER_ID != 0 and user_id == OWNER_ID

    response = JSONResponse({
        "success": True,
        "status": "success",
        "user": {
            "id": user_id,
            "telegram_id": user_id,
            "first_name": telegram_user.get("first_name", ""),
            "username": telegram_user.get("username"),
            "is_owner": is_owner,
        },
    })

    response.set_cookie(
        key="nexus_session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )

    return response


@app.post("/api/auth/logout")
async def logout():
    response = JSONResponse({
        "success": True,
        "status": "success",
    })

    response.delete_cookie(
        key="nexus_session",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return response


@app.get("/api/me")
async def api_me(
    user: dict = Depends(authenticated_user),
):
    telegram_id = int(user["telegram_id"])
    crystals = int(user["crystals"])

    last_collect = user.get("last_collect_at")
    if hasattr(last_collect, "timestamp"):
        last_collect = int(last_collect.timestamp())
    else:
        last_collect = int(last_collect or 0)

    remaining_seconds = max(
        0,
        last_collect + COOLDOWN_SECONDS - int(time.time()),
    )

    level_data = get_level(crystals)
    is_owner = OWNER_ID != 0 and telegram_id == OWNER_ID

    return {
        "id": telegram_id,
        "telegram_id": telegram_id,
        "first_name": user.get("first_name") or "",
        "username": user.get("username"),
        "crystals": crystals,
        "is_owner": is_owner,
        "rank": "Creator Supreme" if is_owner else level_data["name"],
        "level": level_data["level"],
        "level_name": level_data["name"],
        "level_icon": level_data["icon"],
        "threshold": level_data["threshold"],
        "next_threshold": level_data["next_threshold"],
        "next_level": level_data["next_level"],
        "progress": level_data["progress"],
        "remaining_seconds": remaining_seconds,
        "created_at": (
            user["created_at"].isoformat()
            if user.get("created_at")
            and hasattr(user["created_at"], "isoformat")
            else user.get("created_at")
        ),
    }


@app.post("/api/collect")
async def api_collect(
    user: dict = Depends(authenticated_user),
):
    telegram_id = int(user["telegram_id"])
    result = await collect_crystals(telegram_id)
    status = result.get("status")

    if status == "not_registered":
        raise HTTPException(
            status_code=404,
            detail="Foydalanuvchi bazada topilmadi.",
        )

    if status == "cooldown":
        return {
            **result,
            "success": False,
        }

    if status == "success":
        return {
            **result,
            "success": True,
        }

    return result


@app.get("/api/world")
async def api_world():
    stats = await get_world_stats()

    return {
        "players": stats["players"],
        "total_crystals": stats["crystals"],
        "actions": stats["actions"],
    }


@app.get("/api/shop")
async def api_shop(
    user: dict = Depends(authenticated_user),
):
    items = await get_shop_items()

    return {
        "items": [
            {
                **item,
                "id": str(item.get("id") or item.get("item_id")),
                "item_id": str(
                    item.get("item_id") or item.get("id")
                ),
                "price": int(item.get("price") or 0),
            }
            for item in items
        ],
    }


@app.get("/api/inventory")
async def api_inventory(
    user: dict = Depends(authenticated_user),
):
    telegram_id = int(user["telegram_id"])
    items = await get_inventory(telegram_id)

    return {
        "items": [
            {
                **item,
                "id": str(item.get("id") or item.get("item_id")),
                "item_id": str(
                    item.get("item_id") or item.get("id")
                ),
                "price": int(item.get("price") or 0),
            }
            for item in items
        ],
    }


@app.post("/api/shop/buy")
async def api_shop_buy(
    request: Request,
    user: dict = Depends(authenticated_user),
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Noto'g'ri JSON ma'lumot.",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Noto'g'ri so'rov.",
        )

    item_id = str(payload.get("item_id", "")).strip()

    if not item_id or len(item_id) > 100:
        raise HTTPException(
            status_code=400,
            detail="Buyum ID si noto'g'ri.",
        )

    telegram_id = int(user["telegram_id"])
    is_owner = OWNER_ID != 0 and telegram_id == OWNER_ID

    result = await buy_shop_item(
        telegram_id=telegram_id,
        item_id=item_id,
        is_owner=is_owner,
    )

    status = result.get("status")

    if status == "not_registered":
        raise HTTPException(
            status_code=404,
            detail="Foydalanuvchi ro'yxatdan o'tmagan.",
        )

    if status == "item_not_found":
        raise HTTPException(
            status_code=404,
            detail="Buyum topilmadi.",
        )

    if status == "already_owned":
        return {
            **result,
            "success": False,
            "message": "Bu buyum inventaringizda bor.",
        }

    if status == "insufficient_crystals":
        return {
            **result,
            "success": False,
            "message": "Kristall yetarli emas.",
        }

    if status == "success":
        return {
            **result,
            "success": True,
        }

    logger.error("Noma'lum xarid javobi: %r", result)

    raise HTTPException(
        status_code=500,
        detail="Xaridni bajarishda noma'lum xato.",
    )


web_dir = BASE_DIR / "web"

if web_dir.exists():
    app.mount(
        "/app",
        StaticFiles(directory=str(web_dir), html=True),
        name="app",
    )
else:
    logger.warning(
        "Web papkasi topilmadi: %s",
        web_dir,
    )
