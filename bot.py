import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv("/Users/mac/Desktop/WORK/Автоэкспертизы_БОТ/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID   = int(os.getenv("CHAT_ID", "0"))

# Зарегистрированный WebApp — открывается нативно внутри Telegram
WEBAPP_LINK = "https://t.me/AvExp24_bot/newapp"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)


def group_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Новая заявка НЭ", url=WEBAPP_LINK)
    ]])


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет и закрепляет кнопку в группе."""
    if update.effective_chat.id != CHAT_ID:
        return

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
    app.add_handler(CommandHandler("pin",   cmd_pin))
    logging.info("Бот запущен.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
