import pytest
from types import SimpleNamespace

import google_sheets


class FakeWorksheet:
    def __init__(self, values):
        self._values = values

    def col_values(self, idx):
        return self._values

    def append_row(self, row, value_input_option=None):
        self._values.append(str(row[0]))


class FakeSheet:
    def __init__(self, values):
        self._worksheet = FakeWorksheet(values)

    def worksheet(self, name):
        return self._worksheet


class FakeClient:
    def __init__(self, sheet):
        self.sheet = sheet

    def open_by_key(self, key):
        return self.sheet


class FakeCredentials:
    pass


def test_get_next_number_empty(monkeypatch):
    google_sheets.reset_sheet_cache()
    fake_sheet = FakeWorksheet([""])
    monkeypatch.setattr(
        google_sheets.Credentials,
        "from_service_account_file",
        classmethod(lambda cls, path, scopes=None: FakeCredentials()),
    )
    monkeypatch.setattr(
        google_sheets.gspread,
        "Client",
        lambda auth: FakeClient(SimpleNamespace(worksheet=lambda name: fake_sheet)),
    )

    assert google_sheets.get_next_number() == 1


def test_get_next_number_with_values(monkeypatch):
    google_sheets.reset_sheet_cache()
    fake_sheet = FakeWorksheet(["", "1", "5", "invalid", "3"])
    monkeypatch.setattr(
        google_sheets.Credentials,
        "from_service_account_file",
        classmethod(lambda cls, path, scopes=None: FakeCredentials()),
    )
    monkeypatch.setattr(
        google_sheets.gspread,
        "Client",
        lambda auth: FakeClient(SimpleNamespace(worksheet=lambda name: fake_sheet)),
    )

    assert google_sheets.get_next_number() == 6


def test_append_loss_calls_append_row(monkeypatch):
    google_sheets.reset_sheet_cache()
    fake_worksheet = FakeWorksheet([""])
    fake_sheet = SimpleNamespace(worksheet=lambda name: fake_worksheet)
    monkeypatch.setattr(
        google_sheets.Credentials,
        "from_service_account_file",
        classmethod(lambda cls, path, scopes=None: FakeCredentials()),
    )
    monkeypatch.setattr(
        google_sheets.gspread,
        "Client",
        lambda auth: FakeClient(fake_sheet),
    )

    number = google_sheets.append_loss({
        "park": "TEST",
        "brand": "BRAND",
        "grz": "XYZ123",
        "year": "2020",
        "policy": "POLICY",
        "date_dtp": "01.01.2026",
        "insurance": "INS",
    })

    assert number == 1
    assert fake_worksheet._values[-1][0] == "1"
