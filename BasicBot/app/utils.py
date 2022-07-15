import json

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
    print(f'слово {word} загружено')


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
                await event.respond('Не админ, не командуй!))')
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