import telebot, wikipedia, re

# Создаем экземпляр бота
bbot = telebot.TeleBot('5373925548:AAHZ09ubZMRTfsXqlE0a7k_ffwnaQjvhLTY')

# Устанавливаем русский язык в Wikipedia
wikipedia.set_lang("ru")

# Чистим текст статьи в Wikipedia и ограничиваем его тысячей символов
def getwiki(s):
	try:
		ny = wikipedia.page(s)
		# Получаем первую тысячу символов
		wikitext = ny.content[:1000]
		# Разделяем по точкам
		wikimas = wikitext.split('.')
		# Отбрасываем все после последней точки
		wikimas = wikimas[:-1]
		# Создаем пустую переменную  для текста
		wikitext2 = ''
		# Проходимся по строкам, где нет знака "равно" (то есть все, кроме заголовков)
		for x in wikimas:
			if not ('==' in x):
				# Если в строке осталось больше трех символов, добавляем ее к нашей переменной
				# и возвращаем утерянные при разделении строк точки на место
				if (len((x.strip())) > 3):
					wikitext2 = wikitext2 + x + '.'
			else:
				break
		# Теперь при помощи регулярных выражений убираем разметку
		wikitext2 = re.sub('\([^()]*\)', '', wikitext2)
		wikitext2 = re.sub('\([^()]*\)', '', wikitext2)
		wikitext2 = re.sub('\{[^\{\}]*\}', '', wikitext2)
		# Возвращаем текстовую строку
		return wikitext2
	# Обрабатываем исключение, которое мог вернуть модуль wikipedia при запросе
	except Exception as e:
		print('Ашипкааа!!!!11рас')
		return 'Что-то пошло не так((('
# Функция, обрабатывающая команду /start
@bbot.message_handler(commands=["start"])
def start(m, res=False):
	bbot.send_message(m.chat.id, 'Напиши мне слово и я тебя удивлю... Но это не точно))')
	print('Bbot get started...')

# Получение сообщений от юзера
@bbot.message_handler(content_types=["text"])
def handle_text(message):
	bbot.send_message(message.chat.id, getwiki(message.text))
	print('Бот Что-то написал.')

bbot.polling(none_stop=True, interval=0)