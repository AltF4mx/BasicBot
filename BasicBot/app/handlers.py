from telethon import events
from datetime import timedelta
from tortoise import timezone
from telethon.tl.custom import Message

from app import bot
from app.utils import reload_admins
from app.utils import admin_command
from app.utils import admin_moderate_command
from app.models import Chat

@bot.on(events.ChatAction())
async def on_join(event: events.ChatAction.Event):
    if event.is_group and event.user_added and event.user_id == bot.me.id:
        await bot.send_message(event.chat.id, 'Всем привет!')
        await bot.send_message(event.chat.id, 'Я ' + bot.me.first_name + '!')
        await bot.send_message(event.chat.id, 'Я послежу тут за вами немного ;)')
        chat = await Chat.get_or_none(id=event.chat.id)
        if chat is None:
            chat = Chat(id=event.chat.id)
            await chat.save()
            await reload_admins(event.chat.id)

@bot.on(events.ChatAction(func=lambda e: (e.user_added or e.user_joined) and e.user_id != bot.me.id))
async def greet(event: events.ChatAction.Event):
    await event.respond('Привет, ' + event.user.first_name + ', веди себя хорошо!')

@bot.on(events.NewMessage(func=lambda e: e.text.lower() == '/reload' and e.is_group))
async def reload_command(event: Message):
    await reload_admins(event.chat.id)
    await event.respond('Список админов группы обновлен.')

@bot.on(events.NewMessage(func=lambda e: e.is_group))
async def new_message(event: Message):
    chat = await Chat.get(id=event.chat.id)
    if timezone.now() - chat.last_admins_update > timedelta(hours=1):
        await reload_admins(event.chat.id)

@admin_command('greet')
async def greet_command(event: Message):
    await event.respond('Привет, хозяин!')

@admin_moderate_command('mute')
async def mute_command(chat_id: int, user_id: int, mention: str):
    await bot.edit_permissions(chat_id, user_id, send_messages=False)
    return f'{mention} помолчи немного...'

@admin_moderate_command('unmute')
async def unmute_command(chat_id: int, user_id: int, mention:str):
    await bot.edit_permissions(chat_id, user_id, send_messages=True)
    return f'Теперь {mention} может говорить, послушаем же его...'
