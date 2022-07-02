import logging
from telethon import TelegramClient
import config

class Bot(TelegramClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.me = None # Здесь будет информация о боте
    
# Создаем бота, используя данные API
bot = Bot('bot', config.API_ID, config.API_HASH)

bot.parse_mode = 'HTML'
logging.basicConfig(level=logging.INFO)

import app.handlers

async def start():
    # Подключиться к серверу
    await bot.connect()
    
    # Войти через токен. Метод sign_in возвращает информацию о боте. Мы сразу сохраним её в bot.me
    bot.me = await bot.sign_in(bot_token=config.BOT_TOKEN)
    
    # Начать получать апдейты от Телеграма и запустить все хендлеры
    await bot.run_until_disconnected()
    
def run():
    bot.loop.run_until_complete(start())

