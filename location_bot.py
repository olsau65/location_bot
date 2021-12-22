import psycopg2
import telebot
from telebot import types

token = '788192502:AAFPCbGrFZ_o5MY-HRk3QihjrF-THcraYKQ'

# Идентификаторы состояния пользователя
START, NAME, LOCATION, FOTO, CONFIRMATION, RADIUS, BUG = range(7)
# START - начал работу с ботом
# NAME - набрал название места
# LOCATION - отправил геолокацию
# FOTO - отправил фото
# CONFIRMATION - сохранение формы
# RADIUS - запросил точки в радиусе
# BUG - что-то пошло не так

# Тексты на кнопках
text_new = 'Сохранить новое место'
text_list = 'Точки в радиусе 500 метров'
text_all = 'Все сохраненные точки'
text_geo = 'Отправить геолокацию'
text_foto = 'Отправить фото'

# Переменная для хранения id последней точки
vp_id = []
vp_id.append(0)

bot = telebot.TeleBot(token)

# connect to the PostgreSQL server
con = psycopg2.connect(dbname='locbotdb', user='locbotuser', password='12345', host='localhost')
cur = con.cursor()

# Узнаем из базы данных «состояние» пользователя
def get_current_state(user_id):
    cur.execute('SELECT * FROM users WHERE tuser_id=%s;',(user_id,))
    if cur.rowcount == 0:
        return BUG
    else:
        res = cur.fetchone()[3]
        return res

# Меняем в базе данных «состояние» пользователя
def set_current_state(state, user_id):
    cur.execute('UPDATE users SET status = %s WHERE tuser_id=%s;',(state, user_id))
    con.commit()

# Обработчик команды '/start'
@bot.message_handler(commands=['start'])
def start_handler(message):
    cur.execute('SELECT * FROM users WHERE tuser_id=%s;',(message.chat.id,))
    if cur.rowcount == 0:
        cur.execute('INSERT INTO users(tuser_id, first_name, status) VALUES(%s, %s, %s);', (message.chat.id, message.chat.first_name, START))
        con.commit()

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)

    button_new = types.KeyboardButton(text=text_new)
    button_list = types.KeyboardButton(text=text_list)
    button_all = types.KeyboardButton(text=text_all)
    keyboard.add(button_new, button_list, button_all)
    bot.send_message(message.chat.id, "Привет! Сохрани интересное место или получи список уже сохраненных точек", reply_markup=keyboard)

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == NAME)
def user_entering_namepoints(message):

    cur.execute('INSERT INTO viewpoints(name_points, latitude, longitude, location, foto, user_id) VALUES(%s, %s, %s, ST_SetSRID(ST_MakePoint(0.0, 0.0), 4326), %s, %s) RETURNING id;', (message.text, 0.000000, 0.00000, None, message.chat.id))
    vp_id[0] = cur.fetchone()[0]

    con.commit()

    keyboard=types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Отличное место, запомню!", reply_markup=keyboard)

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_geo = types.KeyboardButton(text=text_geo, request_location=True)
    keyboard.add(button_geo)
    bot.send_message(message.chat.id, "Теперь отправь, пожалуйста, геолокацию", reply_markup=keyboard)

    set_current_state(LOCATION, message.chat.id)

@bot.message_handler(content_types=['location'], func=lambda message: get_current_state(message.chat.id) == LOCATION)
def location_handler(message):

    lati = message.location.latitude
    longi = message.location.longitude

    cur.execute('UPDATE viewpoints SET longitude = %s, latitude = %s, location = ST_SetSRID(ST_MakePoint(%s, %s), 4326) WHERE id=%s;', (longi, lati, longi, lati, vp_id[0]))
    con.commit()

    keyboard=types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Ура, у нас есть координаты!", reply_markup=keyboard)

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_foto = types.KeyboardButton(text=text_foto)
    keyboard.add(button_foto)
    bot.send_message(message.chat.id, "Теперь можешь отправить фото этого места", reply_markup=keyboard)

    set_current_state(FOTO, message.chat.id)

