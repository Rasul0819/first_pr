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
