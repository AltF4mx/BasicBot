from telethon import events
from datetime import timedelta
from tortoise import timezone
from telethon.tl.custom import Message

from app import bot
from app.utils import reload_admins
from app.utils import admin_command
from app.utils import admin_moderate_command
from app.utils import update_chat_member
from app.models import Chat, ChatMember

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
async def unmute_command(chat_id: int, user_id: int, mention: str):
    await bot.edit_permissions(chat_id, user_id, send_messages=True)
    return f'Теперь {mention} может говорить, послушаем же его...'

@admin_moderate_command('ban')
async def ban_command(chat_id: int, user_id: int, mention: str):
    await bot.edit_permissions(chat_id, user_id, view_messages=False)
    return f'{mention}, прощай...'

@admin_moderate_command('unban')
async def unban_command(chat_id: int, user_id: int, mention: str):
    await bot.edit_permissions(chat_id, user_id, view_messages=True)
    return f'{mention}, с возвращением!'

@admin_moderate_command('kick')
async def kick_command(chat_id: int, user_id: int, mention: str):
    await bot.kick_participant(chat_id, user_id)
    return f'{mention}, до свидания...'

@admin_moderate_command('warn')
async def warn_command(chat_id: int, user_id: int, mention: str):
    member = await ChatMember.get_or_none(chat_id=chat_id, user_id=user_id)
    warns = member.warns if member else 0
    warns = min(warns + 1, 3)
    await update_chat_member(chat_id, user_id, warns=warns)
    
    if warns == 3:
        try:
            await bot.edit_permissions(chat_id, user_id, send_messages=False)
        except ChatAdminRequiredError:
            return f'Участник {mention} получил 3 предупреждения. Я бы его замьютил,' \
                   f'но мне недостает прав...'
        else:
            return f'Участник {mention} получил 3 предупреждения и теперь должен помолчать.'
    return f'Участнику {mention} выдано предупреждение ({warns}/3)'

@admin_moderate_command('unwarn')
async def unwarn_command(chat_id: int, user_id: int, mention: str):
    member = await ChatMember.get_or_none(chat_id=chat_id, user_id=user_id)
    warns = member.warns if member else 0
    if warns == 0:
        return f'Эмм, так у {mention} нечего отменять...'
    warns -= 1
    await update_chat_member(chat_id, user_id, warns=warns)
    if warns == 2:
        try:
            await bot.edit_permissions(chat_id, user_id, send_messages=True)
        except ChatAdminRequiredError:
            return f'Предупреждение участнику {mention} отменено ({warns}/3). Разбаньте его кто-нибудь...'
        else:
            return f'Предупреждение участнику {mention} отменено ({warns}/3). Так уж и быть, разбаню.'
    return f'Предупреждение участнику {mention} отменено ({warns}/3).'
