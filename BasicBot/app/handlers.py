from telethon import events
from datetime import timedelta
from tortoise import timezone
from telethon.tl.custom import Message
from telethon.tl.custom import Button

from app import bot
from app.utils import reload_admins
from app.utils import admin_command
from app.utils import admin_moderate_command
from app.utils import update_chat_member
from app.utils import upload_words_from_json
from app.models import Chat, ChatMember, Slang
from app.slang_checker import RegexpProc, PymorphyProc, get_words

@bot.on(events.ChatAction())
async def on_join(event: events.ChatAction.Event):
    if event.is_group and event.user_added and event.user_id == bot.me.id:
        await bot.send_message(event.chat.id, 'Всем привет!')
        await bot.send_message(event.chat.id, 'Я ' + \
        f'<a href="tg://user?id={bot.me.id}">{bot.me.first_name}</a>' + '!')
        
        await bot.send_message(event.chat.id, 'Я послежу тут за вами немного ;)')
        await bot.send_message(event.chat.id, 'Для получения справки по командами нажмите кнопку внизу.', \
        buttons=Button.text('/help', resize=True, single_use=True))
        
        chat = await Chat.get_or_none(id=event.chat.id)
        if chat is None:
            chat = Chat(id=event.chat.id)
            await chat.save()
            await reload_admins(event.chat.id)

@bot.on(events.ChatAction(func=lambda e: (e.user_added or e.user_joined) and e.user_id != bot.me.id))
async def greet(event: events.ChatAction.Event):
    await event.respond('Привет, ' + \
                        f'<a href="tg://user?id={event.user.id}">{event.user.first_name}</a>' + \
                        ', веди себя хорошо!')

@bot.on(events.NewMessage(func=lambda e: e.text.lower() == '/reload' and e.is_group))
async def reload_command(event: Message):
    await reload_admins(event.chat.id)
    await event.respond('Список админов группы обновлен.')
    
@bot.on(events.NewMessage(func=lambda e: e.text.lower() == '/uplwords' and e.is_group))
async def upload_words(event: Message):
    await upload_words_from_json()
    await event.respond('Список ненормативных слов загружен в базу.')


@bot.on(events.NewMessage(func=lambda e: e.is_group))
async def new_message(event: Message):
    chat = await Chat.get(id=event.chat.id)
    if timezone.now() - chat.last_admins_update > timedelta(hours=1):
        await reload_admins(event.chat.id)
    
    await get_words()
    if PymorphyProc.test(event.text):
        member = await ChatMember.get_or_none(chat_id=event.chat.id, user_id=event.sender.id)
        if not member or not member.is_admin:
            await event.reply('Ты че, ска?!!')
    
#    if RegexpProc.test(event.text):
#        await event.reply('Ты че, ска?!!')

@admin_command('greet')
async def greet_command(event: Message):
    await event.respond('Привет, хозяин!')
    
@admin_command('listword')
async def show_list_word(event: Message):
    word_list = await get_words()
    await event.respond(f'В списке {len(word_list)} слов(а).')
    await event.respond('Введите начальные буквы в ответном сообщении для вывода ограниченного количества слов:')
    
    @bot.on(events.NewMessage(func=lambda e: e.is_group))
    async def word_list_filter(event: Message):
        if event.is_reply:
            reply_to = await event.get_reply_message()
            if reply_to.sender.bot:
                word_dict_cut = await Slang.filter(word__startswith=event.text.lower()).values('word')
                
                if len(word_dict_cut) == 0:
                    await event.respond(f'В списке нет слов, начинающихся на "{event.text}"')
                    bot.remove_event_handler(word_list_filter, events.NewMessage)
                    return
                
                word_list_cut = []
                for item in word_dict_cut:
                    word_list_cut.append(item['word'])
                
                await event.respond(', '.join(word_list_cut))
                await event.respond('Удалить слово можно при помощи команды /delword.')
                await event.respond('Добавить слово можно при помощи команды /addword.')
                
                bot.remove_event_handler(word_list_filter, events.NewMessage)

@admin_command('help')
async def show_help(event: Message):
    text = "Вы можете использовать следующие команды, отвечая на сообщения пользователя:\n \
    /mute и /unmute - запретить/разрешить пользователю писать;\n \
    /ban и /unban - забанить/разбанить пользователя;\n \
    /kick - исключить пльзователя из чата;\n \
    /warn и /unwarn - предупредить/снять предупреждение с пользователя.\n"
    await bot.send_message(event.chat_id, text)

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
