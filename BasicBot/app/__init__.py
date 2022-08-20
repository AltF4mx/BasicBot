import logging
from telethon import TelegramClient
import config

from tortoise import Tortoise

class Bot(TelegramClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.me = None # Здесь будет информация о боте
    
# Создаем бота, используя данные API
bot = Bot('bot', config.API_ID, config.API_HASH)

bot.parse_mode = 'HTML'

# Настраиваем логгирование
log = logging.getLogger('TGDroidModer')
log.setLevel(logging.INFO)
file_handler = logging.FileHandler('basicbot.log')
console_out = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s | %(name)s] %(levelname)s: %(message)s', datefmt='%m.%d.%Y %H:%M:%S')
file_handler.setFormatter(formatter)
console_out.setFormatter(formatter)
log.addHandler(file_handler)
log.addHandler(console_out)

import app.handlers

TORTOISE_ORM = {
    'connections': {'default': config.DATABASE_URI},
    'apps': {
        'app': {
            'models': ['app.models', 'aerich.models'],
            'default_connection': 'default',
        },
    },
}

async def start():
    await Tortoise.init(config=TORTOISE_ORM)
    # Подключиться к серверу
    await bot.connect()
    
    # Войти через токен. Метод sign_in возвращает информацию о боте. Мы сразу сохраним её в bot.me
    bot.me = await bot.sign_in(bot_token=config.BOT_TOKEN)
    log.info(f'Авторизация успешна под именем {bot.me.first_name}.')
    
    # Начать получать апдейты от Телеграма и запустить все хендлеры
    await bot.run_until_disconnected()
    
    
def run():
    bot.loop.run_until_complete(start())    