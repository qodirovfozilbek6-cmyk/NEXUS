
import os
import time
import logging
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import asyncpg
from dotenv import load_dotenv

from nexus.config import BASE_DIR

logger = logging.getLogger("NEXUS.DB")

load_dotenv(Path(BASE_DIR) / ".env", override=False)

REWARD_AMOUNT = 10
COOLDOWN_SECONDS = 30 * 60
LEADERBOARD_LIMIT = 50

_pool = None


def _prepare_database_url(url: str) -> str:
    if not url:
        raise RuntimeError("DATABASE_URL topilmadi. .env faylini tekshir.")

    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in {"sslmode", "channel_binding"}
    ]

    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(query),
        parts.fragment,
    ))


def _pool_or_raise():
    if _pool is None or _pool.is_closing():
        raise RuntimeError(
            "PostgreSQL pool tayyor emas. Avval await init_db() chaqir."
        )
    return _pool


async def connect():
    return await _pool_or_raise().acquire()


async def close_db():
    global _pool

    if _pool is not None:
        pool = _pool
        _pool = None
        await pool.close()
        logger.info("PostgreSQL pool yopildi.")


async def init_db():
    global _pool

    if _pool is not None and not _pool.is_closing():
        return

    load_dotenv(Path(BASE_DIR) / ".env", override=False)

    database_url = os.getenv("DATABASE_URL", "").strip()
    prepared_url = _prepare_database_url(database_url)

    pool = await asyncpg.create_pool(
        dsn=prepared_url,
        ssl="require",
        min_size=1,
        max_size=5,
        command_timeout=30,
    )

    try:
        async with pool.acquire() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT NOT NULL DEFAULT '',
                    crystals BIGINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_collect_at BIGINT NOT NULL DEFAULT 0,
                    source TEXT NOT NULL DEFAULT 'telegram',
                    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_game_at BIGINT NOT NULL DEFAULT 0
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS shop_items (
                    item_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    price BIGINT NOT NULL DEFAULT 0,
                    kind TEXT NOT NULL DEFAULT 'item',
                    emoji TEXT NOT NULL DEFAULT '✨',
                    active BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    action_type TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    item_id TEXT NOT NULL,
                    purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS crystal_transactions (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    amount BIGINT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    reference TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_telegram_id
                ON actions (telegram_id);
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_inventory_telegram_id
                ON inventory (telegram_id);
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_crystal_transactions_telegram_id
                ON crystal_transactions (telegram_id);
            """)

            defaults = [
                ("aura_green", "Green Aura", "Yashil aura", 50, "aura", "🟢", True),
                ("frame_neon", "Neon Frame", "Neon profil ramkasi", 100, "frame", "🖼️", True),
                ("avatar_comet", "Comet Avatar", "Kometa avatari", 150, "avatar", "☄️", True),
                ("aura_galaxy", "Galaxy Aura", "Galaktik aura", 250, "aura", "🌌", True),
                ("frame_gold", "Gold Frame", "Oltin profil ramkasi", 400, "frame", "👑", True),
            ]

            for item in defaults:
                await db.execute("""
                    INSERT INTO shop_items (
                        item_id, name, description, price, kind, emoji, active
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (item_id) DO NOTHING;
                """, *item)

        _pool = pool
        logger.info("PostgreSQL bazasi tayyor.")

    except Exception:
        await pool.close()
        logger.exception("PostgreSQL bazasini tayyorlashda xato.")
        raise


async def upsert_user(user: dict):
    telegram_id = int(user.get("id") or user.get("telegram_id"))
    username = user.get("username")
    first_name = user.get("first_name") or ""

    async with _pool_or_raise().acquire() as db:
        await db.execute("""
            INSERT INTO users (
                telegram_id, username, first_name, crystals,
                created_at, last_collect_at, source, last_seen_at, last_game_at
            )
            VALUES ($1, $2, $3, 0, NOW(), 0, 'telegram', NOW(), 0)
            ON CONFLICT (telegram_id)
            DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_seen_at = NOW();
        """, telegram_id, username, first_name)


async def get_user(telegram_id: int):
    async with _pool_or_raise().acquire() as db:
        row = await db.fetchrow("""
            SELECT telegram_id, username, first_name, crystals,
                   created_at, last_collect_at, source, last_seen_at, last_game_at
            FROM users
            WHERE telegram_id = $1;
        """, int(telegram_id))

    return dict(row) if row else None


async def get_world_stats():
    async with _pool_or_raise().acquire() as db:
        row = await db.fetchrow("""
            SELECT COUNT(*) AS players,
                   COALESCE(SUM(crystals), 0) AS crystals
            FROM users;
        """)
        actions = await db.fetchval("SELECT COUNT(*) FROM actions;")

    return {
        "players": int(row["players"]),
        "crystals": int(row["crystals"]),
        "actions": int(actions or 0),
    }


async def get_leaderboard(limit: int = LEADERBOARD_LIMIT):
    limit = max(1, min(int(limit), 100))

    async with _pool_or_raise().acquire() as db:
        rows = await db.fetch("""
            SELECT telegram_id, username, first_name, crystals
            FROM users
            ORDER BY crystals DESC, telegram_id ASC
            LIMIT $1;
        """, limit)

    return [dict(row) for row in rows]


async def get_player_position(telegram_id: int):
    async with _pool_or_raise().acquire() as db:
        row = await db.fetchrow("""
            SELECT position
            FROM (
                SELECT telegram_id,
                       ROW_NUMBER() OVER (
                           ORDER BY crystals DESC, telegram_id ASC
                       ) AS position
                FROM users
            ) AS ranking
            WHERE telegram_id = $1;
        """, int(telegram_id))

    return int(row["position"]) if row else None


async def get_shop_items():
    async with _pool_or_raise().acquire() as db:
        rows = await db.fetch("""
            SELECT item_id AS id, item_id, name, description, price,
                   kind AS item_type, kind, emoji, active
            FROM shop_items
            WHERE active IS TRUE
            ORDER BY price ASC;
        """)

    return [dict(row) for row in rows]


async def get_inventory(telegram_id: int):
    async with _pool_or_raise().acquire() as db:
        rows = await db.fetch("""
            SELECT i.id, i.telegram_id, i.item_id, i.purchased_at,
                   s.name, s.description, s.price,
                   s.kind AS item_type, s.emoji
            FROM inventory AS i
            LEFT JOIN shop_items AS s ON s.item_id = i.item_id
            WHERE i.telegram_id = $1
            ORDER BY i.id DESC;
        """, int(telegram_id))

    return [dict(row) for row in rows]


async def buy_shop_item(
    telegram_id: int,
    item_id: str,
    is_owner: bool = False,
):
    pool = _pool_or_raise()
    telegram_id = int(telegram_id)
    item_id = str(item_id).strip()

    if not item_id:
        return {"status": "item_not_found"}

    async with pool.acquire() as db:
        async with db.transaction():
            user = await db.fetchrow("""
                SELECT telegram_id, crystals
                FROM users
                WHERE telegram_id = $1
                FOR UPDATE;
            """, telegram_id)

            if not user:
                return {"status": "not_registered"}

            item = await db.fetchrow("""
                SELECT item_id, name, price, active
                FROM shop_items
                WHERE item_id = $1
                FOR SHARE;
            """, item_id)

            if not item or not item["active"]:
                return {"status": "item_not_found"}

            already_owned = await db.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM inventory
                    WHERE telegram_id = $1 AND item_id = $2
                );
            """, telegram_id, item_id)

            if already_owned:
                return {"status": "already_owned"}

            balance = int(user["crystals"])
            price = 0 if is_owner else int(item["price"])

            if balance < price:
                return {
                    "status": "insufficient_crystals",
                    "crystals": balance,
                    "price": price,
                }

            if price:
                await db.execute("""
                    UPDATE users
                    SET crystals = crystals - $1
                    WHERE telegram_id = $2;
                """, price, telegram_id)

            await db.execute("""
                INSERT INTO inventory (telegram_id, item_id, purchased_at)
                VALUES ($1, $2, NOW());
            """, telegram_id, item_id)

            await db.execute("""
                INSERT INTO crystal_transactions (
                    telegram_id, amount, transaction_type, reference, created_at
                )
                VALUES ($1, $2, $3, $4, NOW());
            """,
                telegram_id,
                -price,
                "creator_free_purchase" if is_owner else "purchase",
                f"shop:{item_id}",
            )

            return {
                "status": "success",
                "item_id": item_id,
                "item_name": item["name"],
                "price": price,
                "crystals": balance - price,
                "free": bool(is_owner),
            }


async def get_creator_overview():
    async with _pool_or_raise().acquire() as db:
        stats = await db.fetchrow("""
            SELECT COUNT(*) AS players,
                   COALESCE(SUM(crystals), 0) AS crystals
            FROM users;
        """)
        action_count = await db.fetchval("SELECT COUNT(*) FROM actions;")

        recent_users = await db.fetch("""
            SELECT telegram_id, username, first_name, crystals, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 10;
        """)

        recent_transactions = await db.fetch("""
            SELECT telegram_id, amount, transaction_type,
                   reference AS description, created_at
            FROM crystal_transactions
            ORDER BY id DESC
            LIMIT 10;
        """)

    return {
        "players": int(stats["players"]),
        "crystals": int(stats["crystals"]),
        "actions": int(action_count or 0),
        "recent_users": [dict(row) for row in recent_users],
        "recent_transactions": [dict(row) for row in recent_transactions],
    }


async def collect_crystals(telegram_id: int):
    pool = _pool_or_raise()
    telegram_id = int(telegram_id)
    now = int(time.time())

    async with pool.acquire() as db:
        async with db.transaction():
            user = await db.fetchrow("""
                SELECT telegram_id, crystals, last_collect_at
                FROM users
                WHERE telegram_id = $1
                FOR UPDATE;
            """, telegram_id)

            if not user:
                return {"status": "not_registered"}

            last_collect = int(user["last_collect_at"] or 0)
            remaining = max(0, last_collect + COOLDOWN_SECONDS - now)

            if remaining > 0:
                return {
                    "status": "cooldown",
                    "remaining": remaining,
                    "crystals": int(user["crystals"]),
                }

            await db.execute("""
                UPDATE users
                SET crystals = crystals + $1,
                    last_collect_at = $2,
                    last_seen_at = NOW()
                WHERE telegram_id = $3;
            """, REWARD_AMOUNT, now, telegram_id)

            await db.execute("""
                INSERT INTO actions (telegram_id, action_type, details, created_at)
                VALUES ($1, $2, $3, NOW());
            """, telegram_id, "collect", f"reward={REWARD_AMOUNT}")

            await db.execute("""
                INSERT INTO crystal_transactions (
                    telegram_id, amount, transaction_type, reference, created_at
                )
                VALUES ($1, $2, $3, $4, NOW());
            """,
                telegram_id,
                REWARD_AMOUNT,
                "collect",
                "crystal_collection_reward",
            )

            return {
                "status": "success",
                "reward": REWARD_AMOUNT,
                "crystals": int(user["crystals"]) + REWARD_AMOUNT,
                "remaining": COOLDOWN_SECONDS,
            }
