import os
from dotenv import load_dotenv
import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup
from utils import check_availability, authenticate_user, save_to_file, load_from_file
from threading import Thread
import schedule
import time
from datetime import datetime
import logging  # Подключаем логирование

logging.basicConfig(level=logging.INFO)  # Настраиваем уровень логирования

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
REPORT_TIME = None  # Переменная для хранения времени отчёта

# Точка входа
@bot.message_handler(commands=['start'])
def start(message):
    password_input = bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(password_input, handle_password)

def handle_password(message):
    """Обрабатываем ввод пароля."""
    if authenticate_user(message.text):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        search_button = KeyboardButton("Начать поиск")
        markup.add(search_button)
        bot.send_message(message.chat.id, "Авторизация успешна! Выберите команду.", reply_markup=markup)
    else:
        msg = bot.send_message(message.chat.id, "Неверный пароль. Попробуйте ещё раз:")
        bot.register_next_step_handler(msg, handle_password)

@bot.message_handler(func=lambda message: message.text == "Начать поиск")
def monitor_site(message):
    input_data = bot.send_message(message.chat.id, "Введите дату въезда (ДД.ММ.ГГГГ):")
    bot.register_next_step_handler(input_data, process_check_in_date)

def process_check_in_date(message):
    check_in_date = message.text.strip()
    try:
        # Проверка, что формат даты корректный
        datetime.strptime(check_in_date, "%d.%m.%Y")
        input_data = bot.send_message(
            message.chat.id,
            f"Введённая дата въезда: {check_in_date}\n\nВведите дату выезда (ДД.ММ.ГГГГ):"
        )
        bot.register_next_step_handler(input_data, lambda m: process_check_out_date(m, check_in_date))
    except ValueError:
        logging.error(f"Некорректный формат даты въезда '{check_in_date}' от пользователя {message.from_user.username}")
        msg = bot.send_message(message.chat.id, "Ошибка: введите дату в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(msg, process_check_in_date)

def process_check_out_date(message, check_in_date):
    check_out_date = message.text.strip()
    try:
        # Проверка формата даты выезда
        datetime.strptime(check_out_date, "%d.%m.%Y")
        input_data = bot.send_message(
            message.chat.id,
            f"Введённые даты:\nВъезд: {check_in_date}, Выезд: {check_out_date}\n\nВведите количество взрослых:"
        )
        bot.register_next_step_handler(input_data, lambda m: process_adults_count(m, check_in_date, check_out_date))
    except ValueError:
        logging.error(f"Некорректный формат даты выезда '{check_out_date}' от пользователя {message.from_user.username}")
        msg = bot.send_message(message.chat.id, "Ошибка: введите дату в формате ДД.ММ.ГГГГ.")
        bot.register_next_step_handler(msg, lambda m: process_check_out_date(m, check_in_date))

def process_adults_count(message, check_in_date, check_out_date):
    try:
        adults_count = int(message.text.strip())
        if adults_count < 0:
            raise ValueError("Количество взрослых не может быть отрицательным.")
        input_data = bot.send_message(
            message.chat.id,
            f"К-во взрослых: {adults_count}\n\nВведите количество детей:"
        )
        bot.register_next_step_handler(input_data, lambda m: process_children_count(m, check_in_date, check_out_date, adults_count))
    except ValueError as e:
        logging.error(f"Ошибка при вводе количества взрослых: {e.args[0]} ({message.text}) от пользователя {message.from_user.username}")
        msg = bot.send_message(message.chat.id, "Ошибка: введите целое неотрицательное число для взрослых.")
        bot.register_next_step_handler(msg, lambda m: process_adults_count(m, check_in_date, check_out_date))

def process_children_count(message, check_in_date, check_out_date, adults_count):
    try:
        children_count = int(message.text.strip())
        if children_count < 0:
            raise ValueError("Количество детей не может быть отрицательным.")
        
        # Сохраняем данные в JSON
        monitoring_data = load_from_file()
        monitoring_data[message.chat.id] = {
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults_count": adults_count,
            "children_count": children_count
        }
        save_to_file(monitoring_data)  # Сохраняем данные в файл
        
        # Начинаем мониторинг (вызываем check_availability)
        result = check_availability(check_in_date, check_out_date, adults_count, children_count)
        bot.send_message(message.chat.id, result)
        
    except ValueError as e:
        logging.error(f"Ошибка при вводе количества детей: {e.args[0]} ({message.text}) от пользователя {message.from_user.username}")
        msg = bot.send_message(message.chat.id, "Ошибка: введите целое неотрицательное число для детей.")
        bot.register_next_step_handler(msg, lambda m: process_children_count(m, check_in_date, check_out_date, adults_count))

# Команда для настройки времени отчёта
@bot.message_handler(commands=['set_report_time'])
def set_report_time(message):
    try:
        time_input = bot.send_message(message.chat.id, "Введите время отчёта (в формате ЧЧ:ММ):")
        bot.register_next_step_handler(time_input, process_report_time)
    except Exception as e:
        logging.error(f"Ошибка при попытке установить время отчёта: {e.args[0]}")
        bot.send_message(message.chat.id, "Ошибка: попробуйте ещё раз.")

def process_report_time(message):
    global REPORT_TIME
    try:
        report_time = message.text.strip()
        datetime.strptime(report_time, "%H:%M")  # Проверяем формат времени
        REPORT_TIME = report_time
        schedule.clear()  # Убираем предыдущие задания
        schedule.every().day.at(REPORT_TIME).do(send_daily_report)
        bot.send_message(message.chat.id, f"Ежедневный отчёт теперь будет отправляться в {REPORT_TIME}.")
    except ValueError:
        logging.error(f"Некорректный формат времени отчёта '{report_time}' от пользователя {message.from_user.username}")
        msg = bot.send_message(message.chat.id, "Ошибка: введите время в формате ЧЧ:ММ.")
        bot.register_next_step_handler(msg, process_report_time)

# Регулярная отправка отчёта
def send_daily_report():
    bot.send_message(ADMIN_CHAT_ID, "На данный момент номеров не найдено, продолжаю поиск.")

# Перезапуск мониторинга при запуске бота
def resume_monitoring():
    monitoring_data = load_from_file()
    if not monitoring_data:
        print("Нет данных для восстановления мониторинга.")
        return
    
    # Восстанавливаем мониторинг для всех пользователей с активными параметрами
    for chat_id, data in monitoring_data.items():
        bot.send_message(chat_id, "Бот перезапущен. Возобновляю мониторинг для заданных параметров.")
        result = check_availability(
            data["check_in_date"],
            data["check_out_date"],
            data["adults_count"],
            data["children_count"]
        )
        bot.send_message(chat_id, result)

if __name__ == "__main__":
    print("Starting the bot...")
    resume_monitoring()  # Начинаем мониторинг для активных пользователей
    bot.polling(non_stop=True)
