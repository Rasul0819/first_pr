"""Monthly Excel dashboard generator (openpyxl, native Excel charts)."""
from __future__ import annotations

import asyncio
import calendar
from io import BytesIO

from openpyxl import Workbook
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from database import EXPENSE, Database, MonthSummary, Transaction

MONEY = '#,##0.00'
GREEN, RED, DARK, LIGHT, GREY = "2E7D32", "C62828", "263238", "ECEFF1", "607D8B"
THIN = Side(style="thin", color="CFD8DC")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def month_title(year: int, month: int) -> str:
    return f"{calendar.month_name[month]} {year}"


def _text(cell, value) -> None:
    """Write user-controlled text as a literal string (never as a formula)."""
    cell.value = value
    if isinstance(value, str):
        cell.data_type = "s"


def _header(ws: Worksheet, row: int, col: int, labels: list[str]) -> None:
    for i, label in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=label)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=DARK)
        c.alignment = Alignment(horizontal="center")
        c.border = BOX


def _kpi(ws: Worksheet, col: int, label: str, value, color: str, fmt: str | None = MONEY) -> None:
    ws.merge_cells(start_row=3, start_column=col, end_row=3, end_column=col + 1)
    ws.merge_cells(start_row=4, start_column=col, end_row=4, end_column=col + 1)
    lab, val = ws.cell(row=3, column=col, value=label), ws.cell(row=4, column=col, value=value)
    lab.font, val.font = Font(color=GREY, size=10, bold=True), Font(color=color, size=18, bold=True)
    lab.alignment = val.alignment = Alignment(horizontal="center", vertical="center")
    if fmt and not isinstance(value, str):
        val.number_format = fmt
    for r in (3, 4):
        for c in (col, col + 1):
            ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=LIGHT)
            ws.cell(row=r, column=c).border = BOX


def _breakdown(ws: Worksheet, row: int, col: int, title: str, head: str, data: dict[str, int]) -> int:
    """Write a ranked table; returns the last used row."""
    ws.cell(row=row, column=col, value=title).font = Font(bold=True, size=12, color=DARK)
    _header(ws, row + 1, col, [head, "Amount", "Share"])
    total = sum(data.values()) or 1
    r = row + 2
    for name, cents in data.items():
        _text(ws.cell(row=r, column=col), name)
        a = ws.cell(row=r, column=col + 1, value=cents / 100)
        a.number_format = MONEY
        s = ws.cell(row=r, column=col + 2, value=cents / total)
        s.number_format = "0.0%"
        for c in range(col, col + 3):
            ws.cell(row=r, column=c).border = BOX
        r += 1
    if not data:
        ws.cell(row=r, column=col, value="—").font = Font(color=GREY)
        r += 1
    return r - 1


def build_workbook(year: int, month: int, summary: MonthSummary,
                   txs: list[Transaction], owner: str = "") -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Dashboard"
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:H1")
    ws["A1"] = f"Monthly report — {month_title(year, month)}"
    ws["A1"].font = Font(size=20, bold=True, color=DARK)
    if owner:
        _text(ws["A2"], owner)
        ws["A2"].font = Font(color=GREY, italic=True)

    net = summary.net_cents
    rate = (net / summary.income_cents) if summary.income_cents else "n/a"
    _kpi(ws, 1, "TOTAL INCOME", summary.income_cents / 100, GREEN)
    _kpi(ws, 3, "TOTAL EXPENSES", summary.expense_cents / 100, RED)
    _kpi(ws, 5, "NET BALANCE", net / 100, GREEN if net >= 0 else RED)
    _kpi(ws, 7, "SAVINGS RATE", rate, GREEN if net >= 0 else RED, "0.0%")
    ws.row_dimensions[4].height = 32

    end1 = _breakdown(ws, 6, 1, "Expenses by category", "Category", summary.by_category)
    end2 = _breakdown(ws, 6, 5, "Income by source", "Source", summary.by_source)
    next_row = max(end1, end2) + 2

    days = calendar.monthrange(year, month)[1]
    daily = wb.create_sheet("Daily")
    _header(daily, 1, 1, ["Day", "Income", "Expenses"])
    inc, exp = [0] * (days + 1), [0] * (days + 1)
    for t in txs:
        (exp if t.kind == EXPENSE else inc)[int(t.tx_date[8:10])] += t.amount_cents
    for d in range(1, days + 1):
        daily.append([d, inc[d] / 100, exp[d] / 100])
        daily.cell(row=d + 1, column=2).number_format = MONEY
        daily.cell(row=d + 1, column=3).number_format = MONEY
    for col, w in zip("ABC", (8, 14, 14)):
        daily.column_dimensions[col].width = w

    if txs:
        if summary.by_category:
            pie = PieChart()
            pie.title = "Expenses by category"
            pie.add_data(Reference(ws, min_col=2, min_row=7, max_row=7 + len(summary.by_category)),
                         titles_from_data=True)
            pie.set_categories(Reference(ws, min_col=1, min_row=8, max_row=7 + len(summary.by_category)))
            pie.dataLabels = DataLabelList()
            pie.dataLabels.showPercent = True
            pie.height, pie.width = 8.5, 11
            ws.add_chart(pie, f"A{next_row}")
        bar = BarChart()
        bar.type, bar.title = "col", "Daily income vs expenses"
        bar.add_data(Reference(daily, min_col=2, max_col=3, min_row=1, max_row=days + 1), titles_from_data=True)
        bar.set_categories(Reference(daily, min_col=1, min_row=2, max_row=days + 1))
        bar.height, bar.width = 8.5, 14
        ws.add_chart(bar, f"E{next_row}")
    else:
        ws.cell(row=next_row, column=1, value="No transactions recorded this month.").font = Font(italic=True, color=GREY)

    for i in range(1, 9):
        ws.column_dimensions[get_column_letter(i)].width = 16

    tx_ws = wb.create_sheet("Transactions")
    _header(tx_ws, 1, 1, ["Date", "Type", "Category / Source", "Note", "Amount"])
    for r, t in enumerate(txs, start=2):
        tx_ws.cell(row=r, column=1, value=t.tx_date)
        tx_ws.cell(row=r, column=2, value="Expense" if t.kind == EXPENSE else "Income")
        _text(tx_ws.cell(row=r, column=3), t.category)
        _text(tx_ws.cell(row=r, column=4), t.note)
        amt = tx_ws.cell(row=r, column=5, value=(-t.amount_cents if t.kind == EXPENSE else t.amount_cents) / 100)
        amt.number_format = MONEY
        amt.font = Font(color=RED if t.kind == EXPENSE else GREEN)
    tx_ws.freeze_panes = "A2"
    tx_ws.auto_filter.ref = f"A1:E{max(len(txs) + 1, 2)}"
    for col, w in zip("ABCDE", (12, 10, 24, 40, 14)):
        tx_ws.column_dimensions[col].width = w
    return wb


def workbook_bytes(*args, **kwargs) -> bytes:
    buf = BytesIO()
    build_workbook(*args, **kwargs).save(buf)
    return buf.getvalue()


async def generate_monthly_report(db: Database, user_id: int, year: int, month: int,
                                  owner: str = "") -> tuple[str, bytes]:
    """Return (filename, xlsx bytes) for one user's month."""
    summary = await db.month_summary(user_id, year, month)
    txs = await db.month_transactions(user_id, year, month)
    data = await asyncio.to_thread(workbook_bytes, year, month, summary, txs, owner)
    return f"report_{year}-{month:02d}.xlsx", data
