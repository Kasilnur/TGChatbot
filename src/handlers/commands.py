import telebot
from telebot import types

class CommandHandler:
    def __init__(self, bot, ai_service, user_sessions):
        self.bot = bot
        self.ai_service = ai_service
        self.user_sessions = user_sessions

    def get_full_commands(self):
        return [
            types.BotCommand("/start", "Запустить бота"),
            types.BotCommand("/help", "Показать справку"),
            types.BotCommand("/clear", "Очистить память"),
            types.BotCommand("/exit", "Завершить работу")
        ]

    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(message):
            chat_id = message.chat.id
            user_id = message.from_user.id
            self.bot.set_my_commands(
                self.get_full_commands(),
                scope=types.BotCommandScopeChat(chat_id)
            )
            self.user_sessions[user_id] = True
            self.ai_service.clear_context(user_id)
            
            welcome_text = (
                f"Привет, {message.from_user.first_name}! 👋\n\n"
                "Я — **Иру**, твой персональный ИИ-ассистент. "
                "Я работаю на базе мощной языковой модели и готов помочь тебе с любыми задачами: "
                "от простого общения до решения сложных вопросов. 🧠\n\n"
                "**Что я умею:**\n"
                "💬 Вести диалог и помнить контекст\n"
                "🎙️ Понимать голосовые сообщения\n"
                "🎭 Распознавать твоё настроение\n\n"
                "Просто напиши мне что-нибудь или отправь «голос»! 🚀"
            )
            
            self.bot.reply_to(message, welcome_text, parse_mode='Markdown')
            try:
                self.bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji('🤝')])
            except:
                pass

        @self.bot.message_handler(commands=['clear'])
        def clear_context(message):
            user_id = message.from_user.id
            self.ai_service.clear_context(user_id)
            self.bot.send_message(message.chat.id, "Память очищена! Начинаем с чистого листа. ✨")

        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            help_text = (
                "<b>Команды бота:</b>\n\n"
                "/start - Запустить бота\n"
                "/help - Показать справку\n"
                "/clear - Очистить контекст\n"
                "/exit - Завершить сессию"
            )
            self.bot.send_message(message.chat.id, help_text, parse_mode='HTML')

        @self.bot.message_handler(commands=['exit'])
        def exit_command(message):
            chat_id = message.chat.id
            user_id = message.from_user.id
            if self.user_sessions.get(user_id) is False:
                self.bot.send_message(message.chat.id, "Я тебя впервые вижу, напиши /start, познакомимся 🙂")
                return
            
            self.user_sessions[user_id] = False
            self.bot.send_message(message.chat.id, "До связи! Если я снова понадоблюсь, напиши /start")
