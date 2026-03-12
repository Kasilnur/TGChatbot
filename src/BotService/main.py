import telebot
from telebot import types
import os
import threading
from datetime import datetime
from dotenv import load_dotenv
import speech_recognition as sr
from pydub import AudioSegment
from huggingface_hub import InferenceClient
import time
import threading

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

user_contexts = {}
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


def keep_typing(chat_id, stop_event):
    while not stop_event.is_set():
        try:
            bot.send_chat_action(chat_id, 'typing')
            time.sleep(4)
        except Exception:
            break

# Инициализация клиента
client = InferenceClient(token=os.getenv("DEEPSEEK_TOKEN"))


def get_ai_response(user_id, prompt):
    today = datetime.now().strftime("%Y-%m-%d")

    if user_id not in user_contexts:
        user_contexts[user_id] = {"summaries": [], "current_day": today, "daily_logs": []}

    # Логика смены дня
    if user_contexts[user_id]["current_day"] != today:
        prev_day = user_contexts[user_id]["current_day"]
        logs = " ".join(user_contexts[user_id]["daily_logs"])
        if logs:
            user_contexts[user_id]["summaries"].append({"date": prev_day, "context": logs})
        user_contexts[user_id]["daily_logs"] = []
        user_contexts[user_id]["current_day"] = today

    recent_logs = "\n".join(user_contexts[user_id]["daily_logs"][-30:])
    history_short = str(user_contexts[user_id]["summaries"][-3:])

    system_prompt = f"""Ты — умный друг. Твое имя - Иру. Ты весьма эмоциональный. Смайликов мало, интеллект высокий.
    Выдавай ответ сразу без рассуждений и тегов. Без Markdown. Делай форматирование сообщения чистым текстом.
    Твоя память о прошлом: {history_short}
    Контекст текущего дня: {recent_logs}"""

    completion = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1:novita",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800
    )
    
    response = completion.choices[0].message.content

    print(f"LOGGER | User: {user_id} | Context: {prompt[:100]}")

    user_contexts[user_id]["daily_logs"].append(f"U: {prompt}")
    user_contexts[user_id]["daily_logs"].append(f"AI: {response}")

    # ФОНОВАЯ СУММАРИЗАЦИЯ
    # Если за день накопилось больше 12 записей - сжатие их в фоне
    if len(user_contexts[user_id]["daily_logs"]) > 12:
        threading.Thread(target=summarize_context, args=(user_id,)).start()

    return response


def summarize_context(user_id):
    if user_id not in user_contexts or not user_contexts[user_id]["daily_logs"]:
        return

    logs_to_summarize = "\n".join(user_contexts[user_id]["daily_logs"])
    
    try:
        summary_completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            messages=[
                {"role": "system", "content": "Ты — архиватор. Сожми переписку в ОДНО емкое предложение, сохранив важные факты."},
                {"role": "user", "content": logs_to_summarize}
            ],
            max_tokens=200
        )
        summary = summary_completion.choices[0].message.content
        user_contexts[user_id]["daily_logs"] = [f"Краткая предыстория дня: {summary}"]
        print(f"LOGGER | Контекст пользователя {user_id} успешно сжат.")
    except Exception as e:
        print(f"LOGGER | Ошибка суммаризации: {e}")

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
        message, "Приветствую, Я Иру! В любой момент ты можешь написать мне. Помогу чем смогу!")

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
        stop_typing = threading.Event()
        typing_thread = threading.Thread(target=keep_typing, args=(message.chat.id, stop_typing))
        typing_thread.start()
        answer = get_ai_response(message.from_user.id, message.text)
        stop_typing.set()
        typing_thread.join()
        bot.send_message(message.chat.id, answer)


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
            stop_typing = threading.Event()
            typing_thread = threading.Thread(target=keep_typing, args=(message.chat.id, stop_typing))
            typing_thread.start()
            answer = get_ai_response(message.from_user.id, text)
            stop_typing.set()
            typing_thread.join()
            bot.send_message(message.chat.id, answer)

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
