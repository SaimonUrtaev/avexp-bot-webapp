#!/bin/bash
set -e

set -a
source "$(dirname "$0")/.env"
set +a

YC=/Users/mac/yandex-cloud/bin/yc

echo "📦 Собираю zip из function/..."
zip -j function.zip \
  function/main.py \
  function/sheets.py \
  function/requirements.txt \
  function/credentials.json

echo "☁️  Деплою функцию avexp-save..."
$YC serverless function version create \
  --function-id "$YC_FUNCTION_ID" \
  --runtime python312 \
  --entrypoint main.handler \
  --memory 256m \
  --execution-timeout 30s \
  --source-path function.zip \
  --environment BOT_TOKEN="$BOT_TOKEN",CHAT_ID="$CHAT_ID",SECRET_TOKEN="$SECRET_TOKEN",SPREADSHEET_ID="$SPREADSHEET_ID",SHEET_NAME="$SHEET_NAME"

echo "🤖 Перезапускаю бота..."
pkill -TERM -f "bot.py" 2>/dev/null || true
sleep 2
nohup venv/bin/python bot.py >> /tmp/avtobot.log 2>&1 &
sleep 2
tail -3 /tmp/avtobot.log

echo "✅ Готово!"
