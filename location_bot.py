import telebot
token = 'xxxxxxxxxxxxxxxxxxxxxxxx'

bot = telebot.TeleBot(token)

@bot.message_handler(commands=['start', 'go'])
def handle_message(message):
    print(message.text)
    bot.send_message(chat_id=message.chat.id, text='Ты на верном пути')

@bot.message_handler(content_types=['text'])
def text_handler(message):
    text = message.text.lower()
    chat_id = message.chat.id
    if text == "привет":
        bot.send_message(chat_id, 'Привет, я бот - парсер хабра.')
    elif text == "как дела?":
        bot.send_message(chat_id, 'Хорошо, а у тебя?')
    else:
        bot.send_message(chat_id, 'Простите, я вас не понял :(')

bot.polling()

