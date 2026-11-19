from datetime import date

import pytest

from database import EXPENSE, INCOME, Database, month_bounds, to_cents


@pytest.mark.parametrize("raw,cents", [("12", 1200), ("12.5", 1250), ("1 200,50", 120050), ("0.01", 1)])
def test_to_cents(raw, cents):
    assert to_cents(raw) == cents


@pytest.mark.parametrize("raw", ["abc", "0", "-5", "nan", "inf", "", "0.001"])
def test_to_cents_invalid(raw):
    with pytest.raises(ValueError):
        to_cents(raw)


def test_month_bounds_december():
    assert month_bounds(2025, 12) == ("2025-12-01", "2026-01-01")
    assert month_bounds(2025, 2) == ("2025-02-01", "2025-03-01")


async def test_user_upsert_and_plan(db):
    await db.upsert_user(1, "a", "Alice")
    await db.upsert_user(1, "a2", "Alice B")
    u = await db.get_user(1)
    assert u["username"] == "a2" and u["plan"] == "free"
    assert await db.set_plan(1, "pro", "2030-01-01")
    assert (await db.get_user(1))["plan"] == "pro"
    assert not await db.set_plan(999, "pro")


async def test_add_summary_and_isolation(db):
    for uid in (1, 2):
        await db.upsert_user(uid, None, None)
    d = date(2025, 3, 10)
    await db.add_transaction(1, EXPENSE, 1000, "Food", "lunch", d)
    await db.add_transaction(1, EXPENSE, 500, "Food", "", d)
    await db.add_transaction(1, EXPENSE, 3000, "Rent", "", d)
    await db.add_transaction(1, INCOME, 100000, "Salary", "", d)
    await db.add_transaction(1, EXPENSE, 999, "Food", "", date(2025, 4, 1))  # other month
    await db.add_transaction(2, EXPENSE, 777, "Food", "", d)                # other user
    s = await db.month_summary(1, 2025, 3)
    assert s.income_cents == 100000 and s.expense_cents == 4500
    assert s.net_cents == 95500
    assert s.by_category == {"Rent": 3000, "Food": 1500}
    assert s.by_source == {"Salary": 100000}
    assert len(await db.month_transactions(1, 2025, 3)) == 4


async def test_empty_month(db):
    await db.upsert_user(1, None, None)
    s = await db.month_summary(1, 2025, 1)
    assert s.net_cents == 0 and s.by_category == {}


async def test_delete_only_own(db):
    await db.upsert_user(1, None, None)
    await db.upsert_user(2, None, None)
    tid = await db.add_transaction(1, EXPENSE, 100, "X")
    assert not await db.delete_transaction(2, tid)
    assert await db.delete_transaction(1, tid)
    assert await db.recent(1) == []


async def test_validation(db):
    await db.upsert_user(1, None, None)
    with pytest.raises(ValueError):
        await db.add_transaction(1, "bogus", 100, "X")
    with pytest.raises(Exception):
        await db.add_transaction(1, EXPENSE, -5, "X")


async def test_recent_order_and_stats(db):
    await db.upsert_user(1, None, None)
    a = await db.add_transaction(1, EXPENSE, 100, "A", tx_date=date(2025, 1, 1))
    b = await db.add_transaction(1, INCOME, 900, "B", tx_date=date(2025, 1, 2))
    assert [t.id for t in await db.recent(1)] == [b, a]
    st = await db.stats()
    assert st["users"] == 1 and st["transactions"] == 2
    assert st["income_cents"] == 900 and st["expense_cents"] == 100


async def test_persistence_to_file(tmp_path):
    p = str(tmp_path / "sub" / "t.db")
    d = Database(p)
    await d.connect()
    await d.upsert_user(5, "x", "y")
    await d.close()
    d2 = Database(p)
    await d2.connect()
    assert (await d2.get_user(5))["username"] == "x"
    await d2.close()
