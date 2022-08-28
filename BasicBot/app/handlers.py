import re
import logging

import pymorphy2

from telethon import events
from datetime import timedelta
from tortoise import timezone
from telethon.tl.custom import Message
from telethon.tl.custom import Button
from telethon.errors import UserIsBlockedError, PeerIdInvalidError

from app import bot, templates
from app.utils import reload_admins
from app.utils import admin_command
from app.utils import admin_moderate_command
from app.utils import update_chat_member
from app.utils import upload_words_from_json
from app.utils import update_slang
from app.utils import del_from_slang
from app.utils import warn, unwarn, get_mention, agree_word
from app.models import Chat, ChatMember, Slang
from app.slang_checker import RegexpProc, PymorphyProc, get_words

from data import config

handlers_log = logging.getLogger('TGDroidModer.handlers')

# Обработчик команд и кнопок меню разработчика.
@bot.on(events.NewMessage(func=lambda e: e.text.lower() == '/dev_menu' and e.is_private))
async def developer_menu_command(event: Message):
    '''Отправляет меню разработчика только мне.'''
    if event.sender.id == config.DEV_ID:
        text, keyboard = templates.developer_menu()
        await bot.send_message(event.sender.id, text, buttons=keyboard)
    else:
        handlers_log.warning(f'Внимание! Пользователь {event.sender.first_name} ввел девелоперскую команду!')
        
