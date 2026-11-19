import config


def test_settings_parse_admin_ids(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "x")
    monkeypatch.setenv("ADMIN_IDS", "1, 2,abc")
    s = config.load_settings()
    assert s.admin_ids == frozenset({1, 2})
    assert s.bot_token == "x"
