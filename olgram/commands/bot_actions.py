"""
Здесь работа с конкретным ботом
"""
from aiogram import types
from aiogram.utils.exceptions import TelegramAPIError, Unauthorized
from aiogram import Bot as AioBot
from olgram.models.models import Bot, BotStartMessage, BotSecondMessage
from server.server import unregister_token
from locales.locale import _


async def delete_bot(bot: Bot, call: types.CallbackQuery):
    """
    Пользователь решил удалить бота
    """
    try:
        await unregister_token(bot.decrypted_token())
    except Unauthorized:
        # Вероятно пользователь сбросил токен или удалил бот, это уже не наши проблемы
        pass
    await bot.delete()
    await call.answer(_("Бот удалён"))
    try:
        await call.message.delete()
    except TelegramAPIError:
        pass


async def reset_bot_text(bot: Bot, call: types.CallbackQuery, state):
    """
    Пользователь решил сбросить текст бота к default
    :param bot:
    :param call:
    :return:
    """
    async with state.proxy() as proxy:
        lang = proxy.get("lang", "none")
    if lang == "none":
        await BotStartMessage.filter(bot=bot).delete()
        bot.start_text = bot._meta.fields_map['start_text'].default
        await bot.save(update_fields=["start_text"])
    else:
        await BotStartMessage.filter(bot=bot, locale=lang).delete()
    await call.answer(_("Текст сброшен"))


async def reset_bot_second_text(bot: Bot, call: types.CallbackQuery, state):
    """
    Пользователь решил сбросить second text бота
    :param bot:
    :param call:
    :return:
    """
    async with state.proxy() as proxy:
        lang = proxy.get("lang", "none")
    if lang == "none":
        await BotSecondMessage.filter(bot=bot).delete()
        bot.second_text = bot._meta.fields_map['second_text'].default
        await bot.save(update_fields=["second_text"])
    else:
        await BotSecondMessage.filter(bot=bot, locale=lang).delete()
    await call.answer(_("Текст сброшен"))


async def select_chat(bot: Bot, call: types.CallbackQuery, chat: str):
    """
    Пользователь выбрал чат, в который хочет получать сообщения от бота
    :param bot:
    :param call:
    :param chat:
    :return:
    """
    if chat == "personal":
        bot.group_chat = None
        await bot.save()
        await call.answer(_("Выбран личный чат"))
        return
    if chat == "leave":
        bot.group_chat = None
        await bot.save()
        chats = await bot.group_chats.all()
        a_bot = AioBot(bot.decrypted_token())
        for chat in chats:
            try:
                await chat.delete()
                await a_bot.leave_chat(chat.chat_id)
            except TelegramAPIError:
                pass
        await call.answer(_("Бот вышел из чатов"))
        await a_bot.session.close()
        return

    chat_obj = await bot.group_chats.filter(id=chat).first()
    if not chat_obj:
        await call.answer(_("Нельзя привязать бота к этому чату"))
        return
    bot.group_chat = chat_obj
    await bot.save()
    await call.answer(_("Выбран чат {0}").format(chat_obj.name))


async def threads(bot: Bot, call: types.CallbackQuery):
    bot.enable_threads = not bot.enable_threads
    await bot.save(update_fields=["enable_threads"])


async def additional_info(bot: Bot, call: types.CallbackQuery):
    bot.enable_additional_info = not bot.enable_additional_info
    await bot.save(update_fields=["enable_additional_info"])


async def always_second_message(bot: Bot, call: types.CallbackQuery):
    bot.enable_always_second_message = not bot.enable_always_second_message
    await bot.save(update_fields=["enable_always_second_message"])


async def thread_interrupt(bot: Bot, call: types.CallbackQuery):
    bot.enable_thread_interrupt = not bot.enable_thread_interrupt
    await bot.save(update_fields=["enable_thread_interrupt"])


async def olgram_text(bot: Bot, call: types.CallbackQuery):
    if await bot.is_promo():
        bot.enable_olgram_text = not bot.enable_olgram_text
        await bot.save(update_fields=["enable_olgram_text"])


async def antiflood(bot: Bot, call: types.CallbackQuery):
    bot.enable_antiflood = not bot.enable_antiflood
    await bot.save(update_fields=["enable_antiflood"])


async def mailing(bot: Bot, call: types.CallbackQuery):
    bot.enable_mailing = not bot.enable_mailing
    await bot.save(update_fields=["enable_mailing"])