@bot.on(events.CallbackQuery(pattern=r'^send_log/'))
async def close_button(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки "Прислать лог".'''
    try:
        await bot.send_file(event.sender_id, './data/basicbot.log')
    except Exception as Ex:
        await event.answer('Произошла ошибка при отправке, подробности в логе...', alert=True)
        handlers_log.error(Ex)

# Обработчики событий в чате (включая обработчик сообщений с фильтром) кроме сообщений с командами.
@bot.on(events.ChatAction())
async def on_join(event: events.ChatAction.Event):
    '''Приветствие участников при вступлении в группу (чат).
    
    Так же создает строку в базе для группы при отсутствии,
    сохраняет количество участников, обнуляет статистику,
    обновляет список админов.
    '''
    if event.is_group and event.user_added and event.user_id == bot.me.id:
        await bot.send_message(event.chat.id, 'Всем привет! \U0001F44B')
        await bot.send_message(event.chat.id, 'Я бот-модератор ' + \
        f'<a href="tg://user?id={bot.me.id}">{bot.me.first_name}</a>' + '!')
        await bot.send_message(event.chat.id, 'Я послежу тут за вами немного \U0001F440')
        
        chat = await Chat.get_or_none(id=event.chat.id)
        if chat is None:
            chat = Chat(id=event.chat.id)
            await chat.save()
        await reload_admins(event.chat.id)
        chat = await Chat.get(id=event.chat.id)
        chat.joined = timezone.now()        
        users = await bot.get_participants(event.chat.id)
        chat.users = len(users)
        chat.messages_checked = 0
        chat.bad_words_detected = 0
        chat.users_muted = 0
        chat.users_kicked = 0
        chat.users_banned = 0
        await chat.save()
        handlers_log.info(f'Успешно вступил в группу "{event.chat.title}", {chat.users} {agree_word("участник", chat.users)}.')

@bot.on(events.ChatAction(func=lambda e: (e.user_added or e.user_joined) and e.user_id != bot.me.id))
async def greet(event: events.ChatAction.Event):
    '''Приветствие нового участника группы (чата).
    
    Так же новый участник предупреждается о наказание за использование
    матерных слов если включен мат фильтр, если не включен -
    просто приветствуется. В базе обновляется количество участников.
    '''
    chat = await Chat.get(id=event.chat.id)
    p_mods = {
        'mute': f'\U0001F6A7 мьютом на {chat.mute_duration} минут.',
        'kick': '\U0001F6AB исключением из группы.',
        'ban': '\U0001F528 баном!'
    }
    penalty_warn = ''
    if chat.filter_enable:
        penalty_warn = ' Мат здесь запрещен, нарушение карается ' + p_mods[chat.penalty_mode]
    await event.respond('Привет, ' + \
                        f'<a href="tg://user?id={event.user.id}">{event.user.first_name}</a>' + \
                        ', веди себя хорошо!' + penalty_warn)
    
    users = await bot.get_participants(event.chat.id)
    chat.users = len(users)
    await chat.save()
    await reload_admins(event.chat.id)
    handlers_log.info(f'В группе "{event.chat.title}" новый участник {event.user.first_name} ({chat.users}).')

@bot.on(events.NewMessage(func=lambda e: e.is_group))
async def new_message(event: Message):
    '''Обработка новых сообщений в группе (чате).
    
    При каждом сообщении обновляется список админов, если с прошлого
    обновления прошло более часа. Если включен мат фильтр, сообщение
    проверяется на наличие мата выбранным способом, счетчик проверенных с
    ообщений увеличивается на 1, при выявлении мата, активируется предупреждение,
    счетчик плохих слов увеличивается на 1, сообщение с матом удаляется,
    в чат соощается о нарушении.
    '''
    chat = await Chat.get(id=event.chat.id)
    if timezone.now() - chat.last_admins_update > timedelta(hours=1):
        await reload_admins(event.chat.id)
    
    word_filter = {'dict': PymorphyProc, 'pattern': RegexpProc}
    chat = await Chat.get(id=event.chat.id)
    if chat.filter_enable:
        chat.messages_checked += 1
        await chat.save()
        await get_words()
        if word_filter[chat.filter_mode].test(event.text):
            member = await ChatMember.get_or_none(chat_id=event.chat.id, user_id=event.sender.id)
            if not member or not member.is_admin:
                chat.bad_words_detected += 1
                await chat.save()
                message = await warn(event.chat.id, event.sender.id, get_mention(event.sender))
                await event.respond(message, buttons=Button.inline('Показать сообщение?', \
                                                                   'censored/'+event.text))
                await event.delete()

@bot.on(events.CallbackQuery(pattern=r'^censored/'))
async def show_bad_text(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки "Показать сообщение?"
    
    По нажатию кнопки проверяет является ли нажавший админом,
    если да - текст сообщения направляется нажавшему кнопку,
    кнопка удаляется. Если нажавший пользователь не является
    админом - выдается предупреждение об этом.
    '''
    sender = await ChatMember.get_or_none(chat_id=event.chat.id, user_id=event.sender_id)
    button_message = await event.get_message()
    if sender and sender.is_admin:
        text = event.data.decode('UTF-8').replace('censored/','', 1)
        try:
            await bot.send_message(event.sender_id, text)
        except PeerIdInvalidError as Ex:
            handlers_log.error(f'censored/: Произошла ошибка при отправке сообщения {event.sender.first_name}.')
            handlers_log.error(Ex)
            await event.answer('Я не могу писать пользователям первый, начни чат со мной и я смогу отправлять сообщения.', \
                               alert=True)
        else:
            await event.answer('Текст сообщения направлен в ЛС.')
            await button_message.edit(buttons=None)
    else:
        await event.answer('Только для админов!', alert=True)
        handlers_log.warning(f'Участник {event.sender.first_name} группы "{event.chat.title}" нажал кнопку показать.')

# Обработчики служебных команд и команд первоначальной настройки.
@bot.on(events.NewMessage(func=lambda e: e.text.lower() == '/reload' and e.is_group))
async def reload_command(event: Message):
    '''Обработка команды обновления списка админов.'''
    await reload_admins(event.chat.id)
    await event.respond('Список админов группы обновлен.')
    
@bot.on(events.NewMessage(func=lambda e: e.text.lower() == '/uplwords' and e.is_group))
async def upload_words(event: Message):
    '''Обработка команды загрузки списка ненормативных слов.
    
    Используется однократно после разворота бота на сервере, либо после
    обнуления базы. Далее работа ведется с базой.
    '''
    await upload_words_from_json()
    await event.respond('Список ненормативных слов загружен в базу.')
    handlers_log.info('Словарь загружен в базу.')

@admin_command('greet')
async def greet_command(event: Message):
    await event.respond('Привет, хозяин!')
    
@admin_command('listword')
async def show_list_word(event: Message):
    '''Обработчик комады вывода списка плохих слов.
    
    В текущей версии выводит в группу количество слов в базе и предлагает ввести
    начальные буквы в ответном сообщении. При получении отправляет в ЛС список слов,
    начинающихся с введенных букв или сообщает об отсутствии таких слов.
    to do: доработать процесс чтобы работа со словарем проводилась в настройках.
    '''
    word_list = await get_words()
    await event.respond(f'''В списке {len(word_list)} {agree_word('слово', len(word_list))}.''')
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
    '''Обработчик комады добавления плохого слова в список.
    
    В текущей версии предлагает в ответном сообщении ввести слово, которое необходимо
    добавить, при получении ответного сообщения нормализует слово и добавляет в базу.
    to do: доработать процесс чтобы работа со словарем проводилась в настройках.
    '''
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
    '''Обработчик комады удаления плохого слова из списка.
    
    В текущей версии предлагает в ответном сообщении ввести слово, которое необходимо
    удалить, при получении ответного сообщения пытается удалить слово из базы.
    to do: доработать процесс чтобы работа со словарем проводилась в настройках.
    '''
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
                
# Обработчики команд для админа (помощь и настройки).
@admin_command('help')
async def show_help(event: Message):
    '''Обработчик команды помощи.
    
    В текущей версии реагирует только на команды админа, посылая ему в ЛС
    сообщение со справкой.
    to do: доработать функцию выведя формирование сообщения в отдельный модуль,
    команду сделать для всех, сообщение формировать в зависимости от того,
    является ли пользователь админом.
    '''
    text = "Вы можете использовать следующие команды, отвечая на сообщения пользователя:\n \
    /mute и /unmute - запретить/разрешить пользователю писать;\n \
    /ban и /unban - забанить/разбанить пользователя;\n \
    /kick - исключить пльзователя из чата;\n \
    /warn и /unwarn - предупредить/снять предупреждение с пользователя.\n \
    \nСледующие команды не требуют цитирования:\n \
    /settings - настроить бота (управление настройками в ЛС)."
    try:
        await bot.send_message(event.sender_id, text)
    except Exception as Ex:
        handlers_log.error(f'/help: Произошла ошибка при отправке сообщения {event.sender.first_name}.')
        handlers_log.error(Ex)
    await event.respond('Список команд направлен Вам в ЛС.')

@admin_command('settings')
async def show_settings(event: Message):
    '''При получении команды /settings направляет в ЛС сообщение с настройками.'''
    chat_id = event.chat.id
    chat_title = event.chat.title
    chat = await Chat.get(id=chat_id)
    text, keyboard = templates.settings_message(chat_id, chat_title, chat)
    try:
        await bot.send_message(event.sender_id, text, buttons=keyboard)
    except UserIsBlockedError as Ex:
        handlers_log.error(f'/settings: Произошла ошибка при отправке сообщения {event.sender.first_name}.')
        handlers_log.error(Ex)
        await event.reply('Вы заблокировали/остановили бота. Для доступа к настройкам - разблокируйте/перезапустите.')
    else:
        await event.reply('Перейдите в ЛС для настройки бота.')

# Обработчки нажатий кнопок в меню настроек.
@bot.on(events.CallbackQuery(pattern=r'^close/'))
async def close_button(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки "Закрыть".
    
    Удаляет сообщение с данной кнопкой, если удаление невозможно -
    показывает всплывающее сообщение об этом.
    '''
    button_message = await event.get_message()
    try:
        await button_message.delete()
    except:
        await event.answer('\U00002757 Невозможно скрыть сообщение...')

@bot.on(events.CallbackQuery(pattern=r'^stat/'))
async def show_stat(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки "Статистика".
    
    По нажатию кнопки получается информация, переданная кнопкой,
    обновляется количество участников, если нажавший кнопку,
    сообщение с настройками трансформируется в сообщение со статистикой
    и кнопкой "Закрыть" и "Назад".
    '''
    comm, chat_id, chat_title = event.data.decode('UTF-8').split('/')
    chat = await Chat.get(id=chat_id)
    button_message = await event.get_message()
    users = await bot.get_participants(int(chat_id))
    chat.users = len(users)
    await chat.save()
    text, keyboard = templates.stat_message(chat_id, chat_title, chat)
    await button_message.edit(text=text, buttons=keyboard)
    
@bot.on(events.CallbackQuery(pattern=r'^back_to_set/'))
async def back_to_set(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки "Назад к настройкам".
    
    Заново подгружает и показывает сообщение с настройками вместо
    сообщения со статистикой.
    '''
    button_message = await event.get_message()
    comm, chat_id, chat_title = event.data.decode('UTF-8').split('/')
    chat = await Chat.get(id=chat_id)
    text, keyboard = templates.settings_message(chat_id, chat_title, chat)
    await button_message.edit(text=text, buttons=keyboard)
    
@bot.on(events.CallbackQuery(pattern=r'^warns_num_inc/'))
async def warn_num_inc(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки + в настройке количества предупреждений.
    
    Увеличивает количество предупреждений на 1 с каждым нажатием с записью
    в базу, но не более 5.
    '''
    button_message = await event.get_message()
    comm, chat_id, chat_title = event.data.decode('UTF-8').split('/')
    chat = await Chat.get(id=chat_id)
    if chat.warns_number == 5:
        await event.answer('Достигнуто максимальное количество предупреждений.')
    else:
        chat.warns_number += 1
        await chat.save()
        text, keyboard = templates.settings_message(chat_id, chat_title, chat)
        await button_message.edit(text=text, buttons=keyboard)

@bot.on(events.CallbackQuery(pattern=r'^warns_num_dec/'))
async def warn_num_dec(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки - в настройке количества предупреждений.
    
    Уменьшает количество предупреждений на 1 с каждым нажатием с записью
    в базу, но не менее 1.
    '''
    button_message = await event.get_message()
    comm, chat_id, chat_title = event.data.decode('UTF-8').split('/')
    chat = await Chat.get(id=chat_id)
    if chat.warns_number == 1:
        await event.answer('Достигнуто минимальное количество предупреждений.')
    else:
        chat.warns_number -= 1
        await chat.save()
        text, keyboard = templates.settings_message(chat_id, chat_title, chat)
        await button_message.edit(text=text, buttons=keyboard)

@bot.on(events.CallbackQuery(pattern=r'^mute_dur_inc/'))
async def mute_dur_inc(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки + в настройке продолжительности мьюта.
    
    Увеличивает продолжительность мьюта на 5 минут с каждым нажатием
    с записью в базу, но не более 60 минут.
    '''
    button_message = await event.get_message()
    comm, chat_id, chat_title = event.data.decode('UTF-8').split('/')
    chat = await Chat.get(id=chat_id)
    if chat.mute_duration == 60:
        await event.answer('Достигнута максимальная продолжительность мьюта.')
    else:
        chat.mute_duration += 5
        await chat.save()
        text, keyboard = templates.settings_message(chat_id, chat_title, chat)
        await button_message.edit(text=text, buttons=keyboard)

@bot.on(events.CallbackQuery(pattern=r'^mute_dur_dec/'))
async def mute_dur_dec(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки - в настройке продолжительности мьюта.
    
    Уменьшает продолжительность мьюта на 5 минут с каждым нажатием
    с записью в базу, но не менее 5 минут.
    '''
    button_message = await event.get_message()
    comm, chat_id, chat_title = event.data.decode('UTF-8').split('/')
    chat = await Chat.get(id=chat_id)
    if chat.mute_duration == 5:
        await event.answer('Достигнута минимальная продолжительность мьюта.')
    else:
        chat.mute_duration -= 5
        await chat.save()
        text, keyboard = templates.settings_message(chat_id, chat_title, chat)
        await button_message.edit(text=text, buttons=keyboard)

@bot.on(events.CallbackQuery(pattern=r'^penalty_mode/'))
async def penalty_mode_change(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки "Наказание за мат".
    
    Переключает виды наказания за мат по кругу mute - kick - ban.
    '''
    button_message = await event.get_message()
    comm, chat_id, chat_title = event.data.decode('UTF-8').split('/')
    chat = await Chat.get(id=chat_id)
    penalty_modes = {
        'mute': 'kick',
        'kick': 'ban',
        'ban': 'mute'
    }
    chat.penalty_mode = penalty_modes[chat.penalty_mode]
    await chat.save()
    text, keyboard = templates.settings_message(chat_id, chat_title, chat)
    await button_message.edit(text=text, buttons=keyboard)

@bot.on(events.CallbackQuery(pattern=r'^filter/'))
async def filter_mode_change(event: events.CallbackQuery.Event):
    '''Обработчик нажатия кнопки "Антимат".
    
    По нажатию кнопки переключает способ фильтрации мата Словарь - Шаблон - Выкл.
    '''
    button_message = await event.get_message()
    comm, chat_id, chat_title = event.data.decode('UTF-8').split('/')
    chat = await Chat.get(id=chat_id)
    if chat.filter_enable and chat.filter_mode == 'dict':
        chat.filter_mode = 'pattern'
        await chat.save()
    elif chat.filter_enable and chat.filter_mode == 'pattern':
        chat.filter_enable = False
        await chat.save()
        handlers_log.warning(f'Админ группы "{chat_title}" {event.sender.first_name} отключил матфильтр.')
    else:
        chat.filter_enable = True
        chat.filter_mode = 'dict'
        await chat.save()
    text, keyboard = templates.settings_message(chat_id, chat_title, chat)
    await button_message.edit(text=text, buttons=keyboard)

# Обработчики админских модерирующих команд в чате.
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
