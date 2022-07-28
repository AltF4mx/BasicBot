import pymorphy2

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
from app.utils import update_slang
from app.utils import del_from_slang
from app.utils import warn, unwarn, get_mention
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
            message = await warn(event.chat.id, event.sender.id, get_mention(event.sender))
            await event.respond(message, buttons=Button.inline('Показать сообщение?', event.text))
            await event.delete()
    
#    if RegexpProc.test(event.text):
#        await event.reply('Ты че, ска?!!')

@bot.on(events.CallbackQuery)
async def show_text(event: events.CallbackQuery.Event):
    member = await ChatMember.get_or_none(chat_id=event.chat.id, user_id=event.sender_id)
    button_message = await event.get_message()
    if member.is_admin:
        await bot.send_message(event.sender_id, event.data.decode('UTF-8'))
        await event.answer('Текст сообщения направлен в ЛС.')
        await button_message.edit(buttons=None)
    else:
        await event.answer('Только для админов!', alert=True)
    

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
                word_list_cut = \
                    await Slang.filter(word__startswith=event.text.lower()).values_list('word', flat=True)
                
                if not word_list_cut:
                    await event.respond(f'В списке нет слов, начинающихся на "{event.text}"')
                    await event.respond('Добавить слово можно при помощи команды /addword.')
                    bot.remove_event_handler(word_list_filter, events.NewMessage)
                    return
                
                await bot.send_message(event.sender_id, ', '.join(word_list_cut))
                await event.respond('Список слов направлен Вам в ЛС.')
                await event.respond('Удалить слово можно при помощи команды /delword.')
                await event.respond('Добавить слово можно при помощи команды /addword.')
                
                bot.remove_event_handler(word_list_filter, events.NewMessage)

@admin_command('addword')
async def add_word(event: Message):
    await event.respond('В ответном сообщении напишите слово, которое нужно добавить.')
    
    @bot.on(events.NewMessage(func=lambda e: e.is_group))
    async def normalise_and_load(event: Message):
        if event.is_reply:
            reply_to = await event.get_reply_message()
            if reply_to.sender.bot:
                morph = pymorphy2.MorphAnalyzer()
                normal_word = morph.parse(event.text.lower())[0].normal_form
                await update_slang(normal_word)
                await event.respond(f'Слово {event.text} добавлено в словарь.')
                
                bot.remove_event_handler(normalise_and_load, events.NewMessage)

@admin_command('delword')
async def del_word(event: Message):
    await event.respond('В ответном сообщении напишите слово, которое хотите удалить.')
    
    @bot.on(events.NewMessage(func=lambda e: e.is_group))
    async def lower_and_del(event: Message):
        if event.is_reply:
            reply_to = await event.get_reply_message()
            if reply_to.sender.bot:
                del_result = await del_from_slang(event.text.lower())
                if del_result:
                    await event.respond(f'Слово "{event.text}" удалено из словаря.')
                else:
                    await event.respond(f'В словаре нет слова "{event.text}".')
        
                bot.remove_event_handler(lower_and_del, events.NewMessage)
                
@admin_command('help')
async def show_help(event: Message):
    text = "Вы можете использовать следующие команды, отвечая на сообщения пользователя:\n \
    /mute и /unmute - запретить/разрешить пользователю писать;\n \
    /ban и /unban - забанить/разбанить пользователя;\n \
    /kick - исключить пльзователя из чата;\n \
    /warn и /unwarn - предупредить/снять предупреждение с пользователя.\n \
    \nСледующие команды не требуют цитирования:\n \
    /listword - вывести список запрещенных слов в словаре;\n \
    /addword и /delword - добавить/удалить запрещенное слово из словаря."
    await bot.send_message(event.sender_id, text)
    await event.respond('Список команд направлен Вам в ЛС.')

@admin_command('settings') # TO DO добавить подсчет статистики
async def show_settings(event: Message):
    await event.respond('Выберите что Вы хотите настроить:', \
                        buttons=Button.inline('Показать статистику', 'Какая-то стата'))

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
    return await warn(chat_id, user_id, mention)

@admin_moderate_command('unwarn')
async def unwarn_command(chat_id: int, user_id: int, mention: str):
    return await unwarn(chat_id, user_id, mention)
