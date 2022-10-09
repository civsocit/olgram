"""
Здесь метрики
"""

from aiogram import types
from aiogram.dispatcher import FSMContext
from olgram.models import models

from olgram.router import dp
from olgram.settings import OlgramSettings
from locales.locale import _


@dp.message_handler(commands=["info"], state="*")
async def info(message: types.Message, state: FSMContext):
    """
    Команда /info
    """

    if message.chat.id != OlgramSettings.supervisor_id():
        await message.answer(_("Недостаточно прав"))
        return

    bots = await models.Bot.all()
    bots_count = len(bots)
    user_count = len(await models.User.all())
    templates_count = len(await models.DefaultAnswer.all())
    promo_count = len(await models.Promo.all())
    olgram_text_disabled = len(await models.Bot.filter(enable_olgram_text=False))

    income_messages = sum([bot.incoming_messages_count for bot in bots])
    outgoing_messages = sum([bot.outgoing_messages_count for bot in bots])

    await message.answer(_("Количество ботов: {0}\n").format(bots_count) +
                         _("Количество пользователей (у конструктора): {0}\n").format(user_count) +
                         _("Шаблонов ответов: {0}\n").format(templates_count) +
                         _("Входящих сообщений у всех ботов: {0}\n").format(income_messages) +
                         _("Исходящих сообщений у всех ботов: {0}\n").format(outgoing_messages) +
                         _("Промо-кодов выдано: {0}\n").format(promo_count) +
                         _("Рекламную плашку выключили: {0}\n").format(olgram_text_disabled))
