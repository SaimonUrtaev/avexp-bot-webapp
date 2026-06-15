import json
import os
import base64
import urllib.request
import urllib.parse

from sheets import write_row

SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "")
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
CHAT_ID      = os.environ.get("CHAT_ID", "")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def tg_post(method, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{TG_API}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def send_photos_to_chat(photos_b64: list, caption: str):
    """Отправляет фото в Telegram группу пачками по 10."""
    BATCH = 10
    for i in range(0, len(photos_b64), BATCH):
        batch = photos_b64[i:i + BATCH]
        media = []
        for j, b64 in enumerate(batch):
            # Убираем data:image/jpeg;base64, если есть
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            media.append({
                "type": "photo",
                "media": f"data:image/jpeg;base64,{b64}",
                "caption": caption if j == 0 and i == 0 else "",
            })
        # sendMediaGroup не принимает base64 напрямую — шлём по одному через sendPhoto
        for j, b64 in enumerate(batch):
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            img_bytes = base64.b64decode(b64)
            # Multipart через urllib
            boundary = "----FormBoundary"
            cap = caption if (i == 0 and j == 0) else ""
            parts = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
                f"{CHAT_ID}\r\n"
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="caption"\r\n\r\n'
                f"{cap}\r\n"
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="photo"; filename="photo.jpg"\r\n'
                f"Content-Type: image/jpeg\r\n\r\n"
            ).encode() + img_bytes + f"\r\n--{boundary}--\r\n".encode()

            req = urllib.request.Request(
                f"{TG_API}/sendPhoto",
                data=parts,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
            urllib.request.urlopen(req, timeout=15)


def handler(event, context):
    """Yandex Cloud Function entry point."""

    # Проверка секретного токена
    headers = event.get("headers", {}) or {}
    token = headers.get("X-Secret-Token", "")
    if SECRET_TOKEN and token != SECRET_TOKEN:
        return {
            "statusCode": 403,
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
            "body": json.dumps({"error": "Invalid JSON"}, ensure_ascii=False),
        }

    # Проверка обязательных полей
    required = ["client", "car", "plate", "date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return {
            "statusCode": 400,
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
            "body": json.dumps({"error": str(e)}, ensure_ascii=False),
        }

    # Отправка фото в Telegram (если есть)
    photos = data.get("photos", [])
    if photos and BOT_TOKEN and CHAT_ID:
        caption = (
            f"📋 Заявка НЭ #{row_num}\n"
            f"👤 {data.get('client')} / {data.get('fio')}\n"
            f"🚗 {data.get('car')} {data.get('plate')}\n"
            f"📅 {data.get('date')}"
        )
        try:
            send_photos_to_chat(photos, caption)
        except Exception as e:
            # Фото не дошли — но заявка уже записана, не фатально
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"ok": True, "row": row_num, "photo_error": str(e)},
                    ensure_ascii=False,
                ),
            }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"ok": True, "row": row_num}, ensure_ascii=False),
    }
