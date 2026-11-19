"""SQLite data layer (aiosqlite). Amounts are stored as integer cents."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import aiosqlite

EXPENSE = "expense"
INCOME = "income"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    full_name       TEXT,
    created_at      TEXT NOT NULL,
    plan            TEXT NOT NULL DEFAULT 'free',
    plan_expires_at TEXT,
    is_blocked      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    kind         TEXT NOT NULL CHECK (kind IN ('expense','income')),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    category     TEXT NOT NULL,
    note         TEXT NOT NULL DEFAULT '',
    tx_date      TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_user_date ON transactions(user_id, tx_date);
"""


def to_cents(value: str | float | Decimal) -> int:
    """Parse a user-entered amount ('12.5', '1 200,50') into integer cents."""
    try:
        d = Decimal(str(value).replace(" ", "").replace(",", "."))
    except InvalidOperation:
        raise ValueError("invalid amount") from None
    if not d.is_finite() or d <= 0:
        raise ValueError("amount must be positive")
    if d != d.quantize(Decimal("0.01")):
        raise ValueError("at most 2 decimal places")
    cents = int(d * 100)
    if cents <= 0 or cents > 10**13:
        raise ValueError("amount out of range")
    return cents


def month_bounds(year: int, month: int) -> tuple[str, str]:
    """Return [start, end) ISO dates for a month."""
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


@dataclass(frozen=True)
class Transaction:
    id: int
    user_id: int
    kind: str
    amount_cents: int
    category: str
    note: str
    tx_date: str

    @property
    def amount(self) -> float:
        return self.amount_cents / 100


@dataclass(frozen=True)
class MonthSummary:
    income_cents: int
    expense_cents: int
    by_category: dict[str, int]   # expenses per category
    by_source: dict[str, int]     # income per source

    @property
    def net_cents(self) -> int:
        return self.income_cents - self.expense_cents


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str = "data/tracker.db") -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        assert self._conn is not None, "Database.connect() was not called"
        return self._conn

    # ---- users -------------------------------------------------------
    async def upsert_user(self, user_id: int, username: str | None, full_name: str | None) -> None:
        await self.conn.execute(
            """INSERT INTO users (user_id, username, full_name, created_at) VALUES (?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name""",
            (user_id, username, full_name, _now()),
        )
        await self.conn.commit()

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        async with self.conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

    async def set_plan(self, user_id: int, plan: str, expires_at: str | None = None) -> bool:
        """Subscription hook: change a user's plan ('free', 'pro', ...)."""
        cur = await self.conn.execute(
            "UPDATE users SET plan=?, plan_expires_at=? WHERE user_id=?", (plan, expires_at, user_id)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def user_ids(self) -> list[int]:
        async with self.conn.execute("SELECT user_id FROM users WHERE is_blocked=0") as cur:
            return [r[0] for r in await cur.fetchall()]

    # ---- transactions ------------------------------------------------
    async def add_transaction(
        self, user_id: int, kind: str, amount_cents: int, category: str,
        note: str = "", tx_date: date | None = None,
    ) -> int:
        if kind not in (EXPENSE, INCOME):
            raise ValueError("kind must be 'expense' or 'income'")
        cur = await self.conn.execute(
            """INSERT INTO transactions (user_id, kind, amount_cents, category, note, tx_date, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, kind, amount_cents, category.strip(), note.strip(),
             (tx_date or date.today()).isoformat(), _now()),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def delete_transaction(self, user_id: int, tx_id: int) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM transactions WHERE id=? AND user_id=?", (tx_id, user_id)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    @staticmethod
    def _row_to_tx(r: aiosqlite.Row) -> Transaction:
        return Transaction(r["id"], r["user_id"], r["kind"], r["amount_cents"],
                           r["category"], r["note"], r["tx_date"])

    async def recent(self, user_id: int, limit: int = 10) -> list[Transaction]:
        async with self.conn.execute(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY tx_date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            return [self._row_to_tx(r) for r in await cur.fetchall()]

    async def month_transactions(self, user_id: int, year: int, month: int) -> list[Transaction]:
        start, end = month_bounds(year, month)
        async with self.conn.execute(
            """SELECT * FROM transactions WHERE user_id=? AND tx_date>=? AND tx_date<?
               ORDER BY tx_date, id""", (user_id, start, end),
        ) as cur:
            return [self._row_to_tx(r) for r in await cur.fetchall()]

    async def month_summary(self, user_id: int, year: int, month: int) -> MonthSummary:
        start, end = month_bounds(year, month)
        async with self.conn.execute(
            """SELECT kind, category, SUM(amount_cents) AS total FROM transactions
               WHERE user_id=? AND tx_date>=? AND tx_date<? GROUP BY kind, category
               ORDER BY total DESC""", (user_id, start, end),
        ) as cur:
            rows = await cur.fetchall()
        exp = {r["category"]: r["total"] for r in rows if r["kind"] == EXPENSE}
        inc = {r["category"]: r["total"] for r in rows if r["kind"] == INCOME}
        return MonthSummary(sum(inc.values()), sum(exp.values()), exp, inc)

    # ---- admin stats -------------------------------------------------
    async def stats(self) -> dict[str, int]:
        async def one(sql: str, *args) -> int:
            async with self.conn.execute(sql, args) as cur:
                return (await cur.fetchone())[0] or 0

        month_start = date.today().replace(day=1).isoformat()
        return {
            "users": await one("SELECT COUNT(*) FROM users"),
            "paid_users": await one("SELECT COUNT(*) FROM users WHERE plan!='free'"),
            "active_month": await one(
                "SELECT COUNT(DISTINCT user_id) FROM transactions WHERE tx_date>=?", month_start),
            "transactions": await one("SELECT COUNT(*) FROM transactions"),
            "income_cents": await one("SELECT SUM(amount_cents) FROM transactions WHERE kind='income'"),
            "expense_cents": await one("SELECT SUM(amount_cents) FROM transactions WHERE kind='expense'"),
        }
