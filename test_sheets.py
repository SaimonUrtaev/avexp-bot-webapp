import os
from datetime import datetime

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv("/Users/mac/Desktop/WORK/Автоэкспертизы_БОТ/.env")

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

NUM_COLUMNS = 10

BORDER = {
    "style": "SOLID",
    "width": 1,
    "color": {"red": 0, "green": 0, "blue": 0, "alpha": 1},
}


def get_sheet():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet, spreadsheet.worksheet(SHEET_NAME)


def apply_row_format(spreadsheet, sheet, row_index):
    """Применяет рамки и выравнивание к строке (индекс с 0)."""
    sheet_id = sheet.id
    spreadsheet.batch_update(
        {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row_index,
                            "endRowIndex": row_index + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": NUM_COLUMNS,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "horizontalAlignment": "CENTER",
                                "verticalAlignment": "MIDDLE",
                                "wrapStrategy": "CLIP",
                                "borders": {
                                    "top": BORDER,
                                    "bottom": BORDER,
                                    "left": BORDER,
                                    "right": BORDER,
                                },
                            }
                        },
                        "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment,wrapStrategy,borders)",
                    }
                }
            ]
        }
    )


def write_row(data: dict):
    """
    data = {
        "client": "Название парка/клиента",
        "fio": "ФИО клиента",
        "car": "Марка ТС",
        "plate": "Гос номер",
        "date": "ДД.ММ.ГГГГ",
        "comment": "Комментарий",
    }
    """
    spreadsheet, sheet = get_sheet()

    row = [
        data.get("client", ""),
        data.get("car", ""),
        data.get("plate", ""),
        "",  # Статус Оплаты — вручную
        "",  # Статус НЭ — вручную
        "",  # Кто Ведет — вручную
        data.get("fio", ""),
        data.get("date", ""),
        "",  # Стоимость НЭ — вручную
        data.get("comment", ""),
    ]

    all_rows = sheet.get_all_values()
    new_row_index = len(all_rows)  # индекс с 0 для новой строки

    # RAW чтобы дата не превращалась в число
    sheet.append_row(row, value_input_option="RAW")
    apply_row_format(spreadsheet, sheet, new_row_index)

    return new_row_index + 1  # номер строки (с 1)


def test_write():
    row_num = write_row(
        {
            "client": "ТЕСТ",
            "fio": "Тестов Тест Тестович",
            "car": "Toyota Camry",
            "plate": "А000АА777",
            "date": datetime.now().strftime("%d.%m.%Y"),
            "comment": "Тестовая запись — можно удалить",
        }
    )
    print(f"✅ Запись в таблицу прошла успешно! Строка {row_num}")
    print(f"   Лист: {SHEET_NAME}")
    print(f"   Таблица: {SPREADSHEET_ID}")


if __name__ == "__main__":
    test_write()
