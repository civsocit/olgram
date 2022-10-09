from olgram.router import dp

from aiogram import types, Bot as AioBot
from olgram.models.models import Bot, User, DefaultAnswer
from aiogram.dispatcher import FSMContext
from aiogram.utils.callback_data import CallbackData
from textwrap import dedent
from olgram.utils.mix import edit_or_create, button_text_limit, wrap
from olgram.commands import bot_actions
from locales.locale import _

import typing as ty


menu_callback = CallbackData('menu', 'level', 'bot_id', 'operation', 'chat')

empty = "0"


async def send_bots_menu(chat_id: int, user_id: int, call=None):
    """
    Отправить пользователю список ботов
    :return:
    """
    if call:
        await call.answer()

    user = await User.get_or_none(telegram_id=user_id)
    bots = await Bot.filter(owner=user)
    if not bots:
        await AioBot.get_current().send_message(chat_id, dedent(_("""
        У вас нет добавленных ботов.

        Отправьте команду /addbot, чтобы добавить бот.
        """)))
        return

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for bot in bots:
        keyboard.insert(
            types.InlineKeyboardButton(text="@" + bot.name,
                                       callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty,
                                                                       chat=empty))
        )

    text = _("Ваши боты")
    if call:
        await edit_or_create(call, text, keyboard)
    else:
        await AioBot.get_current().send_message(chat_id, text, reply_markup=keyboard)


async def send_chats_menu(bot: Bot, call: types.CallbackQuery):
    await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    chats = await bot.group_chats.all()

    for chat in chats:
        keyboard.insert(
            types.InlineKeyboardButton(text=button_text_limit(chat.name),
                                       callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="chat",
                                                                       chat=chat.id))
        )
    if chats:
        keyboard.insert(
            types.InlineKeyboardButton(text=_("Личные сообщения"),
                                       callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="chat",
                                                                       chat="personal"))
        )
        keyboard.insert(
            types.InlineKeyboardButton(text=_("❗️ Выйти из всех чатов"),
                                       callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="chat",
                                                                       chat="leave"))
        )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Назад"),
                                   callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty,
                                                                   chat=empty))
    )

    if not chats:
        text = dedent(_("""
        Этот бот не добавлен в чаты, поэтому все сообщения будут приходить вам в бот.
        Чтобы подключить чат — добавьте бот @{0} в чат, откройте это меню ещё раз и выберите добавленный чат.
        Если ваш бот состоял в групповом чате до того, как его добавили в Olgram - удалите бота из чата и добавьте
        снова.
        """)).format(bot.name)
    else:
        text = dedent(_("""
        В этом разделе вы можете привязать бота @{0} к чату.
        Выберите чат, куда бот будет пересылать сообщения.
        """)).format(bot.name)

    await edit_or_create(call, text, keyboard)


async def send_bot_menu(bot: Bot, call: types.CallbackQuery):
    await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Текст"),
                                   callback_data=menu_callback.new(level=2, bot_id=bot.id, operation="text",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Чат"),
                                   callback_data=menu_callback.new(level=2, bot_id=bot.id, operation="chat",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Удалить бот"),
                                   callback_data=menu_callback.new(level=2, bot_id=bot.id, operation="delete",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Статистика"),
                                   callback_data=menu_callback.new(level=2, bot_id=bot.id, operation="stat",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Рассылка"),
                                   callback_data=menu_callback.new(level=2, bot_id=bot.id, operation="broadcast",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Опции"),
                                   callback_data=menu_callback.new(level=2, bot_id=bot.id, operation="settings",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Назад"),
                                   callback_data=menu_callback.new(level=0, bot_id=empty, operation=empty, chat=empty))
    )

    await edit_or_create(call, dedent(_("""
    Управление ботом @{0}.

    Если у вас возникли вопросы по настройке бота, то посмотрите нашу справку /help или напишите нам
    @civsocit_feedback_bot
    """)).format(bot.name), reply_markup=keyboard)


async def send_bot_delete_menu(bot: Bot, call: types.CallbackQuery):
    await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Да, удалить бот"),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="delete_yes",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Назад"),
                                   callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty, chat=empty))
    )

    await edit_or_create(call, dedent(_("""
    Вы уверены, что хотите удалить бота @{0}?
    """)).format(bot.name), reply_markup=keyboard)


