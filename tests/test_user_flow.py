import pytest
import pytest_asyncio
from datetime import date

from tests.helpers import make_harness

from database import EXPENSE, INCOME
from keyboards import user as kb


@pytest_asyncio.fixture
async def h(db):
    return make_harness(db)


async def test_start_registers_user(h, db):
    await h.send("/start")
    assert (await db.get_user(1))["username"] == "alice"
    assert "Tracker" in h.last()


async def test_expense_full_flow_with_note(h, db):
    await h.send(kb.BTN_EXPENSE)
    await h.send("12,50")
    await h.click("cat:0")
    await h.send("lunch <b>")
    assert "Saved" in h.last() and "&lt;b&gt;" in h.last()  # HTML escaped
    (t,) = await db.recent(1)
    assert (t.kind, t.amount_cents, t.category, t.note) == (EXPENSE, 1250, "🍔 Food", "lunch <b>")
    assert t.tx_date == date.today().isoformat()


async def test_expense_skip_note(h, db):
    await h.send(kb.BTN_EXPENSE)
    await h.send("5")
    await h.click("cat:1")
    await h.click("note:skip")
    (t,) = await db.recent(1)
    assert t.note == "" and t.amount_cents == 500


async def test_income_flow_custom_source(h, db):
    await h.send(kb.BTN_INCOME)
    await h.send("1000")
    await h.click("cat:custom")
    await h.send("Side gig")
    (t,) = await db.recent(1)
    assert (t.kind, t.amount_cents, t.category) == (INCOME, 100000, "Side gig")


async def test_income_preset_source(h, db):
    await h.send(kb.BTN_INCOME)
    await h.send("200")
    await h.click("cat:0")
    (t,) = await db.recent(1)
    assert t.kind == INCOME and t.category == "💼 Salary"


@pytest.mark.parametrize("bad", ["abc", "-5", "0", "1.234", "nan"])
async def test_invalid_amount_keeps_state(h, db, bad):
    await h.send(kb.BTN_EXPENSE)
    await h.send(bad)
    assert "positive number" in h.last()
    await h.send("7")  # still in the amount step, now valid
    await h.click("cat:0")
    await h.click("note:skip")
    assert (await db.recent(1))[0].amount_cents == 700


async def test_cancel(h, db):
    await h.send(kb.BTN_EXPENSE)
    await h.send("10")
    await h.send("/cancel")
    await h.send("hello")  # no active state -> ignored, nothing saved
    assert await db.recent(1) == []


async def test_cancel_button(h, db):
    await h.send(kb.BTN_EXPENSE)
    await h.send("10")
    await h.click("cancel")
    assert h.last() == "Cancelled."
    assert await db.recent(1) == []


async def test_menu_button_interrupts_flow(h, db):
    await h.send(kb.BTN_EXPENSE)
    await h.send(kb.BTN_INCOME)   # switch mid-flow
    await h.send("50")
    await h.click("cat:0")
    assert (await db.recent(1))[0].kind == INCOME


async def test_bad_category_index_and_long_inputs(h, db):
    await h.send(kb.BTN_EXPENSE)
    await h.send("10")
    await h.click("cat:99")
    await h.click("cat:custom")
    await h.send("x" * 31)
    assert "1–30" in h.last()
    await h.send("Pets")
    await h.send("n" * 201)
    assert "too long" in h.last()
    assert await db.recent(1) == []
    await h.send("ok")
    assert (await db.recent(1))[0].category == "Pets"


async def test_history_and_delete(h, db):
    await h.send(kb.BTN_HISTORY)
    assert "No entries" in h.last()
    await db.upsert_user(1, "alice", "Alice")
    a =await db.add_transaction(1, EXPENSE, 100, "A")
    await db.add_transaction(1, INCOME, 200, "B")
    await h.send(kb.BTN_HISTORY)
    assert "A" in h.last() and "B" in h.last()
    await h.click(f"del:{a}")
    assert [t.category for t in await db.recent(1)] == ["B"]


async def test_cannot_delete_other_users_entry(h, db):
    await db.upsert_user(2, None, None)
    other = await db.add_transaction(2, EXPENSE, 100, "Secret")
    await h.click(f"del:{other}")
    assert len(await db.recent(2)) == 1
