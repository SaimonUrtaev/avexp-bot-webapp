import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN, CHAT_ID, WEBAPP_URL
from google_sheets import get_row_count

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

LAST_ROW_FILE = Path(__file__).parent / ".last_row"


def group_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📋 Новая заявка на НЭ", url=WEBAPP_URL)]]
    )


def _load_last_row() -> int:
    try:
        return int(LAST_ROW_FILE.read_text().strip())
    except Exception:
        return 0


def _save_last_row(n: int) -> None:
    LAST_ROW_FILE.write_text(str(n))


async def check_new_rows(context) -> None:
    """Проверяет новые строки в таблице и отправляет кнопку в чат."""
    try:
        current = get_row_count()
        last = _load_last_row()

        if last == 0:
            # Первый запуск — сохраняем текущее состояние, кнопку не шлём
            _save_last_row(current)
            logging.info(f"Sheets init: текущая строка {current}")
            return

        if current > last:
            new_count = current - last
            logging.info(f"Новых строк: {new_count}, отправляю кнопку в чат")
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text="📋 Новая заявка на НЭ",
                reply_markup=group_keyboard(),
            )
            _save_last_row(current)

    except Exception as e:
        logging.error(f"check_new_rows error: {type(e).__name__}: {e}")


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет и закрепляет кнопку в группе."""
    if update.effective_chat.id != CHAT_ID:
        return

    rm = await context.bot.send_message(
        chat_id=CHAT_ID,
        text=".",
        reply_markup=ReplyKeyboardRemove(),
    )
    await context.bot.delete_message(chat_id=CHAT_ID, message_id=rm.message_id)

    msg = await context.bot.send_message(
        chat_id=CHAT_ID,
        text="Нажмите кнопку для создания новой заявки на независимую экспертизу:",
        reply_markup=group_keyboard(),
    )

    await context.bot.pin_chat_message(
        chat_id=CHAT_ID,
        message_id=msg.message_id,
        disable_notification=True,
    )

    if update.message:
        await update.message.delete()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "Бот Автоэкспертизы НЭ.\n/pin — закрепить кнопку заявки в группе."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pin", cmd_pin))

    # Опрос таблицы каждые 15 секунд — кнопка отправляется локально, надёжно
    app.job_queue.run_repeating(check_new_rows, interval=15, first=5)

    logging.info("Бот запущен.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
