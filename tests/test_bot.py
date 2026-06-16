import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import bot


def test_cmd_pin_sends_message():
    sent = []

    class FakeBot:
        async def send_message(self, chat_id, text, reply_markup=None):
            sent.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
            return SimpleNamespace(message_id=123)

        async def pin_chat_message(self, chat_id, message_id, disable_notification=False):
            sent.append({"pinned": True, "chat_id": chat_id, "message_id": message_id})

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=bot.CHAT_ID),
        message=None,
    )
    context = SimpleNamespace(bot=FakeBot())

    asyncio.run(bot.cmd_pin(update, context))

    assert len(sent) == 2
    assert sent[0]["chat_id"] == bot.CHAT_ID
    assert "Нажмите кнопку" in sent[0]["text"]
    assert sent[1]["pinned"] is True
    assert sent[1]["chat_id"] == bot.CHAT_ID
    assert sent[1]["message_id"] == 123


def test_cmd_start_replies_text():
    reply_text = AsyncMock()
    message = SimpleNamespace(reply_text=reply_text)
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=123), message=message)
    context = SimpleNamespace(bot=None)

    asyncio.run(bot.cmd_start(update, context))

    reply_text.assert_awaited_once()
    called_text = reply_text.call_args.args[0]
    assert "Бот Автоэкспертизы" in called_text
