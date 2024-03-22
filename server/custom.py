import asyncio

from aiogram import Bot as AioBot, Dispatcher
from aiogram.dispatcher.webhook import WebhookRequestHandler
from aiogram.dispatcher.webhook import SendMessage
from aiogram import exceptions
from aiogram import types
from contextvars import ContextVar
from aiohttp.web_exceptions import HTTPNotFound
from aioredis.commands import create_redis_pool
from aioredis import Redis
from tortoise.expressions import F
import logging
import typing as ty
from olgram.settings import ServerSettings
from olgram.models.models import Bot, GroupChat, BannedUser, BotStartMessage, BotSecondMessage, MailingUser
from locales.locale import _, translators
from server.inlines import inline_handler

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

db_bot_instance: ContextVar[Bot] = ContextVar('db_bot_instance')

_redis: ty.Optional[Redis] = None


def _get_translator(message: types.Message) -> ty.Callable:
    if not message.from_user.locale:
        return _
    return translators.get(message.from_user.locale.language, _)


async def init_redis():
    global _redis
    _redis = await create_redis_pool(ServerSettings.redis_path())


def _message_unique_id(bot_id: int, message_id: int) -> str:
    return f"{bot_id}_{message_id}"


def _tag_uid(bot_id: int, user_id: int) -> str:
    return f"tag_{bot_id}_{user_id}"


def _thread_unique_id(bot_id: int, chat_id: int) -> str:
    return f"thread_{bot_id}_{chat_id}"


def _last_message_uid(bot_id: int, chat_id: int) -> str:
    return f"lm_{bot_id}_{chat_id}"


def _antiflood_marker_uid(bot_id: int, chat_id: int) -> str:
    return f"af_{bot_id}_{chat_id}"


def _on_security_policy(message: types.Message, bot):
    _ = _get_translator(message)
    text = _("<b>Политика конфиденциальности</b>\n\n"
             "Этот бот не хранит ваши сообщения, имя пользователя и @username. При отправке сообщения (кроме команд "
             "/start и /security_policy) ваш идентификатор пользователя записывается в кеш на некоторое время и потом "
             "удаляется из кеша. Этот идентификатор используется для общения с оператором.\n\n")
    if bot.enable_additional_info:
        text += _("При отправке сообщения (кроме команд /start и /security_policy) оператор <b>видит</b> ваши имя "
                  "пользователя, @username и идентификатор пользователя в силу настроек, которые оператор указал при "
                  "создании бота.\n\n")
    else:
        text += _("В зависимости от ваших настроек конфиденциальности Telegram, оператор может видеть ваш username, "
                  "имя пользователя и другую информацию.\n\n")

    if bot.enable_mailing:
        text += _("В этом боте включена массовая рассылка в силу настроек, которые оператор указал при создании бота. "
                  "Ваш идентификатор пользователя может быть записан в базу данных на долгое время")
    else:
        text += _("В этом боте нет массовой рассылки сообщений")

    return SendMessage(chat_id=message.chat.id,
                       text=text,
                       parse_mode="HTML")


async def send_user_message(message: types.Message, super_chat_id: int, bot, tag: str = ""):
    """Переслать сообщение от пользователя, добавлять к нему user info при необходимости"""
    if bot.enable_additional_info:
        user_info = _("Сообщение от пользователя ")
        user_info += message.from_user.full_name
        if message.from_user.username:
            user_info += " | @" + message.from_user.username
        user_info += f" | #ID{message.from_user.id}"
        if message.from_user.locale:
            user_info += f" | lang: {message.from_user.locale}"
        if message.forward_sender_name:
            user_info += f" | fwd: {message.forward_sender_name}"
        tag = await _redis.get(_tag_uid(bot.pk, message.from_user.id), encoding="utf-8")
        if tag:
            user_info += f" | tag: {tag}"

        # Добавлять информацию в конец текста
        if message.content_type == types.ContentType.TEXT \
                and len(message.text) + len(user_info) < 4093:  # noqa:E721
            new_message = await message.bot.send_message(super_chat_id, message.text + "\n\n" + user_info)
        else:  # Не добавлять информацию в конец текста, информация отдельным сообщением
            new_message = await message.bot.send_message(super_chat_id, text=user_info)
            new_message_2 = await message.copy_to(super_chat_id, reply_to_message_id=new_message.message_id)
            await _redis.set(_message_unique_id(bot.pk, new_message_2.message_id), message.chat.id,
                             pexpire=ServerSettings.redis_timeout_ms())
    elif tag:
        # добавлять тег в конец текста
        if message.content_type == types.ContentType.TEXT and len(message.text) + len(tag) < 4093:
            new_message = await message.bot.send_message(super_chat_id, message.text + "\n\n" + tag)
        else:
            new_message = await message.bot.send_message(super_chat_id, text=tag)
            new_message_2 = await message.copy_to(super_chat_id, reply_to_message_id=new_message.message_id)
            await _redis.set(_message_unique_id(bot.pk, new_message_2.message_id), message.chat.id,
                             pexpire=ServerSettings.redis_timeout_ms())
    else:
        try:
            new_message = await message.forward(super_chat_id)
        except exceptions.MessageCantBeForwarded:
            new_message = await message.copy_to(super_chat_id)

    await _redis.set(_message_unique_id(bot.pk, new_message.message_id), message.chat.id,
                     pexpire=ServerSettings.redis_timeout_ms())
    return new_message


