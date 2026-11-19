import importlib
from datetime import date
from io import BytesIO

import pytest
import pytest_asyncio
from openpyxl import load_workbook

from config import Settings
from database import EXPENSE, INCOME
from main import build_dispatcher
from reports.monthly import generate_monthly_report
from utils import month_title
from reports.scheduler import seconds_until_next_run, send_monthly_reports
from tests.helpers import make_harness
from keyboards import user as kb
from locales import kaa as T
from datetime import datetime


@pytest_asyncio.fixture
async def seeded(db):
    await db.upsert_user(1, "alice", "Alice")
    d = date(2025, 3, 5)
    await db.add_transaction(1, INCOME, 300000, "Salary", "", d)
    await db.add_transaction(1, INCOME, 50000, "Gift", "", date(2025, 3, 31))
    await db.add_transaction(1, EXPENSE, 120000, "Rent", "March", d)
    await db.add_transaction(1, EXPENSE, 30050, "Food", "=1+1", date(2025, 3, 6))
    await db.add_transaction(1, EXPENSE, 9999, "Food", "", date(2025, 4, 1))  # excluded
    return db


async def test_workbook_contents(seeded):
    name, data = await generate_monthly_report(seeded, 1, 2025, 3, owner="Alice")
    assert name == "report_2025-03.xlsx"
    wb = load_workbook(BytesIO(data))
    assert wb.sheetnames == ["Dashboard", "Daily", "Transactions"]
    ws = wb["Dashboard"]
    assert "2025-jıl Mart" in ws["A1"].value
    assert ws["A4"].value == 3500.0          # income
    assert ws["C4"].value == 1500.5          # expenses
    assert ws["E4"].value == pytest.approx(1999.5)  # net
    assert ws["G4"].value == pytest.approx(1999.5 / 3500)
    cats = {ws.cell(row=r, column=1).value: ws.cell(row=r, column=2).value for r in (8, 9)}
    assert cats == {"Rent": 1200.0, "Food": 300.5}
    srcs = {ws.cell(row=r, column=5).value: ws.cell(row=r, column=6).value for r in (8, 9)}
    assert srcs == {"Salary": 3000.0, "Gift": 500.0}
    assert len(ws._charts) == 2


async def test_transactions_sheet_and_formula_injection(seeded):
    _, data = await generate_monthly_report(seeded, 1, 2025, 3)
    tx = load_workbook(BytesIO(data))["Transactions"]
    rows = list(tx.iter_rows(min_row=2, values_only=True))
    assert len(rows) == 4                      # April entry excluded
    note_cell = next(c for r in tx.iter_rows(min_row=2) for c in r if c.value == "=1+1")
    assert note_cell.data_type == "s"          # stored as text, not a formula
    assert sum(r[4] for r in rows) == pytest.approx(1999.5)


async def test_daily_sheet(seeded):
    _, data = await generate_monthly_report(seeded, 1, 2025, 3)
    d = load_workbook(BytesIO(data))["Daily"]
    assert d.max_row == 32                      # header + 31 days
    assert d["B6"].value == 3000.0 and d["C6"].value == 1200.0   # day 5
    assert d["B32"].value == 500.0


async def test_empty_month_report(db):
    await db.upsert_user(1, None, None)
    _, data = await generate_monthly_report(db, 1, 2024, 2)   # leap year
    wb = load_workbook(BytesIO(data))
    ws = wb["Dashboard"]
    assert ws["A4"].value == 0 and ws["G4"].value == "n/a"
    assert "No transactions" in ws["A10"].value
    assert wb["Daily"].max_row == 30            # 29 days + header


async def test_negative_net_and_only_income(db):
    await db.upsert_user(1, None, None)
    await db.add_transaction(1, EXPENSE, 500, "X", tx_date=date(2025, 12, 31))
    _, data = await generate_monthly_report(db, 1, 2025, 12)
    ws = load_workbook(BytesIO(data))["Dashboard"]
    assert ws["E4"].value == -5.0
    assert ws["E4"].font.color.rgb.endswith("C62828")


def test_month_title():
    assert month_title(2025, 3) == "2025-jıl Mart"


# ---- bot integration
@pytest_asyncio.fixture
async def h(seeded):
    return make_harness(seeded)


async def test_report_command_sends_document(h):
    await h.send("/report 2025-03")
    (doc,) = h.documents()
    assert doc.document.filename == "report_2025-03.xlsx"
    assert "3 500.00" in doc.caption and "1 999.50" in doc.caption


async def test_report_button_flow_current_month(h):
    await h.send(kb.BTN_REPORT)
    assert h.last() == T.REPORT_WHICH_MONTH
    await h.click("report:current")
    await h.click("report:previous")
    assert len(h.documents()) == 2


@pytest.mark.parametrize("arg", ["2025-13", "abc", "2025", "1999-01", "2025-03-01"])
async def test_report_bad_args(h, arg):
    await h.send(f"/report {arg}")
    assert h.last() == T.REPORT_USAGE and not h.documents()


async def test_scheduler_sends_only_to_active_users(seeded):
    await seeded.upsert_user(2, None, None)   # no March activity
    h = make_harness(seeded)
    n = await send_monthly_reports(h.bot, seeded, today=date(2025, 4, 1))
    assert n == 1
    (doc,) = h.documents()
    assert doc.chat_id == 1 and doc.document.filename == "report_2025-03.xlsx"


async def test_scheduler_january_rolls_back_year(seeded):
    await seeded.add_transaction(1, INCOME, 100, "Y", tx_date=date(2024, 12, 15))
    h = make_harness(seeded)
    assert await send_monthly_reports(h.bot, seeded, today=date(2025, 1, 1)) == 1
    assert h.documents()[0].document.filename == "report_2024-12.xlsx"


def test_seconds_until_next_run():
    assert seconds_until_next_run(datetime(2025, 1, 1, 8, 0)) == 3600
    assert seconds_until_next_run(datetime(2025, 1, 1, 9, 0)) == 86400
