# Автоэкспертизы Бот

Простой проект для приёма заявок на независимую экспертизу через Telegram WebApp и запись в Google Sheets.

## Структура проекта

- `bot.py` — Telegram бот
- `cloud_function/index.py` — облачная функция для Yandex Cloud
- `function/main.py` — локальная/альтернативная версия функции
- `webapp/index.html` — статичная форма заявки
- `utils.py` — общие утилиты
- `tests/` — тесты

## Быстрый старт

1. Клонировать репозиторий
2. Создать виртуальное окружение:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Скопировать файл `.env.example` или создать свой `.env`
5. Заполнить переменные:
   - `BOT_TOKEN`
   - `CHAT_ID`
   - `SPREADSHEET_ID`
   - `SHEET_NAME`
   - `SECRET_TOKEN`
   - `WEBAPP_URL` (опционально)
6. Запустить бота:
   ```bash
   python3 bot.py
   ```

## Локальные примеры

- `.env.example` — шаблон переменных окружения
- `webapp/secret.example.js` — пример локального файла со скрытым токеном для WebApp

## Разработка

У проекта есть дополнительные инструменты для разработки.

Установите пакеты для разработки:
```bash
pip install -r requirements-dev.txt
```

Запустить тесты:
```bash
pytest tests/ -v
```

Пример использования `black` и `ruff`:
```bash
black .
ruff check .
```

## WebApp и секретный токен

Файл `webapp/index.html` больше не содержит открытый `SECRET` токен. Для локальной разработки создайте файл `webapp/secret.js` с содержимым:

```js
window.SECRET_TOKEN = "ваш_секретный_токен";
```

Файл `webapp/secret.js` не должен попадать в репозиторий.

Ниже пример шаблона:
```bash
cp webapp/secret.example.js webapp/secret.js
```

## Советы по улучшению

- Держите `credentials.json` вне репозитория
- Добавляйте тесты для новых функций
- Используйте `black` и `ruff`, чтобы поддерживать код чистым