async def send_bot_settings_menu(bot: Bot, call: types.CallbackQuery):
    await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Потоки сообщений"),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="threads",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Данные пользователя"),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="additional_info",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Антифлуд"),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="antiflood",
                                                                   chat=empty))
    )
    is_promo = await bot.is_promo()
    if is_promo:
        keyboard.insert(
            types.InlineKeyboardButton(text=_("Olgram подпись"),
                                       callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="olgram_text",
                                                                       chat=empty))
        )

    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Назад"),
                                   callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty,
                                                                   chat=empty))
    )

    thread_turn = _("включены") if bot.enable_threads else _("выключены")
    info_turn = _("включены") if bot.enable_additional_info else _("выключены")
    antiflood_turn = _("включен") if bot.enable_antiflood else _("выключен")
    text = dedent(_("""
    <a href="https://olgram.readthedocs.io/ru/latest/options.html#threads">Потоки сообщений</a>: <b>{0}</b>
    <a href="https://olgram.readthedocs.io/ru/latest/options.html#user-info">Данные пользователя</a>: <b>{1}</b>
    <a href="https://olgram.readthedocs.io/ru/latest/options.html#antiflood">Антифлуд</a>: <b>{2}</b>
    """)).format(thread_turn, info_turn, antiflood_turn)

    if is_promo:
        olgram_turn = _("включена") if bot.enable_olgram_text else _("выключена")
        text += _("Olgram подпись: <b>{0}</b>").format(olgram_turn)

    await edit_or_create(call, text, reply_markup=keyboard, parse_mode="HTML")


async def send_bot_broadcast_menu(bot: Bot, call: ty.Optional[types.CallbackQuery] = None,
                                  chat_id: ty.Optional[int] = None, text: ty.Optional[str] = None):
    if call:
        await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Назад"),
                                   callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty, chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Начать рассылку"),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="start_broadcast",
                                                                   chat=empty))
    )

    if text:
        text = dedent(_("""
        Сейчас вы редактируете текст, который будет отправлен всем пользователям бота @{0} после начала рассылки.

        Текущий текст:
        <pre>
        {1}
        </pre>
        Отправьте сообщение, чтобы изменить текст.
        """)).format(bot.name, text)
    else:
        text = _(
            "Отправьте сообщение с текстом, который будет отправлен всем пользователям бота @{0} после начала рассылки."
        ).format(bot.name)
    if call:
        await edit_or_create(call, text, keyboard, parse_mode="HTML")
    else:
        await AioBot.get_current().send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")


async def send_bot_text_menu(bot: Bot, call: ty.Optional[types.CallbackQuery] = None, chat_id: ty.Optional[int] = None):
    if call:
        await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Завершить редактирование"),
                                   callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty, chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Автоответчик"),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="next_text",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Сбросить текст"),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="reset_text",
                                                                   chat=empty))
    )

    text = dedent(_("""
    Сейчас вы редактируете текст, который отправляется после того, как пользователь отправит вашему боту @{0}
    команду /start

    Текущий текст:
    <pre>
    {1}
    </pre>
    Отправьте сообщение, чтобы изменить текст.
    """))
    text = text.format(bot.name, bot.start_text)
    if call:
        await edit_or_create(call, text, keyboard, parse_mode="HTML")
    else:
        await AioBot.get_current().send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")


async def send_bot_statistic_menu(bot: Bot, call: ty.Optional[types.CallbackQuery] = None,
                                  chat_id: ty.Optional[int] = None):
    if call:
        await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Назад"),
                                   callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty, chat=empty))
    )

    text = dedent(_("""
    Статистика по боту @{0}

    Входящих сообщений: <b>{1}</b>
    Ответных сообщений: <b>{2}</b>
    Шаблоны ответов: <b>{3}</b>
    Забанено пользователей: <b>{4}</b>
    """)).format(bot.name, bot.incoming_messages_count, bot.outgoing_messages_count, len(await bot.answers),
                 len(await bot.banned_users))
    if call:
        await edit_or_create(call, text, keyboard, parse_mode="HTML")
    else:
        await AioBot.get_current().send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")


