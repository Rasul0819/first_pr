"""Generate samples/sample_report_kaa.xlsx from demo data (run: python -m scripts.make_sample_report)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from database import EXPENSE, INCOME, Database
from datetime import date
from locales import kaa as T
from reports.monthly import generate_monthly_report

DEMO = [
    (INCOME, 450000, T.INCOME_SOURCES[0], "", 3),
    (INCOME, 80000, T.INCOME_SOURCES[1], "Sayt jobası", 14),
    (EXPENSE, 120000, T.EXPENSE_CATEGORIES[2], "Ayına kvartira", 4),
    (EXPENSE, 45050, T.EXPENSE_CATEGORIES[0], "Bazar", 6),
    (EXPENSE, 18000, T.EXPENSE_CATEGORIES[1], "Taksi", 7),
    (EXPENSE, 32000, T.EXPENSE_CATEGORIES[3], "Kiyim", 12),
    (EXPENSE, 15500, T.EXPENSE_CATEGORIES[4], "Dári-dármaq", 15),
    (EXPENSE, 9900, T.EXPENSE_CATEGORIES[5], "Kino", 20),
    (EXPENSE, 27300, T.EXPENSE_CATEGORIES[0], "Awqat", 22),
]


async def main() -> Path:
    db = Database(":memory:")
    await db.connect()
    await db.upsert_user(1, "demo", "Demo Paydalanıwshı")
    for kind, cents, cat, note, day in DEMO:
        await db.add_transaction(1, kind, cents, cat, note, date(2025, 3, day))
    _, data = await generate_monthly_report(db, 1, 2025, 3, owner="Demo Paydalanıwshı")
    await db.close()
    out = Path(__file__).resolve().parent.parent / "samples" / "sample_report_kaa.xlsx"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(data)
    return out


if __name__ == "__main__":
    print(asyncio.run(main()))
