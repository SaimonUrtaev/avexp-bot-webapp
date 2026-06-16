import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import bot


def test_cmd_pin_sends_and_pins():
    sent = []

    class FakeBot:
        _id = 100

        async def send_message(self, chat_id, text, reply_markup=None):
            FakeBot._id += 1
            sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
            return SimpleNamespace(message_id=FakeBot._id)

        async def delete_message(self, chat_id, message_id):
            sent.append({"deleted": True, "message_id": message_id})

        async def pin_chat_message(self, chat_id, message_id, disable_notification=False):
            sent.append({"pinned": True, "chat_id": chat_id, "message_id": message_id})

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=bot.CHAT_ID),
        message=None,
    )
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(bot.cmd_pin(update, context))

    assert len(sent) == 4
    # 1: отправка "." с ReplyKeyboardRemove
    assert sent[0]["text"] == "."
    # 2: удаление того сообщения
    assert sent[1]["deleted"] is True
    # 3: кнопка заявки
    assert "Нажмите кнопку" in sent[2]["text"]
    assert sent[2]["reply_markup"] is not None
    # 4: закрепление
    assert sent[3]["pinned"] is True


def test_cmd_start_replies_text():
    reply_text = AsyncMock()
    message = SimpleNamespace(reply_text=reply_text)
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123), message=message)
    context = SimpleNamespace(bot=None)

    asyncio.run(bot.cmd_start(update, context))

    reply_text.assert_awaited_once()
    called_text = reply_text.call_args.args[0]
    assert "Бот Автоэкспертизы" in called_text
