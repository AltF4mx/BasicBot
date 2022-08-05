from tortoise.models import Model
from tortoise import fields

class Chat(Model):
    id = fields.BigIntField(pk=True)
    last_admins_update = fields.DatetimeField(null=True)
    joined = fields.DatetimeField(null=True)
    users = fields.IntField(default=0)
    messages_checked = fields.IntField(default=0)
    bad_words_detected = fields.IntField(default=0)
    users_muted = fields.IntField(default=0)
    users_kicked = fields.IntField(default=0)
    users_banned = fields.IntField(default=0)
    filter_enable = fields.BooleanField(default=True)
    filter_mode = fields.CharField(max_length=10, default='dict')
    warns_number = fields.IntField(default=3)
    penalty_mode = fields.CharField(max_length=10, default='mute')
    mute_duration = fields.IntField(default=30)
    
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