async def send_to_superchat(is_super_group: bool, message: types.Message, super_chat_id: int, bot):
    """Пересылка сообщения от пользователя оператору (логика потоков сообщений)"""
    if bot.enable_tags:
        tag = await _redis.get(_tag_uid(bot.pk, message.chat.id), encoding="utf-8")
    else:
        tag = ""
    if tag:
        tag = str(tag)

    if is_super_group and bot.enable_threads:
        if bot.enable_thread_interrupt:
            thread_timeout = ServerSettings.thread_timeout_ms()
        else:
            thread_timeout = ServerSettings.redis_timeout_ms()
        thread_first_message = await _redis.get(_thread_unique_id(bot.pk, message.chat.id))
        if thread_first_message:
            # переслать в супер-чат, отвечая на предыдущее сообщение
            try:
                if tag:
                    if message.content_type == types.ContentType.TEXT and len(message.text) + len(tag) < 4093:
                        new_message = await message.bot.send_message(
                            super_chat_id,
                            message.text + "\n\n" + tag,
                            reply_to_message_id=int(thread_first_message))
                    else:
                        new_message = await message.copy_to(super_chat_id,
                                                            reply_to_message_id=int(thread_first_message))
                        new_message_2 = await message.bot.send_message(
                            super_chat_id, reply_to_message_id=new_message.message_id, text=tag)
                        await _redis.set(_message_unique_id(bot.pk, new_message_2.message_id), message.chat.id,
                                         pexpire=thread_timeout)
                else:
                    new_message = await message.copy_to(super_chat_id, reply_to_message_id=int(thread_first_message))
                await _redis.set(_message_unique_id(bot.pk, new_message.message_id), message.chat.id,
                                 pexpire=thread_timeout)
            except exceptions.BadRequest:
                new_message = await send_user_message(message, super_chat_id, bot, tag)
                await _redis.set(
                    _thread_unique_id(bot.pk, message.chat.id), new_message.message_id, pexpire=thread_timeout)
        else:
            # переслать супер-чат
            new_message = await send_user_message(message, super_chat_id, bot, tag)
            await _redis.set(_thread_unique_id(bot.pk, message.chat.id), new_message.message_id,
                             pexpire=thread_timeout)
    else:  # личные сообщения не поддерживают потоки сообщений: просто отправляем сообщение
        await send_user_message(message, super_chat_id, bot, tag)


async def _increase_count(_bot):
    _bot.incoming_messages_count = F("incoming_messages_count") + 1
    await _bot.save(update_fields=["incoming_messages_count"])


