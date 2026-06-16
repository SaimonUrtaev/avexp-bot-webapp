import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN, CHAT_ID, WEBAPP_URL

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)


def group_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📋 Новая заявка на НЭ", url=WEBAPP_URL)]]
    )


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет и закрепляет кнопку в группе."""
    if update.effective_chat.id != CHAT_ID:
        return

    # Убираем ReplyKeyboard если осталась от предыдущей версии
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="‌",  # невидимый символ
        reply_markup=ReplyKeyboardRemove(),
    )

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
    logging.info("Бот запущен.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
