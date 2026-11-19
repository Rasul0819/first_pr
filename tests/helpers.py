"""Test harness: drives a real Dispatcher with a fake Bot session (no network)."""
from __future__ import annotations

from datetime import datetime
from itertools import count

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import (AnswerCallbackQuery, EditMessageReplyMarkup, EditMessageText,
                             SendDocument, SendMessage, TelegramMethod)
from aiogram.types import CallbackQuery, Chat, Message, Update, User


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod] = []
        self._ids = count(1000)

    async def close(self) -> None: ...

    async def stream_content(self, *a, **kw):  # pragma: no cover
        raise NotImplementedError

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, (SendMessage, SendDocument)):
            return Message(message_id=next(self._ids), date=datetime.now(),
                           chat=Chat(id=method.chat_id, type="private"),
                           text=getattr(method, "text", None))
        if isinstance(method, (EditMessageText, EditMessageReplyMarkup, AnswerCallbackQuery)):
            return True
        return True


class Harness:
    def __init__(self, dp: Dispatcher, user_id: int = 1, username: str = "alice") -> None:
        self.session = FakeSession()
        self.bot = Bot("42:TEST", session=self.session)
        self.dp = dp
        self.user = User(id=user_id, is_bot=False, first_name="Alice", username=username)
        self.chat = Chat(id=user_id, type="private")
        self._uid = count(1)

    def _msg(self, text: str | None, from_bot: bool = False) -> Message:
        return Message(message_id=next(self._uid) + 5000, date=datetime.now(), chat=self.chat,
                       from_user=User(id=42, is_bot=True, first_name="Bot") if from_bot else self.user,
                       text=text)

    async def send(self, text: str) -> None:
        await self.dp.feed_update(self.bot, Update(update_id=next(self._uid), message=self._msg(text)))

    async def click(self, data: str) -> None:
        cb = CallbackQuery(id=str(next(self._uid)), from_user=self.user, chat_instance="x",
                           data=data, message=self._msg("prev", from_bot=True))
        await self.dp.feed_update(self.bot, Update(update_id=next(self._uid), callback_query=cb))

    # ---- inspection
    def replies(self) -> list[str]:
        return [c.text for c in self.session.calls if isinstance(c, (SendMessage, EditMessageText))]

    def last(self) -> str:
        return self.replies()[-1]

    def documents(self) -> list[SendDocument]:
        return [c for c in self.session.calls if isinstance(c, SendDocument)]

    def clear(self) -> None:
        self.session.calls.clear()


def make_harness(db, user_id: int = 1) -> "Harness":
    """Fresh Dispatcher per test (a Router can only attach to one Dispatcher)."""
    import importlib

    import handlers.user
    from config import Settings
    from main import build_dispatcher

    importlib.reload(handlers.user)
    return Harness(build_dispatcher(db, Settings(bot_token="x")), user_id=user_id)
