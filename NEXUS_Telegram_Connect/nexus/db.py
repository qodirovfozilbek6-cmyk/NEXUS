
import time

import aiosqlite

from nexus.config import settings


REWARD_AMOUNT = 10
COOLDOWN_SECONDS = 30 * 60
LEADERBOARD_LIMIT = 50


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT NOT NULL DEFAULT '',
    crystals INTEGER NOT NULL DEFAULT 0 CHECK (crystals >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_collect_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
);

CREATE INDEX IF NOT EXISTS idx_actions_user
ON actions(telegram_id);

CREATE INDEX IF NOT EXISTS idx_users_crystals
ON users(crystals DESC);

CREATE TABLE IF NOT EXISTS shop_items (
    item_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price INTEGER NOT NULL CHECK (price >= 0),
    kind TEXT NOT NULL DEFAULT 'cosmetic',
    emoji TEXT NOT NULL DEFAULT '✨',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    purchased_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (telegram_id, item_id),
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
    FOREIGN KEY (item_id) REFERENCES shop_items(item_id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_user
ON inventory(telegram_id);

CREATE TABLE IF NOT EXISTS crystal_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    reference TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_user
ON crystal_transactions(telegram_id);
"""


DEFAULT_SHOP_ITEMS = [
    (
        "aura_green",
        "Emerald Aura",
        "Profil uchun yashil kosmik aura.",
        50,
        "effect",
        "🌿",
    ),
    (
        "frame_neon",
        "Neon Frame",
        "Neon uslubidagi profil ramkasi.",
        100,
        "frame",
        "💠",
    ),
    (
        "avatar_comet",
        "Comet Avatar",
        "Kometa mavzusidagi maxsus avatar.",
        150,
        "avatar",
        "☄️",
    ),
    (
        "aura_galaxy",
        "Galaxy Aura",
        "Galaktik binafsha effekt.",
        250,
        "effect",
        "🌌",
    ),
    (
        "frame_gold",
        "Royal Gold",
        "Oltin rangli premium ramka.",
        400,
        "frame",
        "👑",
    ),
]


async def connect():
    db = await aiosqlite.connect(
        settings.database_file(),
        timeout=30,
    )
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA busy_timeout = 30000")
    return db


async def init_db():
    db = await connect()
    try:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.executescript(SCHEMA)

        await db.executemany(
            """
            INSERT OR IGNORE INTO shop_items
                (item_id, name, description, price, kind, emoji)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            DEFAULT_SHOP_ITEMS,
        )

        await db.commit()
    finally:
        await db.close()


async def upsert_user(user: dict):
    telegram_id = int(user["id"])
    username = user.get("username")
    first_name = user.get("first_name", "")

    db = await connect()
    try:
        await db.execute(
            """
            INSERT INTO users
                (telegram_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (telegram_id, username, first_name),
        )
        await db.commit()
    finally:
        await db.close()


async def get_user(telegram_id: int):
    db = await connect()
    try:
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (int(telegram_id),),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_world_stats():
    db = await connect()
    try:
        cursor = await db.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM users) AS players,
                (SELECT COALESCE(SUM(crystals), 0) FROM users)
                    AS crystals,
                (SELECT COUNT(*) FROM actions) AS actions
            """
        )
        return dict(await cursor.fetchone())
    finally:
        await db.close()


async def get_leaderboard(limit: int = LEADERBOARD_LIMIT):
    limit = max(1, min(int(limit), LEADERBOARD_LIMIT))

    db = await connect()
    try:
        cursor = await db.execute(
            """
            SELECT
                telegram_id,
                username,
                first_name,
                crystals,
                ROW_NUMBER() OVER (
                    ORDER BY crystals DESC, created_at ASC, telegram_id ASC
                ) AS position
            FROM users
            ORDER BY crystals DESC, created_at ASC, telegram_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def get_player_position(telegram_id: int):
    db = await connect()
    try:
        cursor = await db.execute(
            """
            SELECT position
            FROM (
                SELECT
                    telegram_id,
                    ROW_NUMBER() OVER (
                        ORDER BY crystals DESC, created_at ASC,
                                 telegram_id ASC
                    ) AS position
                FROM users
            )
            WHERE telegram_id = ?
            """,
            (int(telegram_id),),
        )
        row = await cursor.fetchone()
        return int(row["position"]) if row else None
    finally:
        await db.close()


async def get_shop_items(telegram_id: int):
    db = await connect()
    try:
        cursor = await db.execute(
            """
            SELECT
                s.item_id,
                s.name,
                s.description,
                s.price,
                s.kind,
                s.emoji,
                CASE WHEN i.id IS NULL THEN 0 ELSE 1 END AS owned
            FROM shop_items AS s
            LEFT JOIN inventory AS i
                ON i.item_id = s.item_id
                AND i.telegram_id = ?
            WHERE s.active = 1
            ORDER BY s.price ASC, s.name ASC
            """,
            (int(telegram_id),),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def get_inventory(telegram_id: int):
    db = await connect()
    try:
        cursor = await db.execute(
            """
            SELECT
                s.item_id,
                s.name,
                s.description,
                s.kind,
                s.emoji,
                i.purchased_at
            FROM inventory AS i
            JOIN shop_items AS s ON s.item_id = i.item_id
            WHERE i.telegram_id = ?
            ORDER BY i.id DESC
            """,
            (int(telegram_id),),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def buy_shop_item(telegram_id: int, item_id: str):
    """
    Narxni klientdan olmaydi.
    Balans tekshiruvi, pul yechish va xarid yozuvi
    bitta tranzaksiyada bajariladi.
    """

    db = await connect()

    try:
        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute(
            """
            SELECT item_id, name, price, active
            FROM shop_items
            WHERE item_id = ?
            """,
            (item_id,),
        )
        item = await cursor.fetchone()

        if not item or int(item["active"]) != 1:
            await db.rollback()
            return {"status": "item_not_found"}

        cursor = await db.execute(
            """
            SELECT crystals
            FROM users
            WHERE telegram_id = ?
            """,
            (int(telegram_id),),
        )
        user = await cursor.fetchone()

        if user is None:
            await db.rollback()
            return {"status": "user_not_found"}

        cursor = await db.execute(
            """
            SELECT id
            FROM inventory
            WHERE telegram_id = ? AND item_id = ?
            """,
            (int(telegram_id), item_id),
        )

        if await cursor.fetchone():
            await db.rollback()
            return {"status": "already_owned"}

        price = int(item["price"])
        balance = int(user["crystals"])

        if balance < price:
            await db.rollback()
            return {
                "status": "insufficient_funds",
                "crystals": balance,
                "price": price,
            }

        await db.execute(
            """
            UPDATE users
            SET crystals = crystals - ?
            WHERE telegram_id = ? AND crystals >= ?
            """,
            (price, int(telegram_id), price),
        )

        cursor = await db.execute(
            """
            SELECT crystals
            FROM users
            WHERE telegram_id = ?
            """,
            (int(telegram_id),),
        )
        updated_user = await cursor.fetchone()

        if updated_user is None:
            await db.rollback()
            return {"status": "user_not_found"}

        await db.execute(
            """
            INSERT INTO inventory (telegram_id, item_id)
            VALUES (?, ?)
            """,
            (int(telegram_id), item_id),
        )

        await db.execute(
            """
            INSERT INTO actions (telegram_id, action_type, details)
            VALUES (?, 'shop_purchase', ?)
            """,
            (int(telegram_id), item_id),
        )

        await db.execute(
            """
            INSERT INTO crystal_transactions
                (telegram_id, amount, transaction_type, reference)
            VALUES (?, ?, 'purchase', ?)
            """,
            (int(telegram_id), -price, item_id),
        )

        await db.commit()

        return {
            "status": "success",
            "item_id": item_id,
            "item_name": item["name"],
            "price": price,
            "crystals": int(updated_user["crystals"]),
        }

    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


async def get_creator_overview():
    db = await connect()
    try:
        cursor = await db.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM users) AS players,
                (SELECT COALESCE(SUM(crystals), 0) FROM users)
                    AS total_crystals,
                (SELECT COUNT(*) FROM actions) AS total_actions,
                (SELECT COUNT(*) FROM inventory) AS total_purchases
            """
        )
        stats = dict(await cursor.fetchone())

        cursor = await db.execute(
            """
            SELECT
                telegram_id,
                username,
                first_name,
                crystals,
                created_at
            FROM users
            ORDER BY crystals DESC, created_at ASC
            LIMIT 10
            """
        )
        stats["top_players"] = [
            dict(row) for row in await cursor.fetchall()
        ]
        return stats
    finally:
        await db.close()


async def collect_crystals(telegram_id: int):
    """Har 30 daqiqada bir marta serverdan 10 kristall olish."""

    db = await connect()

    try:
        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute(
            """
            SELECT crystals, last_collect_at
            FROM users
            WHERE telegram_id = ?
            """,
            (int(telegram_id),),
        )
        user = await cursor.fetchone()

        if user is None:
            await db.rollback()
            return {"status": "not_registered"}

        now = int(time.time())
        last_collect_at = int(user["last_collect_at"])
        next_allowed = last_collect_at + COOLDOWN_SECONDS

        if last_collect_at > 0 and now < next_allowed:
            remaining = next_allowed - now
            crystals = int(user["crystals"])
            await db.rollback()

            return {
                "status": "cooldown",
                "remaining": remaining,
                "crystals": crystals,
            }

        await db.execute(
            """
            UPDATE users
            SET crystals = crystals + ?,
                last_collect_at = ?
            WHERE telegram_id = ?
            """,
            (REWARD_AMOUNT, now, int(telegram_id)),
        )

        await db.execute(
            """
            INSERT INTO actions
                (telegram_id, action_type, details)
            VALUES (?, 'collect', ?)
            """,
            (int(telegram_id), f"+{REWARD_AMOUNT} crystals"),
        )

        await db.execute(
            """
            INSERT INTO crystal_transactions
                (telegram_id, amount, transaction_type, reference)
            VALUES (?, ?, 'collect', 'cooldown_reward')
            """,
            (int(telegram_id), REWARD_AMOUNT),
        )

        cursor = await db.execute(
            """
            SELECT crystals, last_collect_at
            FROM users
            WHERE telegram_id = ?
            """,
            (int(telegram_id),),
        )
        updated_user = await cursor.fetchone()

        await db.commit()

        return {
            "status": "success",
            "reward": REWARD_AMOUNT,
            "crystals": int(updated_user["crystals"]),
            "last_collect_at": int(updated_user["last_collect_at"]),
        }

    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()