async def handle_user_message(message: types.Message, super_chat_id: int, bot):
    """Обычный пользователь прислал сообщение в бот, нужно переслать его операторам"""
    _ = _get_translator(message)
    is_super_group = super_chat_id < 0

    if bot.enable_mailing:
        asyncio.create_task(MailingUser.get_or_create(telegram_id=message.chat.id, bot=bot))

    # Проверить, не забанен ли пользователь
    banned = await bot.banned_users.filter(telegram_id=message.chat.id)
    if banned:
        return SendMessage(chat_id=message.chat.id,
                           text=_("Вы заблокированы в этом боте"))

    # Проверить анти-флуд
    if bot.enable_antiflood:
        if await _redis.get(_antiflood_marker_uid(bot.pk, message.chat.id)):
            return SendMessage(chat_id=message.chat.id,
                               text=_("Слишком много сообщений, подождите одну минуту"))
        await _redis.setex(_antiflood_marker_uid(bot.pk, message.chat.id), 60, 1)

    # Пересылаем сообщение в супер-чат
    try:
        await send_to_superchat(is_super_group, message, super_chat_id, bot)
    except (exceptions.Unauthorized, exceptions.ChatNotFound):
        return SendMessage(chat_id=message.chat.id, text=_("Не удаётся связаться с владельцем бота"))
    except exceptions.RetryAfter:
        return SendMessage(chat_id=message.chat.id, text=_("Слишком много сообщений, подождите одну минуту"))
    except exceptions.TelegramAPIError as err:
        _logger.error(f"(exception on forwarding) {err}")
        return

    asyncio.create_task(_increase_count(bot))

    # И отправить пользователю специальный текст, если он указан и если давно не отправляли
    if bot.second_text:
        send_auto = not await _redis.get(_last_message_uid(bot.pk, message.chat.id))
        await _redis.setex(_last_message_uid(bot.pk, message.chat.id), 60 * 60 * 3, 1)
        if send_auto or bot.enable_always_second_message:
            text_obj = await BotSecondMessage.get_or_none(bot=bot, locale=str(message.from_user.locale))
            return SendMessage(chat_id=message.chat.id, text=text_obj.text if text_obj else bot.second_text,
                               parse_mode="HTML")


async def handle_operator_message(message: types.Message, super_chat_id: int, bot):
    """Оператор написал что-то, нужно переслать сообщение обратно пользователю, или забанить его и т.д."""
    _ = _get_translator(message)

    if message.reply_to_message:

        if message.reply_to_message.from_user.id != message.bot.id:
            return  # нас интересуют только ответы на сообщения бота

        # В супер-чате кто-то ответил на сообщение пользователя, нужно переслать тому пользователю
        chat_id = await _redis.get(_message_unique_id(bot.pk, message.reply_to_message.message_id))
        if not chat_id:
            chat_id = message.reply_to_message.forward_from_chat
            if not chat_id:
                return SendMessage(chat_id=message.chat.id,
                                   text=_("<i>Невозможно переслать сообщение: автор не найден (сообщение слишком "
                                          "старое?)</i>"),
                                   parse_mode="HTML")
        chat_id = int(chat_id)

        if message.text == "/ban":
            user, create = await BannedUser.get_or_create(telegram_id=chat_id, bot=bot)
            await user.save()
            return SendMessage(chat_id=message.chat.id, text=_("Пользователь заблокирован"))

        if message.text == "/unban":
            banned_user = await bot.banned_users.filter(telegram_id=chat_id).first()
            if not banned_user:
                return SendMessage(chat_id=message.chat.id, text=_("Пользователь не был забанен"))
            else:
                await banned_user.delete()
                return SendMessage(chat_id=message.chat.id, text=_("Пользователь разбанен"))
        if bot.enable_tags:
            if message.text and message.text.startswith("/tag "):
                tag = message.text.replace("/tag ", "")[:20].strip()
                if tag:
                    await _redis.set(_tag_uid(bot.pk, chat_id), tag, pexpire=ServerSettings.redis_timeout_ms())
                    return SendMessage(chat_id=message.chat.id, text=_("Тег выставлен"))
                else:
                    await _redis.delete(_tag_uid(bot.pk, chat_id))
                    return SendMessage(chat_id=message.chat.id, text=_("Тег убран"))

        try:
            await message.copy_to(chat_id)
        except (exceptions.MessageError, exceptions.Unauthorized):
            await message.reply(_("<i>Невозможно переслать сообщение (автор заблокировал бота?)</i>"),
                                parse_mode="HTML")
            return

        bot.outgoing_messages_count = F("outgoing_messages_count") + 1
        await bot.save(update_fields=["outgoing_messages_count"])

    elif super_chat_id > 0:
        # в супер-чате кто-то пишет сообщение сам себе, только для личных сообщений
        if bot.enable_mailing:
            asyncio.create_task(MailingUser.get_or_create(telegram_id=message.chat.id, bot=bot))
        await message.forward(super_chat_id)
        # И отправить пользователю специальный текст, если он указан
        if bot.second_text:
            return SendMessage(chat_id=message.chat.id, text=bot.second_text, parse_mode="HTML")


