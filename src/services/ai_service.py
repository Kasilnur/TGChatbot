from huggingface_hub import InferenceClient
from src.config.config import Config
import io

class AIService:
    def __init__(self):
        # Модель для текста
        self.client = InferenceClient(
            model="Qwen/Qwen2.5-72B-Instruct", 
            token=Config.DEEPSEEK_TOKEN
        )
        self.user_contexts = {}
        self.system_prompt = """Ты — умный друг. Твое имя - Иру. Ты весьма эмоциональный. Смайликов мало, интеллект высокий.
Выдавай ответ сразу без рассуждений и тегов. Без Markdown. Делай форматирование сообщения чистым текстом."""

    def get_response(self, user_id, user_text):
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = [{"role": "system", "content": self.system_prompt}]
        
        self.user_contexts[user_id].append({"role": "user", "content": user_text})
        
        if len(self.user_contexts[user_id]) > 11:
            self.user_contexts[user_id] = [self.user_contexts[user_id][0]] + self.user_contexts[user_id][-10:]

        try:
            completion = self.client.chat_completion(
                messages=self.user_contexts[user_id],
                max_tokens=500,
                stream=False,
            )
            
            response = ""
            if completion and completion.choices:
                response = completion.choices[0].message.content
            
            if not response:
                return "Извини, я получил пустой ответ от ИИ. Попробуй еще раз!"
                
            self.user_contexts[user_id].append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"AI API Error: {error_msg}")
            
            if "402" in error_msg:
                return "Модель DeepSeek временно стала платной в этом регионе. Я переключаюсь на альтернативу! 🔄 Попробуйте еще раз."
            elif "429" in error_msg:
                return "Ой, слишком много запросов! Дай мне отдохнуть минутку ☕️"
            elif "503" in error_msg or "Model is overloaded" in error_msg:
                return "Сервер ИИ сейчас перегружен. Давай попробуем через пару секунд! ⏳"
            
            return f"Ошибка ИИ: {error_msg[:50]}..."

    def analyze_sentiment(self, text):
        # Быстрый анализ тональности через ту же модель
        try:
            prompt = f"Проанализируй настроение этого сообщения и верни ТОЛЬКО один эмодзи, который лучше всего его описывает (например, 😊, 😔, 😠, 😮, 🤔). Сообщение: '{text}'"
            response = self.client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5
            )
            emoji = response.choices[0].message.content.strip()
            # Очищаем от лишнего текста, если он есть
            import re
            emojis = re.findall(r'[^\w\s,]', emoji)
            return emojis[0] if emojis else "🤔"
        except:
            return "🤔"

    def clear_context(self, user_id):
        self.user_contexts[user_id] = [{"role": "system", "content": self.system_prompt}]
