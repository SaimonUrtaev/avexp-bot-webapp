import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv("/Users/mac/Desktop/WORK/Автоэкспертизы_БОТ/.env")

BOT_TOKEN  = os.getenv("BOT_TOKEN")
CHAT_ID    = int(os.getenv("CHAT_ID"))
WEBAPP_URL = "https://saimonurtaev.github.io/avexp-bot-webapp/webapp/"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет и закрепляет сообщение с кнопкой WebApp."""
    if update.effective_chat.id != CHAT_ID:
        return

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Новая заявка НЭ", url=WEBAPP_URL)
    ]])

    msg = await context.bot.send_message(
        chat_id=CHAT_ID,
        text="Нажмите кнопку чтобы создать новую заявку на независимую экспертизу:",
        reply_markup=keyboard,
    )

    await context.bot.pin_chat_message(
        chat_id=CHAT_ID,
        message_id=msg.message_id,
        disable_notification=True,
    )

    if update.message:
        await update.message.delete()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот Автоэкспертизы НЭ активен.\n"
        "Команда /pin в группе — закрепить кнопку заявки."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pin", cmd_pin))

    logging.info("Бот запущен. Используй /pin в группе.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
