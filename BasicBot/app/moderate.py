from telethon import events
from telethon.tl.custom import Message
from telethon.errors import ChatAdminRequiredError

from app import bot
from app.utils import update_chat_member
from app.models import Chat, ChatMember

async def warn(chat_id: int, user_id: int, mention: str):
    member = await ChatMember.get_or_none(chat_id=chat_id, user_id=user_id)
    warns = member.warns if member else 0
    warns = min(warns + 1, 5)
    await update_chat_member(chat_id, user_id, warns=warns)
    
    if warns == 5:
        try:
            await bot.edit_permissions(chat_id, user_id, send_messages=False)
        except ChatAdminRequiredError:
            return f'Участник {mention} получил 5 предупреждений. Я бы его замьютил,' \
                   f'но мне недостает прав...'
        else:
            return f'Участник {mention} получил 5 предупреждений и теперь должен помолчать.'
    return f'Участнику {mention} выдано предупреждение ({warns}/5)'
