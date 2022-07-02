from tortoise.models import Model
from tortoise import fields

class Chat(Model):
    tablename = 'chats'
    id = fields.BigIntField(pk=True)
    last_admins_update = fields.DatetimeField(null=True)
    
class ChatMember(Model):
    tablename = 'chat_members'
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField()
    chat_id = fields.BigIntField()
    is_admin = fields.BooleanField(default=False)