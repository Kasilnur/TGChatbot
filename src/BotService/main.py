import telebot
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Бот запущен и видит токен!")


# Запуск бота
bot.infinity_polling(timeout=5)