@bot.message_handler(content_types=['photo'], func=lambda message: get_current_state(message.chat.id) == FOTO)
def photo_handler(message):

    file_info = bot.get_file(message.photo[len(message.photo)-1].file_id)
    # downloaded_file = bot.download_file(file_info.file_path)

    cur.execute('UPDATE viewpoints SET foto = %s WHERE id=%s;', (file_info.file_id, vp_id[0]))
    con.commit()

    keyboard=types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Все получилось! Точка сохранена.", reply_markup=keyboard)

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)

    button_new = types.KeyboardButton(text=text_new)
    button_list = types.KeyboardButton(text=text_list)
    button_all = types.KeyboardButton(text=text_all)
    keyboard.add(button_new, button_list, button_all)
    bot.send_message(message.chat.id, "Продолжаем гулять! Сохрани интересное место или получи список уже сохраненных точек", reply_markup=keyboard)

    set_current_state(START, message.chat.id)

@bot.message_handler(content_types=['location'], func=lambda message: get_current_state(message.chat.id) == RADIUS)
def radius_handler(message):

    lati = message.location.latitude
    longi = message.location.longitude
    chat_id = message.chat.id

    cur.execute('SELECT name_points FROM viewpoints WHERE user_id = %s AND ST_DWithin(location, ST_SetSRID(ST_MakePoint(%s, %s), 4326), 0.005) LIMIT 10;', (chat_id, longi, lati))

    if cur.rowcount == 0:
        bot.send_message(chat_id, 'В радиусе 500 метров нет сохраненных точек.')
    else:
        bot.send_message(chat_id, 'Точки в радиусе 500 метров:')
        for row in cur:
            bot.send_message(chat_id, row[0])

    keyboard=types.ReplyKeyboardRemove()
    bot.send_message(chat_id, "С тобой интересно! Идем дальше?", reply_markup=keyboard)

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_new = types.KeyboardButton(text=text_new)
    button_list = types.KeyboardButton(text=text_list)
    button_all = types.KeyboardButton(text=text_all)
    keyboard.add(button_new, button_list, button_all)
    bot.send_message(chat_id, "Сохрани интересное место или получи список уже сохраненных точек", reply_markup=keyboard)

    set_current_state(START, chat_id)

# Обработчик команды '/reset'
@bot.message_handler(commands=['reset'])
def reset_handler(message):
    chat_id = message.chat.id
    cur.execute("DELETE FROM viewpoints WHERE user_id = %s;", (chat_id,))
    con.commit()
    bot.send_message(chat_id, 'С прошлым покончено! Начинаем с чистого листа.')

@bot.message_handler(content_types=['text'])
def text_handler(message):

    text = message.text
    chat_id = message.chat.id

    if text == text_new or text == '/add':
        keyboard=types.ReplyKeyboardRemove()
        bot.send_message(chat_id, 'Дай название этому месту, мой дорогой:', reply_markup=keyboard)

        set_current_state(NAME, message.chat.id)

    elif text == text_list or text == '/list':
        # В приведенном запросе мы ищем точки в радиусе около 500 метров.
        # Поскольку данные мы храним в типе geometry, здесь в ST_DWithin мы можем указать лимит на расстояние в градусах
        # Можно примерно перевести градусы в метры из рассчета, что в одном градусе 60 морских миль, а в одной морской миле 1852 метра.
        # Т.е. 1 градус = 60 миль * 1852 метра = 111 120 метров * 0,005 = 555,6 метра

        keyboard=types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Сейчас посмотрим", reply_markup=keyboard)

        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_geo = types.KeyboardButton(text=text_geo, request_location=True)
        keyboard.add(button_geo)
        bot.send_message(chat_id, "Отправь, пожалуйста, свою геолокацию", reply_markup=keyboard)

        set_current_state(RADIUS, chat_id)

    elif text == text_all:
        cur.execute('SELECT name_points, foto FROM viewpoints WHERE user_id = %s;', (chat_id,))
        if cur.rowcount == 0:
            bot.send_message(chat_id, 'Нет сохраненных точек.')
        else:
            bot.send_message(chat_id, 'Все сохраненные точки:')
            for row in cur:
                bot.send_message(chat_id, row[0])
                bot.send_photo(chat_id, row[1])

    elif text == text_foto:
        bot.send_message(chat_id, 'Нажми 📎 и выбери картинку или фото для отправки')

    else:
        bot.send_message(chat_id, 'Прости, я тебя не понял 🙏')
        bot.send_message(chat_id, 'Используй кнопки меню или список команд /')


if __name__ == '__main__':
     bot.polling(none_stop=True)

