import pymorphy2

from telethon.tl.custom import Button

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
    morph = pymorphy2.MorphAnalyzer()
    joined = chat.joined.strftime('%d.%m.%Y')
    users = chat.users
    users_word = morph.parse('пользователь')[0].make_agree_with_number(users).word
    messages = chat.messages_checked
    mess_word = morph.parse('сообщение')[0].make_agree_with_number(messages).word
    bad_words = chat.bad_words_detected
    words_word = morph.parse('слово')[0].make_agree_with_number(bad_words).word
    muted = chat.users_muted
    mute_word = morph.parse('случай')[0].make_agree_with_number(muted).word
    kicked = chat.users_kicked
    kick_word = morph.parse('пользователь')[0].make_agree_with_number(kicked).word
    banned = chat.users_banned
    ban_word = morph.parse('пользователь')[0].make_agree_with_number(banned).word
    text = f'''
Статистика группы {chat_title}:
\U0001F4C6 Бот в этом чате с {joined} г.
\U0001F465 Сейчас в чате {users} {users_word}.
С момента вступления:
\U0001F4E8 - проверено {messages} {mess_word};
\U0001F51E  - выявлено {bad_words} плохих слов;
\U0001F6A7  - зарегистрирвано {muted} {mute_word} мьюта пользователю;
\U0001F6AB  - кикнуто {kicked} {kick_word};
\U0001F528 - забанено {banned} {ban_word}.
'''
    keyboard = [
        Button.inline('\U0000274C  Закрыть', 'close/'),
        Button.inline('\U000023EA  Назад к настройкам', f'back_to_set/{chat_id}/{chat_title}')
    ]
    return text, keyboard
