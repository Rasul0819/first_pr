"""Qaraqalpaq tili (Karakalpak, Latin script) — all user-facing strings.

Templates use str.format placeholders; HTML tags are Telegram HTML.
Edit wording here only; handlers/keyboards/reports contain no literal text.
"""

# ------------------------------------------------------------------ months
MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
          "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"]
MONTH_TITLE = "{year}-jıl {month}"

# ------------------------------------------------------------------ menu buttons
BTN_EXPENSE = "➖ Shıǵın"
BTN_INCOME = "➕ Kirim"
BTN_REPORT = "📊 Esabat"
BTN_HISTORY = "🕘 Tariyx"

# ------------------------------------------------------------------ categories / sources
EXPENSE_CATEGORIES = ["🍔 Awqat", "🚌 Transport", "🏠 Turaq jay", "🛍 Satıp alıwlar",
                      "💊 Densawlıq", "🎬 Dem alıs", "📚 Bilim", "📦 Basqa"]
INCOME_SOURCES = ["💼 Jalaqı", "🧾 Frilans", "🎁 Sawǵa", "📈 Investiciya", "📦 Basqa"]

# ------------------------------------------------------------------ inline buttons
BTN_CUSTOM = "✏️ Ózim jazaman…"
BTN_CANCEL = "✖️ Biykar etiw"
BTN_SKIP_NOTE = "⏭ Ótkizip jiberiw"
BTN_REPORT_CURRENT = "Usı ay"
BTN_REPORT_PREVIOUS = "Ótken ay"

# ------------------------------------------------------------------ welcome / generic
WELCOME = (
    "👋 <b>Kirim hám shıǵın esabı</b>\n\n"
    "Kúndelik kirim hám shıǵınlarıńızdı jazıp barıń, ay sayın Excel esabatın alıń.\n"
    "Tómendegi menyudan paydalanıń. /cancel — háreketti biykar etedi."
)
CANCELLED = "Biykar etildi."
UNKNOWN_OPTION = "Belgisiz tańlaw"

# ------------------------------------------------------------------ add flow
ASK_AMOUNT_EXPENSE = "Shıǵın summasın kiritiń (mısalı: <code>12.50</code>):"
ASK_AMOUNT_INCOME = "Kirim summasın kiritiń (mısalı: <code>12.50</code>):"
BAD_AMOUNT = "❗ Oń san kiritiń, nokattan keyin eń kóbi 2 belgi (mısalı: <code>12.50</code>)."
CHOOSE_CATEGORY = "Summa: <b>{amount}</b>\nKategoriyanı tańlań:"
CHOOSE_SOURCE = "Summa: <b>{amount}</b>\nKirim deregin tańlań:"
CUSTOM_PROMPT_CATEGORY = "Kategoriya atın jazıń (eń kóbi {max} belgi):"
CUSTOM_PROMPT_SOURCE = "Derek atın jazıń (eń kóbi {max} belgi):"
BAD_NAME = "❗ Atı 1–{max} belgi aralıǵında bolıwı kerek."
ASK_NOTE = "Kategoriya: <b>{category}</b>\nEskertpe jazıń (yamasa ótkizip jiberiń):"
NOTE_TOO_LONG = "❗ Eskertpe júdá uzın (eń kóbi {max} belgi)."
SAVED = "✅ Saqlandı: <b>{sign}{amount}</b> · {category}"
SAVED_NOTE_LINE = "\n📝 {note}"

# ------------------------------------------------------------------ history
HISTORY_EMPTY = "Házirshe jazıwlar joq. ➖ Shıǵın yamasa ➕ Kirim arqalı qosıń."
HISTORY_TITLE = "🕘 <b>Sońǵı jazıwlar</b> (óshiriw ushın basıń):"
DELETED = "Óshirildi"
ALREADY_DELETED = "Aldın óshirilgen"

# ------------------------------------------------------------------ report (chat side)
REPORT_WHICH_MONTH = "Qaysı ay ushın esabat kerek?"
REPORT_GENERATING = "Tayarlanbaqta…"
REPORT_USAGE = "Qollanıw: <code>/report</code> yamasa <code>/report 2025-03</code>"
REPORT_CAPTION = (
    "📊 <b>{title}</b>\n"
    "Kirim: <b>{income}</b>\n"
    "Shıǵın: <b>{expense}</b>\n"
    "Qaldıq: <b>{net}</b>"
)
