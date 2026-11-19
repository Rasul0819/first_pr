from datetime import date, timedelta

import pytest
import pytest_asyncio

from database import EXPENSE, INCOME
from locales import kaa as T
from tests.helpers import make_harness

ADMIN = 100


@pytest_asyncio.fixture
async def world(db):
    await db.upsert_user(ADMIN, "boss", "Boss")
    await db.upsert_user(1, "alice", "Alice")
    await db.upsert_user(2, None, "Bob <b>")
    await db.add_transaction(1, INCOME, 10000, "Salary")
    await db.add_transaction(1, EXPENSE, 2550, "Food")
    return db


async def test_non_admin_is_ignored(world):
    h = make_harness(world, user_id=1)
    for cmd in ("/admin", "/stats", "/setplan 2 pro 30"):
        await h.send(cmd)
    await h.click("adm:stats")
    assert h.replies() == []
    assert (await world.get_user(2))["plan"] == "free"


async def test_admin_panel_and_stats(world):
    h = make_harness(world, user_id=ADMIN)
    await h.send("/admin")
    assert "Admin panel" in h.last()
    await h.send("/stats")
    out = h.last()
    assert "Users: <b>3</b>" in out and "paid: 0" in out
    assert "100.00" in out and "25.50" in out
    await h.click("adm:stats")
    assert "Statistics" in h.last()


async def test_recent_users_escapes_html(world):
    h = make_harness(world, user_id=ADMIN)
    await h.click("adm:users")
    out = h.last()
    assert "@alice" in out and "Bob &lt;b&gt;" in out and "Bob <b>" not in out


async def test_setplan_with_expiry(world):
    h = make_harness(world, user_id=ADMIN)
    await h.send("/setplan 1 pro 30")
    u = await world.get_user(1)
    assert u["plan"] == "pro"
    assert u["plan_expires_at"] == (date.today() + timedelta(days=30)).isoformat()
    assert "now <b>pro</b>" in h.last()
    assert (await world.stats())["paid_users"] == 1
    await h.send("/setplan 1 free")
    u = await world.get_user(1)
    assert u["plan"] == "free" and u["plan_expires_at"] is None


@pytest.mark.parametrize("args", ["", "1", "x pro", "1 gold", "1 pro 0", "1 pro abc", "1 pro 1 2", "1 pro 99999"])
async def test_setplan_bad_args(world, args):
    h = make_harness(world, user_id=ADMIN)
    await h.send(f"/setplan {args}")
    assert "Usage" in h.last()
    assert (await world.get_user(1))["plan"] == "free"


async def test_setplan_unknown_user(world):
    h = make_harness(world, user_id=ADMIN)
    await h.send("/setplan 555 pro")
    assert "not found" in h.last()


async def test_active_plan_expiry(world):
    await world.set_plan(1, "pro", "2025-01-01")
    assert await world.active_plan(1, today=date(2025, 1, 1)) == "pro"
    assert await world.active_plan(1, today=date(2025, 1, 2)) == "free"
    await world.set_plan(1, "pro", None)
    assert await world.active_plan(1, today=date(2099, 1, 1)) == "pro"
    assert await world.active_plan(404) == "free"


async def test_admin_can_still_use_user_features(world):
    h = make_harness(world, user_id=ADMIN)
    await h.send("/start")
    assert h.last() == T.WELCOME
