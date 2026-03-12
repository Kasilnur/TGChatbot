import telebot
from src.config.config import Config
from src.services.ai_service import AIService
from src.services.voice_service import VoiceService
from src.handlers.commands import CommandHandler
from src.utils.logger import log_message

# Валидация конфига
Config.validate()

# Инициализация бота и сервисов
bot = telebot.TeleBot(Config.BOT_TOKEN)
ai_service = AIService()
voice_service = VoiceService()
user_sessions = {}

# Инициализация команд
command_handler = CommandHandler(bot, ai_service, user_sessions)
command_handler.register_handlers()

# Регистрация обработчиков текста и голоса
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    if user_sessions.get(user_id) is False:
        bot.send_message(message.chat.id, "Я тебя впервые вижу. Напиши /start, познакомимся 🙂")
        return
    
    if message.text == "Справка":
        bot.send_message(message.chat.id, "Команды в меню!")
    elif message.text == "Выход":
        bot.send_message(message.chat.id, "Выход в меню!")
    else:
        # Анализируем тональность для подбора эмодзи
        mood_emoji = ai_service.analyze_sentiment(message.text)
        
        # Добавляем реакцию на основе настроения
        try:
            bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji(mood_emoji)])
        except:
            pass
            
        # Показываем статус 'печатает'
        bot.send_chat_action(message.chat.id, 'typing')
        
        thinking_msg = bot.send_message(message.chat.id, "Печатает... ✍️")
        ai_response = ai_service.get_response(user_id, message.text)
        
        # Логируем текст
        username = message.from_user.username or message.from_user.first_name
        log_message(user_id, username, "TEXT", message.text, ai_response)
        
        bot.edit_message_text(ai_response, message.chat.id, thinking_msg.message_id)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    if user_sessions.get(user_id) is False:
        bot.send_message(message.chat.id, "Я тебя впервые вижу. Напиши /start, познакомимся 🙂")
        return
    
    # Добавляем реакцию 'глаза' на голосовое сообщение
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji('👀')])
    except:
        pass
        
    # Показываем статус 'записывает голос' или 'печатает'
    bot.send_chat_action(message.chat.id, 'typing')
    
    voice_service.handle_voice(bot, message, ai_service)

if __name__ == "__main__":
    print("Бот Иру запущен!")
    bot.infinity_polling(timeout=5)
