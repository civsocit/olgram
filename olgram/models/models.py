from tortoise.models import Model
from tortoise import fields
from uuid import uuid4
from textwrap import dedent
from olgram.settings import DatabaseSettings
from locales.locale import _


class MetaInfo(Model):
    id = fields.IntField(pk=True)
    version = fields.IntField(default=0)

    def __init__(self, **kwargs):
        # Кажется это единственный способ сделать single-instance модель в TortoiseORM :(
        if "id" in kwargs:
            kwargs["id"] = 0
        self.id = 0
        super(MetaInfo, self).__init__(**kwargs)

    class Meta:
        table = '_custom_meta_info'


class Bot(Model):
    id = fields.IntField(pk=True)
    token = fields.CharField(max_length=200, unique=True)
    owner = fields.ForeignKeyField("models.User", related_name="bots")
    name = fields.CharField(max_length=33)
    code = fields.UUIDField(default=uuid4, index=True)
    start_text = fields.TextField(default=dedent(_("""
    Здравствуйте!
    Напишите ваш вопрос и мы ответим вам в ближайшее время.
    """)))
    second_text = fields.TextField(null=True, default=None)

    group_chats = fields.ManyToManyField("models.GroupChat", related_name="bots", on_delete=fields.relational.CASCADE,
                                         null=True)
    group_chat = fields.ForeignKeyField("models.GroupChat", related_name="active_bots",
                                        on_delete=fields.relational.CASCADE,
                                        null=True)

    incoming_messages_count = fields.BigIntField(default=0)
    outgoing_messages_count = fields.BigIntField(default=0)

    enable_threads = fields.BooleanField(default=False)
    enable_additional_info = fields.BooleanField(default=False)
    enable_olgram_text = fields.BooleanField(default=True)
    enable_antiflood = fields.BooleanField(default=False)
    enable_always_second_message = fields.BooleanField(default=False)
    enable_thread_interrupt = fields.BooleanField(default=True)
    enable_mailing = fields.BooleanField(default=False)
    last_mailing_at = fields.DatetimeField(null=True, default=None)

    def decrypted_token(self):
        cryptor = DatabaseSettings.cryptor()
        return cryptor.decrypt(self.token)

    @classmethod
    def encrypted_token(cls, token: str):
        cryptor = DatabaseSettings.cryptor()
        return cryptor.encrypt(token)

    async def super_chat_id(self):
        group_chat = await self.group_chat
        if group_chat:
            return group_chat.chat_id
        return (await self.owner).telegram_id

    async def is_promo(self):
        await self.fetch_related("owner")
        return await self.owner.is_promo()

    class Meta:
        table = 'bot'


class BotStartMessage(Model):
    id = fields.IntField(pk=True)
    bot = fields.ForeignKeyField("models.Bot", related_name="start_texts", on_delete=fields.CASCADE)
    locale = fields.CharField(max_length=15)
    text = fields.TextField()

    class Meta:
        unique_together = ("bot", "locale")
        table = 'bot_start_message'


class BotSecondMessage(Model):
    id = fields.IntField(pk=True)
    bot = fields.ForeignKeyField("models.Bot", related_name="second_texts", on_delete=fields.CASCADE)
    locale = fields.CharField(max_length=5)
    text = fields.TextField()

    class Meta:
        unique_together = ("bot", "locale")
        table = 'bot_second_message'


class User(Model):
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(index=True, unique=True)

    async def is_promo(self):
        await self.fetch_related("promo")
        return bool(self.promo)

    class Meta:
        table = 'user'


class MailingUser(Model):
    id = fields.BigIntField(pk=True)
    telegram_id = fields.BigIntField(index=True)

    bot = fields.ForeignKeyField("models.Bot", related_name="mailing_users", on_delete=fields.relational.CASCADE)

    class Meta:
        table = 'mailinguser'
        unique_together = (("bot", "telegram_id"), )


class GroupChat(Model):
    id = fields.IntField(pk=True)
    chat_id = fields.BigIntField(index=True, unique=True)
    name = fields.CharField(max_length=255)

    class Meta:
        table = 'group_chat'


class BannedUser(Model):
    id = fields.BigIntField(pk=True)
    telegram_id = fields.BigIntField(index=True)
    username = fields.CharField(max_length=100, default=None, null=True)

    bot = fields.ForeignKeyField("models.Bot", related_name="banned_users", on_delete=fields.relational.CASCADE)

    class Meta:
        table = "bot_banned_user"


class DefaultAnswer(Model):
    id = fields.BigIntField(pk=True)
    bot = fields.ForeignKeyField("models.Bot", related_name="answers", on_delete=fields.relational.CASCADE)
    text = fields.TextField()


class Promo(Model):
    id = fields.BigIntField(pk=True)
    code = fields.UUIDField(default=uuid4, index=True)
    date = fields.DatetimeField(auto_now_add=True)

    owner = fields.ForeignKeyField("models.User", related_name="promo", on_delete=fields.relational.SET_NULL,
                                   null=True, default=None)
