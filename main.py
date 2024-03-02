import asyncio
import argparse
from tortoise import Tortoise

from olgram.router import dp
from olgram.settings import TORTOISE_ORM, OlgramSettings
from olgram.utils.permissions import AccessMiddleware
from server.custom import init_redis

import olgram.commands.menu  # noqa: F401
import olgram.commands.bots  # noqa: F401
import olgram.commands.start  # noqa: F401
import olgram.commands.bot_actions  # noqa: F401
import olgram.commands.info  # noqa: F401
import olgram.commands.promo  # noqa: F401
import olgram.commands.admin  # noqa: F401
from locales.locale import _

from server.server import main as server_main


async def init_database():
    await Tortoise.init(config=TORTOISE_ORM)


async def init_olgram():
    from olgram.router import bot, dp
    dp.setup_middleware(AccessMiddleware(OlgramSettings.admin_ids()))
    from aiogram.types import BotCommand
    await bot.set_my_commands(
        [
            BotCommand("start", _("Запустить бота")),
            BotCommand("addbot", _("Добавить бот")),
            BotCommand("mybots", _("Управление ботами")),
            BotCommand("help", _("Справка"))
        ]
    )


async def initialization():
    await init_database()
    await init_redis()
    await init_olgram()


def main():
    parser = argparse.ArgumentParser("Olgram bot and feedback server")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--noserver", help="Не запускать сервер обратной связи, только сам Olgram", action="store_true")
    group.add_argument("--onlyserver", help="Запустить только сервер обратной связи, без Olgram", action="store_true")
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(initialization())

    if not args.onlyserver:
        print("Run olgram polling")
        loop.create_task(dp.start_polling())
    if not args.noserver:
        print("Run olgram server")
        loop.create_task(server_main().start())

    loop.run_forever()


if __name__ == '__main__':
    main()
