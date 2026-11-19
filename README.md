# Expense & Income Tracker Bot

Telegram bot (aiogram 3.x + SQLite) for logging daily expenses/income and
generating a monthly Excel dashboard.

## Layout
```
main.py            entry point, wires routers
config.py          settings from .env
database/          SQLite layer (aiosqlite)
handlers/user.py   user flows (FSM)   handlers/admin.py  admin panel
keyboards/         reply/inline keyboards
reports/           Excel dashboard generator
tests/             pytest suite
```

## Run
```
pip install -r requirements.txt
cp .env.example .env   # fill BOT_TOKEN, ADMIN_IDS
python main.py
pytest
```

## Features
- ➖ Expense (amount → category → note) and ➕ Income (amount → source), stored in SQLite as integer cents
- 🕘 History with per-entry delete
- 📊 Excel dashboard (KPIs, category/source tables, pie + daily bar charts, full transaction sheet):
  `/report` or `/report 2025-03`; sent automatically on the 1st of each month at 09:00
- 🛠 Admin (IDs in `ADMIN_IDS`): `/admin`, `/stats`, `/setplan <user_id> <free|pro> [days]`
  — `users.plan` / `plan_expires_at` and `Database.set_plan/active_plan` are the hooks for paid subscriptions