async def send_bot_second_text_menu(bot: Bot, call: ty.Optional[types.CallbackQuery] = None,
                                    chat_id: ty.Optional[int] = None):
    if call:
        await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Завершить редактирование"),
                                   callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty, chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Предыдущий текст"),
                                   callback_data=menu_callback.new(level=2, bot_id=bot.id, operation="text",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Шаблоны ответов..."),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id, operation="templates",
                                                                   chat=empty))
    )
    keyboard.insert(
        types.InlineKeyboardButton(text=_("Сбросить текст"),
                                   callback_data=menu_callback.new(level=3, bot_id=bot.id,
                                                                   operation="reset_second_text", chat=empty))
    )

    text = dedent(_("""
    Сейчас вы редактируете текст автоответчика. Это сообщение отправляется в ответ на все входящие сообщения @{0} \
автоматически. По умолчанию оно отключено.

    Текущий текст:
    <pre>
    {1}
    </pre>
    Отправьте сообщение, чтобы изменить текст.
    """))
    text = text.format(bot.name, bot.second_text if bot.second_text else _("(отключено)"))
    if call:
        await edit_or_create(call, text, keyboard, parse_mode="HTML")
    else:
        await AioBot.get_current().send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")


async def send_bot_templates_menu(bot: Bot, call: ty.Optional[types.CallbackQuery] = None,
                                  chat_id: ty.Optional[int] = None):
    if call:
        await call.answer()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.insert(
        types.InlineKeyboardButton(text=_("<< Завершить редактирование"),
                                   callback_data=menu_callback.new(level=1, bot_id=bot.id, operation=empty, chat=empty))
    )

    text = dedent(_("""
    Сейчас вы редактируете шаблоны ответов для @{0}. Текущие шаблоны:

    <pre>
    {1}
    </pre>
    Отправьте какую-нибудь фразу (например: "Ваш заказ готов, ожидайте!"), чтобы добавить её в шаблон.
    Чтобы удалить шаблон из списка, отправьте его номер в списке (например, 4)
    """))

    templates = await bot.answers

    total_text_len = sum(len(t.text) for t in templates) + len(text)  # примерная длина текста
    max_len = 1000
    if total_text_len > 4000:
        max_len = 100

    templates_text = "\n".join(f"{n}. {wrap(template.text, max_len)}" for n, template in enumerate(templates))
    if not templates_text:
        templates_text = _("(нет шаблонов)")
    text = text.format(bot.name, templates_text)
    if call:
        await edit_or_create(call, text, keyboard, parse_mode="HTML")
    else:
        await AioBot.get_current().send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")


@dp.message_handler(state="wait_broadcast_text", content_types="text", regexp="^[^/].*")  # Not command
async def broadcast_text_received(message: types.Message, state: FSMContext):
    broadcast_text = message.html_text
    async with state.proxy() as proxy:
        bot_id = proxy.get("bot_id")
        proxy["broadcast_text"] = broadcast_text
    bot = await Bot.get_or_none(pk=bot_id)
    await send_bot_broadcast_menu(bot, chat_id=message.chat.id, text=broadcast_text)


@dp.message_handler(state="wait_start_text", content_types="text", regexp="^[^/].*")  # Not command
async def start_text_received(message: types.Message, state: FSMContext):
    async with state.proxy() as proxy:
        bot_id = proxy.get("bot_id")
    bot = await Bot.get_or_none(pk=bot_id)
    bot.start_text = message.html_text
    await bot.save()
    await send_bot_text_menu(bot, chat_id=message.chat.id)


@dp.message_handler(state="wait_second_text", content_types="text", regexp="^[^/].*")  # Not command
async def second_text_received(message: types.Message, state: FSMContext):
    async with state.proxy() as proxy:
        bot_id = proxy.get("bot_id")
    bot = await Bot.get_or_none(pk=bot_id)
    bot.second_text = message.html_text
    await bot.save()
    await send_bot_second_text_menu(bot, chat_id=message.chat.id)


