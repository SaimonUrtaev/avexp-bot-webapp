"""
Unit-тесты для function/main.py
Запуск: venv/bin/python -m pytest tests/ -v
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import types
from urllib.parse import urlencode

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


# ─── Тесты _verify_init_data ───────────────────────────────────────────────────

TEST_BOT = "000:TEST"


def _make_init_data(bot_token: str = TEST_BOT, age_seconds: int = 0, extra: dict = None) -> str:
    """Генерирует подписанный initData как это делает Telegram."""
    params = {
        "auth_date": str(int(time.time()) - age_seconds),
        "user": '{"id":123456,"first_name":"Test"}',
        "query_id": "AAHdF6IQAAAAAN0XohA",
    }
    if extra:
        params.update(extra)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_val = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_val
    return urlencode(params)


def test_verify_init_data_valid():
    """Корректно подписанный initData (свежий) — возвращает True."""
    init_data = _make_init_data()
    assert main._verify_init_data(init_data, TEST_BOT) is True


def test_verify_init_data_wrong_bot_token():
    """initData подписан другим токеном — возвращает False."""
    init_data = _make_init_data(bot_token="999:WRONG")
    assert main._verify_init_data(init_data, TEST_BOT) is False


def test_verify_init_data_tampered_hash():
    """Последний символ hash изменён — возвращает False."""
    init_data = _make_init_data()
    last = init_data[-1]
    tampered = init_data[:-1] + ("0" if last != "0" else "1")
    assert main._verify_init_data(tampered, TEST_BOT) is False


def test_verify_init_data_expired():
    """auth_date старше max_age — возвращает False."""
    init_data = _make_init_data(age_seconds=7200)  # 2 часа > 1 часа (дефолт)
    assert main._verify_init_data(init_data, TEST_BOT) is False


def test_verify_init_data_future_date():
    """auth_date в будущем — возвращает False (отрицательный diff не должен проходить)."""
    params = {
        "auth_date": str(int(time.time()) + 3600 * 24 * 365),  # +1 год
        "user": '{"id":123456,"first_name":"Test"}',
        "query_id": "AAHdF6IQAAAAAN0XohA",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", TEST_BOT.encode(), hashlib.sha256).digest()
    hash_val = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_val
    init_data = urlencode(params)
    assert main._verify_init_data(init_data, TEST_BOT) is False


def test_verify_init_data_missing_hash():
    """initData без поля hash — возвращает False."""
    params = {"auth_date": str(int(time.time())), "user": '{"id":1}'}
    init_data = urlencode(params)  # нет hash
    assert main._verify_init_data(init_data, TEST_BOT) is False


def test_verify_init_data_non_string_returns_false():
    """Нестроковый init_data (dict, list) — возвращает False, не падает."""
    assert main._verify_init_data({}, TEST_BOT) is False
    assert main._verify_init_data([], TEST_BOT) is False
    assert main._verify_init_data(None, TEST_BOT) is False


def test_handler_accepts_valid_init_data():
    """handler принимает запрос с валидным initData (без SECRET_TOKEN в заголовке)."""
    sheets_mock.write_row.return_value = 55
    # Временно убираем SECRET_TOKEN чтобы проверить initData-путь
    orig = main.SECRET_TOKEN
    main.SECRET_TOKEN = ""
    try:
        init_data = _make_init_data()
        body = {**VALID_BODY, "init_data": init_data}
        event = {"httpMethod": "POST", "headers": {}, "body": json.dumps(body)}
        with mock.patch.object(main, "send_text_to_chat"), \
             mock.patch.object(main, "send_button_to_chat"):
            resp = main.handler(event, {})
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"])["ok"] is True
    finally:
        main.SECRET_TOKEN = orig


def test_handler_rejects_tampered_init_data():
    """handler отклоняет запрос с поддельным initData."""
    orig = main.SECRET_TOKEN
    main.SECRET_TOKEN = ""
    try:
        init_data = _make_init_data()
        tampered = init_data[:-1] + ("0" if init_data[-1] != "0" else "1")
        body = {**VALID_BODY, "init_data": tampered}
        event = {"httpMethod": "POST", "headers": {}, "body": json.dumps(body)}
        resp = main.handler(event, {})
        assert resp["statusCode"] == 403
    finally:
        main.SECRET_TOKEN = orig


# ─── Тесты _send_single_photo / send_photos_to_chat ────────────────────────────


def test_send_single_photo_builds_valid_multipart():
    """_send_single_photo строит корректный multipart с полями chat_id и photo."""
    tiny_jpeg = b"\xff\xd8\xff\xe0fake_jpeg"
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["data"] = req.data
        resp = mock.MagicMock()
        resp.__enter__ = lambda s: s
        resp.__exit__ = mock.MagicMock(return_value=False)
        return resp

    with mock.patch.object(main.urllib.request, "urlopen", fake_urlopen):
        main._send_single_photo(tiny_jpeg)

    body = captured["data"].decode("latin-1")
    assert 'name="chat_id"' in body
    assert 'name="photo"' in body
    assert "Content-Type: image/jpeg" in body
    assert tiny_jpeg.decode("latin-1") in body


def test_send_photos_to_chat_continues_after_group_failure():
    """Если одна группа упала — оставшиеся группы отправляются дальше."""
    call_count = {"n": 0}

    def fake_send_group(group):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OSError("сеть упала")

    tiny_b64 = base64.b64encode(b"\xff\xd8\xff\xe0fake").decode()
    photos = [tiny_b64] * 13  # 2 группы: 10 + 3

    with mock.patch.object(main, "_send_media_group", fake_send_group):
        errors = main.send_photos_to_chat(photos)

    assert call_count["n"] == 2
    assert len(errors) == 1


# ─── Тесты: порядок текст → фото → кнопка ────────────────────────────────────


def test_11_photos_sends_two_batches():
    """11 фото → sendMediaGroup(10) + _send_single_photo(1)."""
    group_calls = []
    single_calls = []

    with mock.patch.object(main, "_send_media_group", lambda g: group_calls.append(len(g))), \
         mock.patch.object(main, "_send_single_photo", lambda img: single_calls.append(1)):
        tiny_b64 = base64.b64encode(b"\xff\xd8\xff\xe0fake").decode()
        main.send_photos_to_chat([tiny_b64] * 11)

    assert group_calls == [10]
    assert single_calls == [1]


def test_10_photos_sends_one_batch():
    """Ровно 10 фото → только один вызов sendMediaGroup."""
    group_calls = []

    with mock.patch.object(main, "_send_media_group", lambda g: group_calls.append(len(g))):
        tiny_b64 = base64.b64encode(b"\xff\xd8\xff\xe0fake").decode()
        main.send_photos_to_chat([tiny_b64] * 10)

    assert group_calls == [10]


def test_order_text_photos_button():
    """Порядок: текст → фото → кнопка."""
    call_order = []

    sheets_mock.write_row.return_value = 99
    tiny_b64 = base64.b64encode(b"\xff\xd8\xff\xe0fake").decode()
    body = {**VALID_BODY, "photos": [tiny_b64]}

    with mock.patch.object(main, "send_text_to_chat", lambda t: call_order.append("text")), \
         mock.patch.object(main, "send_photos_to_chat", lambda p: (call_order.append("photos"), [])[1]), \
         mock.patch.object(main, "send_button_to_chat", lambda: call_order.append("button")):
        main.handler(make_event(body), {})

    assert call_order == ["text", "photos", "button"], f"Ожидался порядок text→photos→button, получили: {call_order}"


def test_button_sent_even_when_photos_fail():
    """Если фото упали — кнопка всё равно отправляется."""
    button_sent = {"v": False}

    sheets_mock.write_row.return_value = 12
    tiny_b64 = base64.b64encode(b"\xff\xd8\xff\xe0fake").decode()
    body = {**VALID_BODY, "photos": [tiny_b64]}

    with mock.patch.object(main, "send_text_to_chat"), \
         mock.patch.object(main, "send_button_to_chat", lambda: button_sent.update({"v": True})), \
         mock.patch.object(main, "send_photos_to_chat", return_value=["ошибка"]):
        resp = main.handler(make_event(body), {})

    assert button_sent["v"] is True
    data = json.loads(resp["body"])
    assert data["ok"] is True
    assert "photo_error" in data


def test_response_ok_true_with_photo_error():
    """При ошибке фото ответ ok=True — данные уже записаны в таблицу."""
    sheets_mock.write_row.return_value = 3
    tiny_b64 = base64.b64encode(b"\xff\xd8\xff\xe0fake").decode()
    body = {**VALID_BODY, "photos": [tiny_b64]}

    with mock.patch.object(main, "send_text_to_chat"), \
         mock.patch.object(main, "send_button_to_chat"), \
         mock.patch.object(main, "send_photos_to_chat", return_value=["timeout"]):
        resp = main.handler(make_event(body), {})

    assert resp["statusCode"] == 200
    data = json.loads(resp["body"])
    assert data["ok"] is True
    assert data["row"] == 3


def test_text_sent_for_both_with_and_without_photos():
    """Текст уведомления отправляется всегда — с фото и без."""
    for has_photos in [True, False]:
        text_calls = []
        sheets_mock.write_row.return_value = 7
        tiny_b64 = base64.b64encode(b"\xff\xd8\xff\xe0fake").decode()
        body = {**VALID_BODY, **({"photos": [tiny_b64]} if has_photos else {})}

        with mock.patch.object(main, "send_text_to_chat", lambda t: text_calls.append(t)), \
             mock.patch.object(main, "send_photos_to_chat", return_value=[]), \
             mock.patch.object(main, "send_button_to_chat"):
            main.handler(make_event(body), {})

        assert len(text_calls) == 1, f"текст должен отправляться (has_photos={has_photos})"
        assert "Заявка НЭ" in text_calls[0]
