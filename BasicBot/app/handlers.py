from telethon import events

from app import bot

@bot.on(events.ChatAction())
async def on_join(event: events.ChatAction.Event):
    if event.is_group and event.user_added and event.user_id == bot.me.id:
        await bot.send_message(event.chat.id, 'Всем привет!')
        await bot.send_message(event.chat.id, 'Я ' + bot.me.first_name)
        await bot.send_message(event.chat.id, 'Я послежу тут за вами немного ;)')