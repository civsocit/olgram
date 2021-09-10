from aiogram import Bot as AioBot, Dispatcher
from aiogram.dispatcher.webhook import WebhookRequestHandler
from aiogram.dispatcher.webhook import SendMessage
from aiogram import exceptions
from aiogram import types
from contextvars import ContextVar
from aiohttp.web_exceptions import HTTPNotFound
import aioredis
import typing as ty
from olgram.settings import ServerSettings


from olgram.models.models import Bot

db_bot_instance: ContextVar[Bot] = ContextVar('db_bot_instance')

_redis: ty.Optional[aioredis.Redis] = None


async def init_redis():
    global _redis
    _redis = await aioredis.create_redis_pool(ServerSettings.redis_path())


def _message_unique_id(bot_id: int, message_id: int) -> str:
    return f"{bot_id}_{message_id}"


async def message_handler(message, *args, **kwargs):
    bot = db_bot_instance.get()

    if message.text and message.text.startswith("/start"):
        # На команду start нужно ответить, не пересылая сообщение никуда
        return SendMessage(chat_id=message.chat.id,
                           text=bot.start_text)

    super_chat_id = await bot.super_chat_id()

    if message.chat.id != super_chat_id:
        # Это обычный чат: сообщение нужно переслать в супер-чат
        new_message = await message.forward(super_chat_id)
        await _redis.set(_message_unique_id(bot.pk, new_message.message_id), message.chat.id)
    else:
        # Это супер-чат
        if message.reply_to_message:
            # Ответ из супер-чата переслать тому пользователю,
            chat_id = await _redis.get(_message_unique_id(bot.pk, message.reply_to_message.message_id))
            if not chat_id:
                chat_id = message.reply_to_message.forward_from_chat
                if not chat_id:
                    return SendMessage(chat_id=message.chat.id, text="Невозможно переслать сообщение: автор не найден")
            chat_id = int(chat_id)
            try:
                await message.copy_to(chat_id)
            except exceptions.MessageError:
                await message.reply("Невозможно переслать сообщение: возможно, автор заблокировал бота")
                return
        else:
            await message.forward(super_chat_id)


class CustomRequestHandler(WebhookRequestHandler):

    def __init__(self, *args, **kwargs):
        self._dispatcher = None
        super(CustomRequestHandler, self).__init__(*args, **kwargs)

    async def _create_dispatcher(self):
        key = self.request.url.path[1:]

        bot = await Bot.filter(code=key).first()
        if not bot:
            return None
        db_bot_instance.set(bot)
        dp = Dispatcher(AioBot(bot.token))

        dp.register_message_handler(message_handler, content_types=[types.ContentType.TEXT,
                                                                    types.ContentType.CONTACT,
                                                                    types.ContentType.ANIMATION,
                                                                    types.ContentType.AUDIO,
                                                                    types.ContentType.DOCUMENT,
                                                                    types.ContentType.PHOTO,
                                                                    types.ContentType.STICKER,
                                                                    types.ContentType.VIDEO,
                                                                    types.ContentType.VOICE])

        return dp

    async def post(self):
        dispatcher = await self._create_dispatcher()
        if not dispatcher:
            raise HTTPNotFound()

        Dispatcher.set_current(dispatcher)
        AioBot.set_current(dispatcher.bot)
        return await super(CustomRequestHandler, self).post()

    def get_dispatcher(self):
        """
        Get Dispatcher instance from environment

        :return: :class:`aiogram.Dispatcher`
        """
        return Dispatcher.get_current()