@dp.message_handler(state="wait_template", content_types="text", regexp="^[^/].*")  # Not command
async def template_received(message: types.Message, state: FSMContext):
    async with state.proxy() as proxy:
        bot_id = proxy.get("bot_id")
    bot = await Bot.get_or_none(pk=bot_id)

    if message.text.isdigit():
        # Delete template
        number = int(message.text)
        templates = await bot.answers
        if not templates:
            await message.answer(_("У вас нет шаблонов, чтобы их удалять"))
        if number < 0 or number >= len(templates):
            await message.answer(_("Неправильное число. Чтобы удалить шаблон, введите число от 0 до {0}").format(
                len(templates)))
            return
        await templates[number].delete()
    else:
        # Add template
        total_templates = len(await bot.answers)
        if total_templates > 30:
            await message.answer(_("У вашего бота уже слишком много шаблонов"))
        else:
            answers = await bot.answers.filter(text=message.text)
            if answers:
                await message.answer(_("Такой текст уже есть в списке шаблонов"))
            else:
                template = DefaultAnswer(text=message.text, bot=bot)
                await template.save()

    await send_bot_templates_menu(bot, chat_id=message.chat.id)


@dp.callback_query_handler(menu_callback.filter(), state="*")
async def callback(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    level = callback_data.get("level")

    if level == "0":
        return await send_bots_menu(call.message.chat.id, call.from_user.id, call)

    bot_id = callback_data.get("bot_id")
    bot = await Bot.get_or_none(id=bot_id)
    if not bot or (await bot.owner).telegram_id != call.from_user.id:
        await call.answer(_("У вас нет прав на этого бота"), show_alert=True)
        return

    if level == "1":
        await state.reset_state()
        return await send_bot_menu(bot, call)

    operation = callback_data.get("operation")
    if level == "2":
        await state.reset_state()
        if operation == "chat":
            return await send_chats_menu(bot, call)
        if operation == "delete":
            return await send_bot_delete_menu(bot, call)
        if operation == "stat":
            return await send_bot_statistic_menu(bot, call)
        if operation == "settings":
            return await send_bot_settings_menu(bot, call)
        if operation == "broadcast":
            await state.set_state("wait_broadcast_text")
            async with state.proxy() as proxy:
                proxy["bot_id"] = bot.id
            return await send_bot_broadcast_menu(bot, call)
        if operation == "text":
            await state.set_state("wait_start_text")
            async with state.proxy() as proxy:
                proxy["bot_id"] = bot.id
            return await send_bot_text_menu(bot, call)

    if level == "3":
        if operation == "delete_yes":
            return await bot_actions.delete_bot(bot, call)
        if operation == "chat":
            return await bot_actions.select_chat(bot, call, callback_data.get("chat"))
        if operation == "threads":
            await bot_actions.threads(bot, call)
            return await send_bot_settings_menu(bot, call)
        if operation == "antiflood":
            await bot_actions.antiflood(bot, call)
            return await send_bot_settings_menu(bot, call)
        if operation == "additional_info":
            await bot_actions.additional_info(bot, call)
            return await send_bot_settings_menu(bot, call)
        if operation == "olgram_text":
            await bot_actions.olgram_text(bot, call)
            return await send_bot_settings_menu(bot, call)
        if operation == "reset_text":
            await bot_actions.reset_bot_text(bot, call)
            return await send_bot_text_menu(bot, call)
        if operation == "next_text":
            await state.set_state("wait_second_text")
            async with state.proxy() as proxy:
                proxy["bot_id"] = bot.id
            return await send_bot_second_text_menu(bot, call)
        if operation == "reset_second_text":
            await bot_actions.reset_bot_second_text(bot, call)
            return await send_bot_second_text_menu(bot, call)
        if operation == "start_broadcast":
            async with state.proxy() as proxy:
                text = proxy.get("broadcast_text")
            return await bot_actions.start_broadcast(bot, call, text)
        if operation == "templates":
            await state.set_state("wait_template")
            async with state.proxy() as proxy:
                proxy["bot_id"] = bot.id
            return await send_bot_templates_menu(bot, call)
