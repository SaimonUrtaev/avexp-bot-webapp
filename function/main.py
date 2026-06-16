import base64
import html
import json
import os
import urllib.request
import uuid

from sheets import write_row

SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _send_single_photo(img_bytes: bytes) -> None:
    """Отправляет одно фото через sendPhoto."""
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{CHAT_ID}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="photo.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + img_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{TG_API}/sendPhoto",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=30):
        pass


def _send_media_group(photos_bytes: list) -> None:
    """Отправляет группу 2–10 фото через sendMediaGroup (один альбом)."""
    boundary = uuid.uuid4().hex
    media = [{"type": "photo", "media": f"attach://file_{i}"} for i in range(len(photos_bytes))]

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{CHAT_ID}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"\r\n\r\n'
        f"{json.dumps(media, ensure_ascii=False)}\r\n"
    ).encode()

    for i, img_bytes in enumerate(photos_bytes):
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file_{i}"; filename="photo.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode() + img_bytes + b"\r\n"

    body += f"--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{TG_API}/sendMediaGroup",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=30):
        pass


def send_text_to_chat(text: str):
    """Отправляет текстовое сообщение в Telegram группу."""
    payload = json.dumps(
        {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        ensure_ascii=False,
    ).encode()
    req = urllib.request.Request(
        f"{TG_API}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15):
        pass


WEBAPP_URL = "https://t.me/AvExp24_bot/newapp"


def send_button_to_chat():
    """Отправляет кнопку 'Новая заявка на НЭ' в группу."""
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": "➕ Новая заявка",
        "reply_markup": {
            "inline_keyboard": [[{
                "text": "📋 Новая заявка на НЭ",
                "url": WEBAPP_URL,
            }]]
        },
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"{TG_API}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15):
        pass


def _e(value: str) -> str:
    """Экранирует HTML-спецсимволы в пользовательском вводе."""
    return html.escape(str(value))


def build_notification(row_num: int, data: dict) -> str:
    """Формирует текст уведомления о заявке НЭ."""
    lines = [f"📋 <b>Заявка НЭ #{row_num}</b>", ""]
    lines.append(f"🏢 <b>Клиент:</b> {_e(data.get('client', '—'))}")
    lines.append(f"🚗 <b>Авто:</b> {_e(data.get('car', '—'))}")
    lines.append(f"🔢 <b>Госномер:</b> {_e(data.get('plate', '—'))}")
    lines.append(f"📅 <b>Дата ДТП:</b> {_e(data.get('date', '—'))}")
    if data.get("status_dtp"):
        lines.append(f"🔖 <b>Статус ДТП:</b> {_e(data.get('status_dtp'))}")
    if data.get("comment"):
        lines.append(f"📝 <b>Комментарий:</b> {_e(data.get('comment'))}")
    return "\n".join(lines)


def send_photos_to_chat(photos_b64: list, caption: str) -> list[str]:
    """Отправляет фото группами по 10 через sendMediaGroup. Возвращает список ошибок."""
    errors = []

    # Декодируем все фото заранее
    photos_bytes = []
    for b64 in photos_b64:
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        try:
            photos_bytes.append(base64.b64decode(b64))
        except Exception as e:
            errors.append(str(e))

    if not photos_bytes:
        return errors

    # 1 фото → sendPhoto; 2+ фото → sendMediaGroup группами по 10
    if len(photos_bytes) == 1:
        try:
            _send_single_photo(photos_bytes[0])
        except Exception as e:
            errors.append(str(e))
    else:
        for i in range(0, len(photos_bytes), 10):
            group = photos_bytes[i:i + 10]
            try:
                _send_media_group(group)
            except Exception as e:
                errors.append(str(e))

    return errors


_CORS_BASE = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Secret-Token",
}

# Для preflight 204 — без Content-Type (нет тела)
CORS_PREFLIGHT = {**_CORS_BASE}

# Для ответов с JSON-телом
CORS_HEADERS = {**_CORS_BASE, "Content-Type": "application/json"}


def handler(event, context):
    """Yandex Cloud Function entry point."""

    # CORS preflight — браузер спрашивает разрешение перед реальным запросом
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 204, "headers": CORS_PREFLIGHT, "body": ""}

    # Проверка секретного токена
    headers = event.get("headers", {}) or {}
    token = headers.get("x-secret-token") or headers.get("X-Secret-Token", "")
    if SECRET_TOKEN and token != SECRET_TOKEN:
        return {
            "statusCode": 403,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "Forbidden"}, ensure_ascii=False),
        }

    # Парсинг тела запроса
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            data = json.loads(body)
        else:
            data = body
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "Invalid JSON"}, ensure_ascii=False),
        }

    if not isinstance(data, dict):
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "Body must be a JSON object"}, ensure_ascii=False),
        }

    # Проверка обязательных полей
    required = ["client", "car", "plate", "date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"error": f"Не заполнены поля: {', '.join(missing)}"},
                ensure_ascii=False,
            ),
        }

    # Запись в таблицу
    try:
        row_num = write_row(data)
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)}, ensure_ascii=False),
        }

    # Уведомление в Telegram
    photo_errors = []
    if BOT_TOKEN and CHAT_ID:
        try:
            send_text_to_chat(build_notification(row_num, data))
        except Exception as e:
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({"ok": True, "row": row_num, "notify_error": str(e)}, ensure_ascii=False),
            }

        photos = data.get("photos", [])
        if photos:
            photo_errors = send_photos_to_chat(photos, "")

        try:
            send_button_to_chat()
        except Exception:
            pass  # кнопка не критична — данные уже записаны

    if photo_errors:
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"ok": True, "row": row_num, "photo_error": photo_errors[0]},
                ensure_ascii=False,
            ),
        }

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({"ok": True, "row": row_num}, ensure_ascii=False),
    }
