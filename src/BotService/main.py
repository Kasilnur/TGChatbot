import telebot
from telebot import types
import os
from dotenv import load_dotenv
import speech_recognition as sr
from pydub import AudioSegment
from huggingface_hub import InferenceClient

# Инициализация путей для папок
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_DIR = os.path.join(BASE_DIR, '..', 'TempAudio')
if not os.path.exists(VOICE_DIR):
    os.makedirs(VOICE_DIR)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

user_sessions = {}


def get_full_commands():
    return [
        types.BotCommand("/start", "Запустить бота"),
        types.BotCommand("/help", "Показать справку"),
        types.BotCommand("/exit", "Завершить работу")
    ]


def get_start_only():
    return [
        types.BotCommand("/start", "Запустить бота")
    ]


# Инициализация клиента
client = InferenceClient(token=os.getenv("DEEPSEEK_TOKEN"))


def get_ai_response(prompt):
    completion = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1:novita",
        messages=[
            {
                "role": "system",
                "content": """Ты — лаконичный помощник в чате telegram.
                 Сразу подавай общение на уровне хороших друзей.
                 Выдавай ответ сразу без рассуждений и тегов.
                 Не дублируй ответ.
                 В ответе не пытайся использовать Markdown.""" # Добавить под API
            },
                {
                "role": "user",
                "content": prompt
            }
        ],
    )
    print(f"""
    LOGGER
    Ответ LLM: {completion.choices[0].message.content}
    """)
    return completion.choices[0].message.content

# Слушатели
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id

    bot.set_my_commands(
        get_full_commands(),
        scope=types.BotCommandScopeChat(chat_id)
    )
    user_sessions[message.from_user.id] = True
    bot.reply_to(
        message, "Приветствую, Я Иру! В любой момент ты можешь написать мне. Благодаря, мне  Помогу чем смогу!")

    bot.set_message_reaction(message.chat.id, message.message_id, [
                             telebot.types.ReactionTypeEmoji('🤝')])


@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        """
<b>Команды бота:</b>

/start - Запустить бота
/help - Показать справку о командах
/exit - Завершить сессию

Просто напиши мне что-нибудь, и я отвечу!
        """
    )
    # parse_mode='HTML' для html команд
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')


@bot.message_handler(commands=['exit'])
def exit_command(message):
    chat_id = message.chat.id

    if user_sessions.get(message.from_user.id) is False:
        bot.send_message(
            message.chat.id, "Я тебя впервые вижу, напиши /start, познакомимся 🙂")
        return

    user_sessions[message.from_user.id] = False
    bot.set_my_commands(
        get_start_only(),
        scope=types.BotCommandScopeChat(chat_id)
    )
    bot.send_message(
        message.chat.id, "До связи! Если я снова понадоблюсь, напиши /start")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    if user_sessions.get(message.from_user.id) is False:
        bot.send_message(
            message.chat.id, "Я тебя впервые вижу. Напиши /start, познакомимся 🙂")
        return
    if message.text == "Справка":
        help_command(message)
    elif message.text == "Выход":
        exit_command(message)
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.send_message(message.chat.id, get_ai_response(message.text))


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("👀")])
    try:
        # Скачивание голосового сообщения
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        ogg_filename = os.path.join(VOICE_DIR, f"{message.from_user.id}.ogg")
        wav_filename = os.path.join(VOICE_DIR, f"{message.from_user.id}.wav")

        # Сохранение скачанного файла в формат ogg
        with open(ogg_filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Конвертация OGG в WAV
        audio = AudioSegment.from_file(ogg_filename)
        audio.export(wav_filename, format="wav")

        # Распознавание текста
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_filename) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            bot.send_chat_action(message.chat.id, 'typing')
            bot.send_message(message.chat.id, get_ai_response(text))

            print(f"""LOGGER\nТекст голосового сообщения от пользователя {message.from_user.id}: {text}""")

    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(message, "Я не совсем понял, что вы сказали")

    finally:
        if os.path.exists(ogg_filename):
            os.remove(ogg_filename)
        if os.path.exists(wav_filename):
            os.remove(wav_filename)


bot.set_my_commands([
    types.BotCommand("/start", "Запустить бота"),
    types.BotCommand("/help", "Показать справку"),
    types.BotCommand("/exit", "Завершить работу")
])


if __name__ == "__main__":
    # Запуск бота
    print("Бот запущен")
    bot.infinity_polling(none_stop=True, interval=0, logger_level=0, skip_pending=True)
