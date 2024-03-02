import logging
from io import BytesIO
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.exceptions import TelegramAPIError
from aiogram import types, Bot as AioBot

from typing import Optional


async def try_delete_message(message: Message):
    try:
        await message.delete()
    except TelegramAPIError:
        pass


async def edit_or_create(call: CallbackQuery, message: str,
                         reply_markup: Optional[InlineKeyboardMarkup] = None,
                         parse_mode: Optional[str] = None):
    try:
        await call.message.edit_text(message, parse_mode=parse_mode)
        await call.message.edit_reply_markup(reply_markup)
    except TelegramAPIError:  # кнопка устарела
        await call.bot.send_message(call.message.chat.id, text=message, reply_markup=reply_markup,
                                    parse_mode=parse_mode)


def wrap(data: str, max_len: int) -> str:
    if len(data) > max_len:
        data = data[:max_len-4] + "..."
    return data


def button_text_limit(data: str) -> str:
    return wrap(data, 30)


async def send_stored_message(storage: dict, bot: AioBot, chat_id: int):
    content_type = storage["mailing_content_type"]
    if content_type == types.ContentType.TEXT:
        return await bot.send_message(chat_id, storage["mailing_text"], parse_mode="HTML")
    if content_type == types.ContentType.LOCATION:
        return await bot.send_location(chat_id, storage["mailing_location"][0], storage["mailing_location"][1])
    if content_type in (types.ContentType.AUDIO, types.ContentType.VIDEO, types.ContentType.DOCUMENT,
                        types.ContentType.PHOTO):
        caption = storage.get("mailing_caption")
        if storage.get("mailing_id"):
            logging.info("Mailing use file id")
            obj = storage["mailing_id"]
        else:
            logging.info("Mailing upload file")
            obj = types.InputFile(BytesIO(storage["mailing_data"]), filename=storage.get("mailing_file_name"))

        if content_type == types.ContentType.AUDIO:
            return (await bot.send_audio(chat_id, audio=obj, caption=caption)).audio.file_id
        if content_type == types.ContentType.PHOTO:
            return (await bot.send_photo(chat_id, photo=obj, caption=caption)).photo[-1].file_id
        if content_type == types.ContentType.VIDEO:
            return (await bot.send_video(chat_id, video=obj, caption=caption)).video.file_id
        if content_type == types.ContentType.DOCUMENT:
            return (await bot.send_document(chat_id, document=obj, caption=caption)).document.file_id

    raise NotImplementedError("Mailing, unknown content type")
