from types import SimpleNamespace

import google_sheets


class FakeWorksheet:
    def __init__(self, rows):
        self._rows = rows  # list of rows (first row = header)

    def get_all_values(self):
        return list(self._rows)

    def append_row(self, row, value_input_option=None):
        self._rows.append(row)


class FakeClient:
    def __init__(self, worksheet):
        self._worksheet = worksheet

    def open_by_key(self, key):
        return SimpleNamespace(
            worksheet=lambda name: self._worksheet,
            add_worksheet=lambda title, rows, cols: self._worksheet,
        )


class FakeCredentials:
    pass


def _patch(monkeypatch, worksheet):
    monkeypatch.setattr(
        google_sheets.Credentials,
        "from_service_account_file",
        classmethod(lambda cls, path, scopes=None: FakeCredentials()),
    )
    monkeypatch.setattr(
        google_sheets.gspread,
        "Client",
        lambda auth: FakeClient(worksheet),
    )


def test_append_loss_empty_sheet(monkeypatch):
    """Первая запись в пустой таблице (только заголовок) → номер 1."""
    fake_ws = FakeWorksheet([["№", "ПАРК"]])  # только заголовок
    _patch(monkeypatch, fake_ws)

    number = google_sheets.append_loss({"park": "TEST", "brand": "BRAND"})

    assert number == 1
    assert len(fake_ws._rows) == 2  # заголовок + новая строка
    assert fake_ws._rows[-1][0] == 1


def test_append_loss_existing_rows(monkeypatch):
    """При наличии 3 строк данных → новая получает номер 4."""
    fake_ws = FakeWorksheet([["№"], ["1"], ["2"], ["3"]])
    _patch(monkeypatch, fake_ws)

    number = google_sheets.append_loss({"park": "P2"})

    assert number == 4


def test_append_loss_fields_written(monkeypatch):
    """Все поля записываются в правильные колонки."""
    fake_ws = FakeWorksheet([["header"]])
    _patch(monkeypatch, fake_ws)

    google_sheets.append_loss({
        "park": "PARK",
        "brand": "BRAND",
        "grz": "A123BC",
        "year": "2020",
        "policy": "POL",
        "date_dtp": "01.01.2026",
        "insurance": "INS",
    })

    added = fake_ws._rows[-1]
    assert added[1] == "PARK"
    assert added[2] == "BRAND"
    assert added[3] == "A123BC"
    assert added[4] == "2020"
    assert added[5] == "POL"
    assert added[6] == "01.01.2026"
    assert added[10] == "INS"
