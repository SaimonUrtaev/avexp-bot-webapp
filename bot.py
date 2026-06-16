import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config import BOT_TOKEN, CHAT_ID, WEBAPP_URL

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

BUTTON_TEXT = "📋 Новая заявка на НЭ"


def persistent_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BUTTON_TEXT)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def webapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📋 Открыть форму заявки", url=WEBAPP_URL)]]
    )


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Устанавливает постоянную кнопку-панель внизу экрана."""
    if update.effective_chat.id != CHAT_ID:
        return

    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="Нажмите кнопку ниже для создания заявки на независимую экспертизу:",
        reply_markup=persistent_keyboard(),
    )

    if update.message:
        await update.message.delete()


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь нажал кнопку внизу — отвечаем inline-кнопкой с WebApp."""
    if not update.message or update.effective_chat.id != CHAT_ID:
        return
    if update.message.text != BUTTON_TEXT:
        return

    await update.message.reply_text(
        "Откройте форму:",
        reply_markup=webapp_keyboard(),
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "Бот Автоэкспертизы НЭ.\n/pin — установить кнопку заявки в группе."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pin", cmd_pin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Chat(CHAT_ID), handle_button))
    logging.info("Бот запущен.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
