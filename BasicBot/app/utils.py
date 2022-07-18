import json
import logging

from tortoise import timezone

from telethon import events
from telethon.errors import ChatAdminRequiredError
from telethon.tl.custom import Message
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.tl.types import User

from app import bot
from app.models import Chat, ChatMember, Slang

async def upload_words_from_json():
    with open("./word_data.json", 'r') as w:
        words = json.load(w)
        for item in words:
            await update_slang(word=item['fields']['word'])

async def update_slang(word: str):
    await Slang.update_or_create(word=word)
    logging.info(f'Слово {word} загружено')

async def del_from_slang(word: str):
    if not await Slang.filter(word=word).exists():
        return False
    try:
        await Slang.filter(word=word).delete()
        logging.info(f'Слово {word} удалено.')
        return True
    except:
        return False

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

def admin_command(command: str):
    def decorator(func):
        pattern = f'(?i)^/{command}$'
        @bot.on(events.NewMessage(pattern=pattern, func=lambda e: e.is_group))
        async def handle(event: Message):
            if not await is_admin(event.chat.id, event.sender.id):
                await event.reply('Не админ, не командуй!))')
                return
    
            try:
                await func(event)
            except ChatAdminRequiredError:
                await event.respond('Упс... А я не админ...')
                
        return handle
    return decorator

def get_mention(user: User):
    name = user.first_name
    if user.last_name:
        user += ' ' + user.last_name
    return f'<a href="tg://user?id={user.id}">{name}</a>'

def admin_moderate_command(command: str):
    def decorator(func):
        @admin_command(command)
        async def handle(event: Message):
            if not event.is_reply:
                await event.respond('Ответь этой командой на сообщение пользователя, по-братски...')
                return
            
            reply_to = await event.get_reply_message()
            
            if reply_to.sender.bot:
                await event.respond('Бота не трогай, ладно?')
                return
            if await is_admin(event.chat.id, reply_to.sender.id):
                await event.respond('Не рекомендую делать это с админом...')
                return
            
            result = await func(event.chat.id, reply_to.sender.id, get_mention(reply_to.sender))
            await event.respond(result)
            
        return handle
    return decorator

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

async def unwarn(chat_id: int, user_id: int, mention: str):
    member = await ChatMember.get_or_none(chat_id=chat_id, user_id=user_id)
    warns = member.warns if member else 0
    if warns == 0:
        return f'Эмм, так у {mention} нечего отменять...'
    warns -= 1
    await update_chat_member(chat_id, user_id, warns=warns)
    if warns == 4:
        try:
            await bot.edit_permissions(chat_id, user_id, send_messages=True)
        except ChatAdminRequiredError:
            return f'Предупреждение участнику {mention} отменено ({warns}/5). Разбаньте его кто-нибудь...'
        else:
            return f'Предупреждение участнику {mention} отменено ({warns}/5). Так уж и быть, разбаню.'
    return f'Предупреждение участнику {mention} отменено ({warns}/5).'