"""
Unit-тесты для function/main.py
Запуск: venv/bin/python -m pytest tests/ -v
"""

import base64
import json
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "function"))

# --- Заглушки зависимостей ---

# Мокаем sheets.write_row чтобы не обращаться к Google Sheets
import unittest.mock as mock

sheets_mock = types.ModuleType("sheets")
sheets_mock.write_row = mock.MagicMock(return_value=42)
sys.modules["sheets"] = sheets_mock

# Принудительно устанавливаем тестовые значения — setdefault не подходит,
# т.к. test_bot.py загружает реальный .env через config.py раньше нас.
os.environ["SECRET_TOKEN"] = "test-secret"
os.environ["BOT_TOKEN"] = "000:TEST"
os.environ["CHAT_ID"] = "-100123456"
os.environ.setdefault("SPREADSHEET_ID", "fake-id")
os.environ.setdefault("SHEET_NAME", "Лист1")

import main  # noqa: E402  # импортируем после установки env и заглушек

# ─── helpers ───────────────────────────────────────────────────────────────────


def make_event(body: dict, token: str = "test-secret") -> dict:
    return {
        "headers": {"x-secret-token": token},
        "body": json.dumps(body, ensure_ascii=False),
    }


VALID_BODY = {
    "client": "Тест Парк",
    "fio": "Иванов Иван",
    "car": "Kia Rio",
    "plate": "А000АА797",
    "date": "16.06.2026",
    "comment": "",
}


# ─── Тесты handler ─────────────────────────────────────────────────────────────


def test_valid_request_returns_200():
    sheets_mock.write_row.return_value = 5
    resp = main.handler(make_event(VALID_BODY), {})
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ok"] is True
    assert body["row"] == 5


def test_wrong_token_returns_403():
    resp = main.handler(make_event(VALID_BODY, token="wrong"), {})
    assert resp["statusCode"] == 403
    assert "Forbidden" in resp["body"]


def test_missing_token_returns_403():
    event = {"headers": {}, "body": json.dumps(VALID_BODY)}
    resp = main.handler(event, {})
    assert resp["statusCode"] == 403


def test_invalid_json_returns_400():
    event = {"headers": {"x-secret-token": "test-secret"}, "body": "не json{{{"}
    resp = main.handler(event, {})
    assert resp["statusCode"] == 400


def test_missing_required_field_returns_400():
    body = {**VALID_BODY, "plate": ""}  # пустой гос. номер
    resp = main.handler(make_event(body), {})
    assert resp["statusCode"] == 400
    assert "plate" in resp["body"]


def test_all_required_fields_missing_returns_400():
    resp = main.handler(make_event({"comment": "только комментарий"}), {})
    assert resp["statusCode"] == 400
    data = json.loads(resp["body"])
    for field in ["client", "car", "plate", "date"]:
        assert field in data["error"]


def test_sheets_error_returns_500():
    sheets_mock.write_row.side_effect = Exception("Google API недоступен")
    resp = main.handler(make_event(VALID_BODY), {})
    assert resp["statusCode"] == 500
    sheets_mock.write_row.side_effect = None
    sheets_mock.write_row.return_value = 42


def test_photos_field_not_required():
    """Заявка без фото должна проходить."""
    sheets_mock.write_row.return_value = 7
    body = {**VALID_BODY}  # без поля photos
    resp = main.handler(make_event(body), {})
    assert resp["statusCode"] == 200


def test_response_has_content_type_header():
    sheets_mock.write_row.return_value = 1
    resp = main.handler(make_event(VALID_BODY), {})
    assert resp.get("headers", {}).get("Content-Type") == "application/json"


# ─── Тесты send_one_photo ───────────────────────────────────────────────────────


def test_send_one_photo_caption_strips_crlf():
    """Caption с \r\n не должен ломать MIME-структуру."""
    tiny_jpeg = base64.b64decode(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkS"
        "Ew8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJ"
        "CQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
        "MjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/"
        "EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAA"
        "AAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AJUA/9k="
    )
    malicious_caption = "нормальный текст\r\n--boundary--\r\nвредная часть"

    called_parts = {}

    def fake_urlopen(req, timeout=None):
        called_parts["data"] = req.data
        called_parts["headers"] = req.headers
        resp = mock.MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = mock.MagicMock(return_value=False)
        return resp

    with mock.patch.object(main.urllib.request, "urlopen", fake_urlopen):
        main.send_one_photo(tiny_jpeg, malicious_caption)

    body_str = called_parts["data"].decode("utf-8", errors="replace")
    # caption должен быть в теле, но \r\n внутри него заменены пробелами
    # (иначе MIME-структура была бы сломана)
    caption_start = body_str.index('name="caption"\r\n\r\n') + len(
        'name="caption"\r\n\r\n'
    )
    caption_end = body_str.index("\r\n--", caption_start)
    caption_value = body_str[caption_start:caption_end]
    assert (
        "\r\n" not in caption_value
    ), f"\\r\\n попал внутрь caption: {caption_value!r}"


def test_send_photos_to_chat_continues_after_one_failure():
    """Если одно фото не отправилось — остальные идут дальше."""
    call_count = {"n": 0}

    def fake_send_one(img_bytes, cap):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("сеть упала")

    with mock.patch.object(main, "send_one_photo", fake_send_one):
        # 3 фото — второе упадёт, но третье должно дойти
        photos = ["data:image/jpeg;base64,/9j/fake=="] * 3
        main.send_photos_to_chat(photos, "заголовок")

    assert call_count["n"] == 3  # все три попытки были сделаны