async def message_handler(message: types.Message, *args, **kwargs):
    _ = _get_translator(message)
    bot = db_bot_instance.get()

    if message.text and message.text == "/start":
        # На команду start нужно ответить, не пересылая сообщение никуда
        text_obj = await BotStartMessage.get_or_none(bot=bot, locale=str(message.from_user.locale))
        text = text_obj.text if text_obj else bot.start_text
        if bot.enable_olgram_text:
            text += _(ServerSettings.append_text())
        return SendMessage(chat_id=message.chat.id, text=text, parse_mode="HTML")

    if message.text and message.text == "/security_policy":
        # На команду security_policy нужно ответить, не пересылая сообщение никуда
        return _on_security_policy(message, bot)

    super_chat_id = await bot.super_chat_id()

    if message.chat.id != super_chat_id:
        # Это обычный чат
        return await handle_user_message(message, super_chat_id, bot)
    else:
        # Это супер-чат
        return await handle_operator_message(message, super_chat_id, bot)


async def edited_message_handler(message: types.Message, *args, **kwargs):
    return await message_handler(message, *args, **kwargs, is_edited=True)


async def receive_invite(message: types.Message):
    bot = db_bot_instance.get()
    for member in message.new_chat_members:
        if member.id == message.bot.id:
            chat, _ = await GroupChat.get_or_create(chat_id=message.chat.id,
                                                    defaults={"name": message.chat.full_name})
            chat.name = message.chat.full_name
            await chat.save()
            if chat not in await bot.group_chats.all():
                await bot.group_chats.add(chat)
                await bot.save()
            break


async def receive_group_create(message: types.Message):
    bot = db_bot_instance.get()

    chat, _ = await GroupChat.get_or_create(chat_id=message.chat.id,
                                            defaults={"name": message.chat.full_name})
    chat.name = message.chat.full_name
    await chat.save()
    if chat not in await bot.group_chats.all():
        await bot.group_chats.add(chat)
        await bot.save()


async def receive_left(message: types.Message):
    bot = db_bot_instance.get()
    if message.left_chat_member.id == message.bot.id:
        chat = await bot.group_chats.filter(chat_id=message.chat.id).first()
        if chat:
            await bot.group_chats.remove(chat)
            bot_group_chat = await bot.group_chat
            if bot_group_chat == chat:
                bot.group_chat = None
            await bot.save()


async def receive_inline(inline_query):
    _logger.info("inline handler")
    bot = db_bot_instance.get()
    return await inline_handler(inline_query, bot)


async def receive_migrate(message: types.Message):
    bot = db_bot_instance.get()
    from_id = message.chat.id
    to_id = message.migrate_to_chat_id

    chats = await bot.group_chats.filter(chat_id=from_id)
    for chat in chats:
        chat.chat_id = to_id
        await chat.save(update_fields=["chat_id"])


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
        dp = Dispatcher(AioBot(bot.decrypted_token()))

        supported_messages = [types.ContentType.TEXT,
                              types.ContentType.CONTACT,
                              types.ContentType.ANIMATION,
                              types.ContentType.AUDIO,
                              types.ContentType.DOCUMENT,
                              types.ContentType.PHOTO,
                              types.ContentType.STICKER,
                              types.ContentType.VIDEO,
                              types.ContentType.VOICE,
                              types.ContentType.LOCATION]
        dp.register_message_handler(message_handler, content_types=supported_messages)
        dp.register_edited_message_handler(edited_message_handler, content_types=supported_messages)

        dp.register_message_handler(receive_invite, content_types=[types.ContentType.NEW_CHAT_MEMBERS])
        dp.register_message_handler(receive_left, content_types=[types.ContentType.LEFT_CHAT_MEMBER])
        dp.register_message_handler(receive_migrate, content_types=[types.ContentType.MIGRATE_TO_CHAT_ID])
        dp.register_message_handler(receive_group_create, content_types=[types.ContentType.GROUP_CHAT_CREATED])
        dp.register_inline_handler(receive_inline)

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
