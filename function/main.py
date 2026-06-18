import base64
import hashlib
import hmac
import html
import json
import os
import time
import urllib.request
import uuid
from urllib.parse import parse_qsl

from sheets import write_row

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Пауза между пачками фото чтобы не получить 429 от Telegram
_INTER_BATCH_DELAY = 1.5


def _verify_init_data(init_data: str, bot_token: str, max_age: int = 3600) -> bool:
    try:
        params = dict(parse_qsl(init_data, strict_parsing=True))
    except Exception:
        return False
    received_hash = params.pop("hash", None)
    if not received_hash:
        return False
    try:
        auth_date = int(params.get("auth_date", 0))
    except (ValueError, TypeError):
        return False
    diff = time.time() - auth_date
    if diff > max_age or diff < 0:
        return False
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, received_hash)


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
    with urllib.request.urlopen(req, timeout=60):
        pass


def _send_media_group(photos_bytes: list) -> None:
    """Отправляет группу 2–10 фото через sendMediaGroup."""
    boundary = uuid.uuid4().hex
    media = [{"type": "photo", "media": f"attach://file_{i}"} for i in range(len(photos_bytes))]

    parts = [(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{CHAT_ID}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"\r\n\r\n'
        f"{json.dumps(media, ensure_ascii=False)}\r\n"
    ).encode()]
    for i, img_bytes in enumerate(photos_bytes):
        parts.append((
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file_{i}"; filename="photo.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode())
        parts.append(img_bytes)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{TG_API}/sendMediaGroup",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=90):
        pass


def send_text_to_chat(text: str) -> None:
    """Отправляет текстовое сообщение (используется только когда нет фото)."""
    payload = json.dumps(
        {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        ensure_ascii=False,
    ).encode()
    req = urllib.request.Request(
        f"{TG_API}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30):
        pass


WEBAPP_URL = "https://t.me/AvExp24_bot/newapp"


def send_button_to_chat() -> None:
    """Отправляет только кнопку 'Новая заявка на НЭ' без лишнего текста."""
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": "📋 Новая заявка на НЭ",
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
    with urllib.request.urlopen(req, timeout=30):
        pass


def _e(value: str) -> str:
    return html.escape(str(value))


def build_notification(row_num: int, data: dict) -> str:
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


def send_photos_to_chat(photos_b64: list) -> list:
    """Отправляет фото группами по 10."""
    errors = []
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

    if len(photos_bytes) == 1:
        try:
            _send_single_photo(photos_bytes[0])
        except Exception as e:
            errors.append(str(e))
    else:
        for idx, i in enumerate(range(0, len(photos_bytes), 10)):
            if idx > 0:
                time.sleep(_INTER_BATCH_DELAY)
            group = photos_bytes[i:i + 10]
            try:
                if len(group) == 1:
                    _send_single_photo(group[0])
                else:
                    _send_media_group(group)
            except Exception as e:
                errors.append(str(e))

    return errors


_CORS_BASE = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}
CORS_PREFLIGHT = _CORS_BASE
CORS_HEADERS = {**_CORS_BASE, "Content-Type": "application/json"}


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 204, "headers": {**CORS_PREFLIGHT}, "body": ""}

    # Парсинг тела
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            if len(body) > 3 * 1024 * 1024:
                return {
                    "statusCode": 413,
                    "headers": {**CORS_HEADERS},
                    "body": json.dumps({"error": "Payload too large"}, ensure_ascii=False),
                }
            data = json.loads(body)
        else:
            data = body
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {**CORS_HEADERS},
            "body": json.dumps({"error": "Invalid JSON"}, ensure_ascii=False),
        }

    if not isinstance(data, dict):
        return {
            "statusCode": 400,
            "headers": {**CORS_HEADERS},
            "body": json.dumps({"error": "Body must be a JSON object"}, ensure_ascii=False),
        }

    # Авторизация
    headers = event.get("headers", {}) or {}
    init_data = data.pop("init_data", "")
    if init_data:
        if not BOT_TOKEN or not _verify_init_data(init_data, BOT_TOKEN):
            return {
                "statusCode": 403,
                "headers": {**CORS_HEADERS},
                "body": json.dumps({"error": "Forbidden"}, ensure_ascii=False),
            }
    elif SECRET_TOKEN:
        token = headers.get("x-secret-token") or headers.get("X-Secret-Token", "")
        if token != SECRET_TOKEN:
            return {
                "statusCode": 403,
                "headers": {**CORS_HEADERS},
                "body": json.dumps({"error": "Forbidden"}, ensure_ascii=False),
            }
    else:
        return {
            "statusCode": 403,
            "headers": {**CORS_HEADERS},
            "body": json.dumps({"error": "Forbidden"}, ensure_ascii=False),
        }

    # Проверка обязательных полей
    required = ["client", "car", "plate", "date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return {
            "statusCode": 400,
            "headers": {**CORS_HEADERS},
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
            "headers": {**CORS_HEADERS},
            "body": json.dumps({"error": str(e)}, ensure_ascii=False),
        }

    # Уведомления в Telegram: текст → фото → кнопка
    photo_errors = []
    if BOT_TOKEN and CHAT_ID:
        notification_text = build_notification(row_num, data)

        # 1. Текст — первым отдельным сообщением
        try:
            send_text_to_chat(notification_text)
        except Exception:
            pass

        # 2. Фото
        photos = data.get("photos", [])
        if not isinstance(photos, list):
            photos = []
        if len(photos) > 50:
            photos = photos[:50]
        if photos:
            photo_errors = send_photos_to_chat(photos)

        # 3. Кнопка "Новая заявка на НЭ" — последней
        try:
            send_button_to_chat()
        except Exception:
            pass

    result = {"ok": True, "row": row_num}
    if photo_errors:
        result["photo_error"] = photo_errors[0]
    return {
        "statusCode": 200,
        "headers": {**CORS_HEADERS},
        "body": json.dumps(result, ensure_ascii=False),
    }
