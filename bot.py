import logging
import os
from dotenv import load_dotenv
from telegram import (
    Update,
    KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv("/Users/mac/Desktop/WORK/Автоэкспертизы_БОТ/.env")

BOT_TOKEN  = os.getenv("BOT_TOKEN")
CHAT_ID    = int(os.getenv("CHAT_ID", "0"))
BOT_USERNAME = "AvExp24_bot"
WEBAPP_URL = "https://saimonurtaev.github.io/avexp-bot-webapp/webapp/"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)


def webapp_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с WebApp кнопкой для личного чата."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📋 Новая заявка НЭ", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
        is_persistent=True,
    )


def group_keyboard() -> InlineKeyboardMarkup:
    """Inline-кнопка для закреплённого сообщения в группе.
    Ведёт в личный чат с ботом — там Telegram открывает WebApp нативно.
    """
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "📋 Новая заявка НЭ",
            url=f"https://t.me/{BOT_USERNAME}?start=ne",
        )
    ]])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """В личном чате — сразу показываем WebApp кнопку внизу экрана."""
    if not update.message:
        return

    # Работает только в личных чатах (именно там web_app кнопка активна)
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "Нажмите кнопку внизу чтобы открыть форму заявки:",
            reply_markup=webapp_keyboard(),
        )
    else:
        await update.message.reply_text(
            "Для создания заявки напишите мне в личные сообщения: "
            f"@{BOT_USERNAME}"
        )


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет и закрепляет сообщение с кнопкой в группе."""
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


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pin",   cmd_pin))

    logging.info("Бот запущен.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
