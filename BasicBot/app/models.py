from tortoise.models import Model
from tortoise import fields

class Chat(Model):
    id = fields.BigIntField(pk=True)
    last_admins_update = fields.DatetimeField(null=True)
    
    class Meta:
        table = 'chats'
    
class ChatMember(Model):
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField()
    chat_id = fields.BigIntField()
    is_admin = fields.BooleanField(default=False)
    warns = fields.IntField(default=0)
    
    class Meta:
        table = 'chat_members'
        
class Slang(Model):
    id = fields.IntField(pk=True)
    word = fields.CharField(max_length=255, unique=True)
    
    class Meta:
        table = 'slang'