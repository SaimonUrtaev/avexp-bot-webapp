import os

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SHEET_NAME = os.environ["SHEET_NAME"]
GOOGLE_CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")

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
    creds = Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet, spreadsheet.worksheet(SHEET_NAME)


def apply_row_format(spreadsheet, sheet, row_index):
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


def write_row(data: dict) -> int:
    """
    data = {client, fio, car, plate, date, comment}
    Возвращает номер строки (с 1).
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
    new_row_index = len(all_rows)

    sheet.append_row(row, value_input_option="RAW")
    apply_row_format(spreadsheet, sheet, new_row_index)

    return new_row_index + 1
