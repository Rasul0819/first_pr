"""Guards: all user-facing text lives in locales/kaa.py and is Karakalpak (Latin)."""
import ast
import re
from pathlib import Path

import pytest

from locales import kaa as T

ROOT = Path(__file__).resolve().parent.parent
# Files whose literals must contain no human-readable text (grows per stage).
TRANSLATED_FILES = ["handlers/user.py", "keyboards/user.py",
                    "handlers/admin.py", "keyboards/admin.py"]

ENGLISH = {
    "expense", "expenses", "income", "report", "cancel", "cancelled", "category", "categories",
    "total", "balance", "net", "users", "statistics", "history", "saved", "deleted", "amount",
    "note", "skip", "choose", "enter", "usage", "month", "last", "this", "welcome", "source",
    "transactions", "daily", "share", "savings", "rate", "date", "type", "admin", "panel",
    "stats", "recent", "paid", "active", "found", "please", "invalid", "your", "the", "and",
}


def _human_literals(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(
                    getattr(node.body[0], "value", None), ast.Constant):
                docstrings.add(id(node.body[0].value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            text = re.sub(r"<[^>]+>|\{[^}]*\}", "", node.value)
            if re.search(r"\s", text.strip()) and re.search(r"[A-Za-z]{3,}", text):
                yield node.lineno, node.value


@pytest.mark.parametrize("rel", TRANSLATED_FILES)
def test_no_literal_text_outside_locale_file(rel):
    found = list(_human_literals(ROOT / rel))
    assert not found, f"{rel} has hard-coded text: {found}"


def _all_strings():
    for name in dir(T):
        v = getattr(T, name)
        if name.isupper():
            for s in (v if isinstance(v, list) else list(v.values()) if isinstance(v, dict) else [v]):
                yield name, s


def test_locale_has_no_english_words():
    bad = []
    for name, s in _all_strings():
        words = re.findall(r"[A-Za-zÀ-žıǴǵŃńÍíÓóÚúÁá]+", re.sub(r"<[^>]+>|\{[^}]*\}|/\w+", "", s))  # commands like /cancel stay
        bad += [(name, w) for w in words if w.lower() in ENGLISH]
    assert not bad, bad


def test_locale_is_latin_script_not_cyrillic():
    for name, s in _all_strings():
        assert not re.search(r"[Ѐ-ӿ]", s), name


def test_months_complete():
    assert len(T.MONTHS) == 12 and len(set(T.MONTHS)) == 12


def test_placeholders_are_valid_format_fields():
    import string
    for name, s in _all_strings():
        for _, field, _, _ in string.Formatter().parse(s):
            assert field is None or field.isidentifier(), (name, field)


def test_karakalpak_characters_survive_roundtrip():
    sample = "ǵ ń ı ó ú á í Ǵ Ń Í Ó Ú Á"
    assert sample.encode("utf-8").decode("utf-8") == sample
    assert "ǵ" in T.BTN_EXPENSE and "ı" in T.WELCOME
