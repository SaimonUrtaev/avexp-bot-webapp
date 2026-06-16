# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Запуск бота (polling-режим)
python3 bot.py

# Запуск тестов (все)
venv/bin/python -m pytest tests/ -v

# Запуск одного теста
venv/bin/python -m pytest tests/test_handler.py::test_valid_request_returns_200 -v

# Деплой Cloud Function в Yandex Cloud
./deploy.sh
```

Зависимости устанавливаются в `venv/`: `pip install -r requirements.txt`.

## Архитектура

Проект состоит из двух независимых частей:

### 1. Telegram Bot (`bot.py`)
Запускается локально (polling). Принимает команды `/start` и `/pin`. Команда `/pin` отправляет в группу сообщение с кнопкой-ссылкой на WebApp и закрепляет его. Работает только в чате с `CHAT_ID` из `.env`.

### 2. Cloud Function (два варианта)

**`cloud_function/index.py`** — активная версия, деплоится через `deploy.sh`:
- Принимает POST от WebApp (форма заявки на независимую экспертизу НЭ)
- Записывает строку в Google Sheets (`function/sheets.py` → 10 колонок)
- Отправляет фото в Telegram через `sendPhoto` (multipart, без внешних зависимостей)
- Проверяет `x-secret-token` в заголовке

**`function/main.py`** — более полная версия (убытки ОСАГО, 27 колонок):
- Использует `gspread` + `requests`
- Поля: `park`, `brand`, `grz`, `policy`, `date_dtp`, `insurance`, `admin_note`
- Fallback: если `send_photos` упал → `notify_user` текстом
- `CREDENTIALS_PATH = "/function/code/credentials.json"` (путь внутри Yandex Cloud)

### 3. WebApp (`webapp/index.html`)
Статичная страница на GitHub Pages. Открывается кнопкой из Telegram. Форма с полями: клиент, ФИО, авто, госномер, дата, фото. Отправляет POST на URL Cloud Function.

### 4. Общие утилиты (`utils.py`)
Используется и ботом и Cloud Function:
- `build_text(number, data)` — текст уведомления в Telegram
- `get_headers_list()` — 27 колонок таблицы убытков

## Переменные окружения (`.env`)

| Переменная | Где используется |
|---|---|
| `BOT_TOKEN` | bot.py, Cloud Function |
| `CHAT_ID` | bot.py, Cloud Function |
| `SPREADSHEET_ID` | google_sheets.py, Cloud Function |
| `SHEET_NAME` | google_sheets.py, Cloud Function |
| `GOOGLE_CREDENTIALS_FILE` | config.py → google_sheets.py |
| `YC_FUNCTION_ID` | deploy.sh |
| `SECRET_TOKEN` | function/main.py |

## Тесты

Тесты в `tests/test_handler.py` покрывают `function/main.py`. Мокают `sheets.write_row` через `sys.modules` до импорта `main`. Реальных обращений к Google Sheets и Telegram нет.

`test_bot.py` и `test_sheets.py` в корне — старые файлы, не входят в основной тест-сьют.

## Деплой

`deploy.sh` паркует в zip: `cloud_function/index.py`, `requirements.txt`, `credentials.json`, `utils.py` — и создаёт новую версию функции через `yc serverless function version create`. После деплоя перезапускает локальный `bot.py` через `pkill` + `nohup`.
