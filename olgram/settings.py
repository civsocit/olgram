from dotenv import load_dotenv
from abc import ABC
import os
import logging
from functools import lru_cache
from datetime import timedelta
import typing as ty
from olgram.utils.crypto import Cryptor

load_dotenv()


# TODO: рефакторинг, использовать какой-нибудь lazy-config вместо своих костылей

class AbstractSettings(ABC):
    @classmethod
    def _get_env(cls, parameter: str, allow_none: bool = False) -> str:
        parameter_v = os.getenv(parameter, None)
        if not parameter_v and not allow_none:
            raise ValueError(f"{parameter} not defined in ENV")
        return parameter_v


class OlgramSettings(AbstractSettings):
    @classmethod
    def max_bots_per_user(cls) -> int:
        """
        Максимальное количество ботов у одного пользователя
        :return: int
        """
        return 10

    @classmethod
    def max_bots_per_user_promo(cls) -> int:
        """
        Максимальное количество ботов у одного пользователя с промо-доступом
        :return: int
        """
        return 25

    @classmethod
    def version(cls):
        return "0.7.2"

    @classmethod
    @lru_cache
    def admin_ids(cls):
        _ids = cls._get_env("ADMIN_ID", True)
        return set(map(int, _ids.split(","))) if _ids else None

    @classmethod
    @lru_cache
    def supervisor_id(cls):
        _id = cls._get_env("SUPERVISOR_ID", True)
        return int(_id) if _id else None


class ServerSettings(AbstractSettings):
    @classmethod
    def hook_host(cls) -> str:
        return cls._get_env("WEBHOOK_HOST")

    @classmethod
    def hook_port(cls) -> int:
        return int(cls._get_env("WEBHOOK_PORT"))

    @classmethod
    def app_port(cls) -> int:
        return 80

    @classmethod
    def redis_path(cls) -> str:
        """
        Путь до БД redis
        :return:
        """
        return cls._get_env("REDIS_PATH")

    @classmethod
    def use_custom_cert(cls) -> bool:
        use = cls._get_env("CUSTOM_CERT", allow_none=True)
        return use and "true" in use.lower()

    @classmethod
    def priv_path(cls) -> str:
        return "/cert/private.key"

    @classmethod
    def public_path(cls) -> str:
        return "/cert/public.pem"

    @classmethod
    def append_text(cls) -> str:
        return "\n\nЭтот бот создан с помощью @OlgramBot"

    @classmethod
    @lru_cache
    def redis_timeout_ms(cls) -> ty.Optional[int]:
        return int(timedelta(days=180).total_seconds() * 1000.0)

    @classmethod
    @lru_cache
    def thread_timeout_ms(cls) -> int:
        return int(timedelta(days=1).total_seconds() * 1000.0)


logging.basicConfig(level=os.environ.get("LOGLEVEL") or "WARNING",
                    format='%(asctime)s %(levelname)-8s %(message)s')


class BotSettings(AbstractSettings):
    @classmethod
    @lru_cache
    def token(cls) -> str:
        """
        Токен olgram бота
        :return:
        """
        return cls._get_env("BOT_TOKEN")

    @classmethod
    def language(cls) -> str:
        """
        Язык
        """
        lang = cls._get_env("O_LANG", allow_none=True)
        return lang.lower() if lang else "ru"


class DatabaseSettings(AbstractSettings):
    @classmethod
    def user(cls) -> str:
        return cls._get_env("POSTGRES_USER")

    @classmethod
    def password(cls) -> str:
        return cls._get_env("POSTGRES_PASSWORD")

    @classmethod
    def database_name(cls) -> str:
        return cls._get_env("POSTGRES_DB")

    @classmethod
    def host(cls) -> str:
        return cls._get_env("POSTGRES_HOST")

    @classmethod
    @lru_cache
    def cryptor(cls) -> Cryptor:
        password = cls._get_env("TOKEN_ENCRYPTION_KEY")
        return Cryptor(password)


TORTOISE_ORM = {
    "connections": {"default": f'postgres://{DatabaseSettings.user()}:{DatabaseSettings.password()}'
                               f'@{DatabaseSettings.host()}/{DatabaseSettings.database_name()}'},
    "apps": {
        "models": {
            "models": ["olgram.models.models", "aerich.models"],
            "default_connection": "default",
        },
    },
    "use_tz": False,
    "timezone": "UTC"
}
