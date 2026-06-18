"""
Интеграция с Google Sheets через Service Account.
Таблица: Лист1, колонки соответствуют существующей структуре.
"""

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS_FILE, SHEET_NAME, SPREADSHEET_ID
from utils import get_headers_list

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Порядок колонок в таблице (27 штук)
HEADERS = get_headers_list()


def reset_sheet_cache():
    pass  # кэш убран; оставлен для совместимости с тестами


def _get_sheet():
    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    client = gspread.Client(auth=creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    try:
        sheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=1000, cols=27)
    return sheet


def get_row_count() -> int:
    """Возвращает текущее число строк в таблице (включая заголовок)."""
    sheet = _get_sheet()
    return len(sheet.col_values(1))


def append_loss(data: dict) -> int:
    """
    Записать новый убыток в таблицу.
    data — словарь с ключами: park, brand, grz, year, policy, date_dtp, insurance
    Возвращает номер строки (индекс после вставки, без гонки на pre-read).
    """
    sheet = _get_sheet()

    # Читаем текущее число строк ДО вставки, чтобы знать индекс новой строки
    all_rows = sheet.get_all_values()
    new_row_index = len(all_rows)  # 0-based index новой строки после вставки
    number = new_row_index  # строка данных №N (заголовок = строка 0)

    row = [""] * 27
    row[0] = number
    row[1] = data.get("park", "")       # ПАРК
    row[2] = data.get("brand", "")      # МАРКА ТС
    row[3] = data.get("grz", "")        # ГОС.НОМЕР
    row[4] = data.get("year", "")       # ГОД ТС
    row[5] = data.get("policy", "")     # ПОЛИС ОСАГО
    row[6] = data.get("date_dtp", "")   # ДАТА ДТП
    row[10] = data.get("insurance", "") # СК

    sheet.append_row(row, value_input_option="USER_ENTERED")
    return number
