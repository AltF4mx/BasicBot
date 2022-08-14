import pymorphy2

from telethon.tl.custom import Button

morph = pymorphy2.MorphAnalyzer()

def agree_word(word: str, number: int):
    return morph.parse(word)[0].make_agree_with_number(number).word

def settings_message(chat_id: str, chat_title: str, chat):
    chat_id, chat_title, chat = chat_id, chat_title, chat
    text = f'Настройки для группы {chat_title}:'
    f_mods = {'dict': 'Словарь', 'pattern': 'Шаблон'}
    warns_number = chat.warns_number
    mute_duration = chat.mute_duration
    p_mods = {
        'mute': '\U0001F6A7 мьют',
        'kick': '\U0001F6AB кик',
        'ban': '\U0001F528 бан'
    }
    keyboard_off = [
        [
            Button.inline('\U0001F4CA  Показать статистику', f'stat/{chat_id}/{chat_title}')
        ],
        [
            Button.inline('\U00002757  Антимат: Off.', f'filter/{chat_id}/{chat_title}')
        ],
        [
            Button.inline('\U0000274C  Закрыть', 'close/')
        ]
    ]
    keyboard_on_not_mute = [
        [
            Button.inline('\U0001F4CA  Показать статистику', f'stat/{chat_id}/{chat_title}')
        ],
        [
            Button.inline(f'\U00002705 Антимат: {f_mods[chat.filter_mode]}.', \
                          f'filter/{chat_id}/{chat_title}')
        ],
        [
            Button.inline('\U00002795', f'warns_num_inc/{chat_id}/{chat_title}'),
            Button.inline(f'{warns_number} предупреждений', f'warns_num/{chat_id}/{chat_title}'),
            Button.inline('\U00002796', f'warns_num_dec/{chat_id}/{chat_title}')
        ],
        [
            Button.inline(f'Наказание за мат: {p_mods[chat.penalty_mode]}.', \
                          f'penalty_mode/{chat_id}/{chat_title}')
        ],
        [
            Button.inline('\U0000274C  Закрыть', 'close/')
        ]
    ]
    keyboard_full = [
        [
            Button.inline('\U0001F4CA  Показать статистику', f'stat/{chat_id}/{chat_title}')
        ],
        [
            Button.inline(f'\U00002705  Антимат: {f_mods[chat.filter_mode]}.', \
                          f'filter/{chat_id}/{chat_title}')
        ],
        [
            Button.inline('\U00002795', f'warns_num_inc/{chat_id}/{chat_title}'),
            Button.inline(f'{warns_number} предупреждений', f'warns_num/{chat_id}/{chat_title}'),
            Button.inline('\U00002796', f'warns_num_dec/{chat_id}/{chat_title}')
        ],
        [
            Button.inline(f'Наказание за мат: {p_mods[chat.penalty_mode]}.', \
                          f'penalty_mode/{chat_id}/{chat_title}')
        ],
        [
            Button.inline('\U00002795', f'mute_dur_inc/{chat_id}/{chat_title}'),
            Button.inline(f'Мьют - {mute_duration} минут', f'mute_dur/{chat_id}/{chat_title}'),
            Button.inline('\U00002796', f'mute_dur_dec/{chat_id}/{chat_title}')
        ],
        [
            Button.inline('\U0000274C  Закрыть', 'close/')
        ]
    ]
    if chat.filter_enable:
        if chat.penalty_mode == 'mute':
            keyboard = keyboard_full
        else:
            keyboard = keyboard_on_not_mute
    else:
        keyboard = keyboard_off
    return text, keyboard

def stat_message(chat_id: str, chat_title: str, chat):
    chat_id, chat_title, chat = chat_id, chat_title, chat
    joined = chat.joined.strftime('%d.%m.%Y')
    users = chat.users
    messages = chat.messages_checked
    bad_words = chat.bad_words_detected
    muted = chat.users_muted
    kicked = chat.users_kicked
    banned = chat.users_banned
    text = f'''
Статистика группы {chat_title}:
\U0001F4C6 Бот в этом чате с {joined} г.
\U0001F465 Сейчас в чате {users} {agree_word('пользователь', users)}.
С момента вступления:
\U0001F4E8 - проверено {messages} {agree_word('сообщение', messages)};
\U0001F51E  - выявлено {bad_words} {agree_word('плохое', bad_words)} {agree_word('слово', bad_words)};
\U0001F6A7  - зарегистрирвано {muted} {agree_word('случай', muted)} мьюта пользователю;
\U0001F6AB  - кикнуто {kicked} {agree_word('пользователь', kicked)};
\U0001F528 - забанено {banned} {agree_word('пользователь', banned)}.
'''
    keyboard = [
        Button.inline('\U0000274C  Закрыть', 'close/'),
        Button.inline('\U000023EA  Назад к настройкам', f'back_to_set/{chat_id}/{chat_title}')
    ]
    return text, keyboard
