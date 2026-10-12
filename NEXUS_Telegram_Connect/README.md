# 💎 NEXUS — Enter Your Digital Universe

**One Universe. One Identity. Infinite Possibilities.**

NEXUS is a Telegram-powered crystal and rank experience built with Python, FastAPI, Aiogram, SQLite, and a web Mini App. It supports Telegram Mini App authentication and a server-verified Telegram Login Widget for ordinary browsers.

## Features
- 💎 Shared server-side crystal balance and cooldowns
- 🤖 Telegram bot and Mini App integration
- 🔐 Server-side verification of Telegram authentication data
- 🌐 Browser login with a signed, HttpOnly, Secure session cookie
- 🏆 Rank progression and world statistics

## Deploy

**Build command**
```bash
pip install -r requirements.txt
```

**Start command**
```bash
python -m uvicorn nexus.main:app --host 0.0.0.0 --port $PORT
```

Set these environment variables in the hosting dashboard:

- `BOT_TOKEN` — Telegram bot token (keep secret)
- `NEXUS_OWNER_ID` — numeric Telegram user ID for the creator badge
- `WEBAPP_URL` — public HTTPS URL, e.g. `https://nexus-0rvy.onrender.com/app/`
- `DATABASE_PATH` — database file path (use persistent storage in production)
- `DEBUG=false`

## Enable browser Telegram Login
1. Open [@BotFather](https://t.me/BotFather).
2. Run `/setdomain` and select `@nexus_fozilbek_bot`.
3. Set the domain to `nexus-0rvy.onrender.com` (domain only; no `https://` or path).
4. Deploy this version. Open `https://nexus-0rvy.onrender.com/app/` and use the Telegram login button.

The backend validates the Telegram Login Widget hash using the bot token and checks the authentication timestamp. A successful login creates a signed session cookie; the browser cannot choose a Telegram ID to impersonate another account. Mini App requests continue to use Telegram's signed `initData`.

## Security notes
- Never commit `.env` or publish your bot token.
- Browser sessions are signed and stored in `HttpOnly`, `Secure`, `SameSite=Lax` cookies.
- Use a persistent disk/database for production; ephemeral SQLite storage can be lost during redeploys or restarts.
- Telegram Login Widget requires the website domain to be configured with BotFather.

## Project structure
```text
NEXUS/
├── nexus/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── handlers.py
│   └── security.py
├── web/
│   └── index.html
├── requirements.txt
├── .env.example
└── README.md
```

**Created by Fozilbek Qodirov**
