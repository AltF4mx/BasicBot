from tortoise import timezone

from telethon.tl.types import ChannelParticipantsAdmins

from app import bot
from app.models import Chat, ChatMember

async def update_chat_member(chat_id: int, user_id: int, **kwargs):
    await ChatMember.update_or_create(chat_id=chat_id, user_id=user_id, defaults=kwargs)

async def is_admin(chat_id: int, user_id: int):
    member = await ChatMember.get_or_none(chat_id=chat_id, user_id=user_id)
    return member and member.is_admin

async def reload_admins(chat_id):
    await ChatMember.filter(chat_id=chat_id, is_admin=True).update(is_admin=False)
    
    participants = await bot.get_participants(chat_id, filter=ChannelParticipantsAdmins())
    for participant in participants:
        await update_chat_member(chat_id, participant.id, is_admin=True)
    
    chat = await Chat.get(id=chat_id)
    chat.last_admins_update = timezone.now()
    await chat.save()

