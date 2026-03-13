from huggingface_hub import InferenceClient
from src.config.config import Config
import io

class AIService:
    def __init__(self):
        # Переключаемся на Qwen2.5-72B-Instruct — это сейчас самая стабильная 
        # и качественная БЕСПЛАТНАЯ модель на Hugging Face. 
        # DeepSeek часто выдает 402 ошибку из-за перегрузки серверов.
        self.client = InferenceClient(
            model="Qwen/Qwen2.5-72B-Instruct", 
            token=Config.DEEPSEEK_TOKEN
        )
        self.user_contexts = {}
        self.system_prompt = (
            "Ты — Иру, дружелюбный и невероятно умный ИИ-помощник. Читай контекст перед ответом, чтобы ты не отвечал как рыбка."
            "Твоя задача — быть максимально полезным, общаться естественно и человечно. "
            "На простые запросы (привет, как дела) отвечай кратко и дружелюбно,. "
            "На сложные вопросы давай структурированные и точные ответы. "
            "Используй русский язык. Избегай технических терминов про модели ИИ в диалоге. "
            "Выдавай ответ сразу без рассуждений и тегов. Без Markdown. "
            "Делай форматирование сообщения чистым текстом."
        )

    def get_response(self, user_id, user_text):
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = [{"role": "system", "content": self.system_prompt}]
        
        # Добавляем сообщение пользователя в контекст
        self.user_contexts[user_id].append({"role": "user", "content": user_text})
        
        # Ограничиваем размер контекста (системный промпт + 14 последних сообщений)
        # Увеличим до 15 элементов (1 системный + 14 сообщений диалога), чтобы память была длиннее
        if len(self.user_contexts[user_id]) > 15:
            self.user_contexts[user_id] = [self.user_contexts[user_id][0]] + self.user_contexts[user_id][-14:]

        try:
            # Логируем контекст для отладки
            print(f"--- Context for user {user_id} (Length: {len(self.user_contexts[user_id])}) ---")
            for msg in self.user_contexts[user_id]:
                role_icon = "👤" if msg['role'] == "user" else "🤖" if msg['role'] == "assistant" else "⚙️"
                print(f"{role_icon} {msg['role']}: {msg['content'][:60]}...")
            print("--------------------------------")

            completion = self.client.chat_completion(
                messages=self.user_contexts[user_id],
                max_tokens=800, # Увеличим лимит для более развернутых ответов
                stream=False,
            )
            
            response = ""
            if completion and completion.choices:
                response = completion.choices[0].message.content
            
            if not response:
                # Вместо ошибки возвращаем человечный ответ и не ломаем контекст
                return "Хм, кажется, я немного отвлеклась... Можешь повторить еще раз? 😊"
            
            # Добавляем ответ ассистента в контекст
            self.user_contexts[user_id].append({"role": "assistant", "content": response})
            
            return response
        except Exception as e:
            error_msg = str(e)
            print(f"CRITICAL AI ERROR: {error_msg}")
            
            # Если ошибка произошла, удаляем последнее сообщение пользователя, 
            # чтобы при повторе контекст оставался логичным
            if user_id in self.user_contexts and self.user_contexts[user_id][-1]["role"] == "user":
                self.user_contexts[user_id].pop()
            
            # Универсальный человечный ответ при ЛЮБОЙ ошибке. 
            # Никаких упоминаний DeepSeek или технических деталей.
            return "Ой, что-то я немного задумалась... 🤔 Напиши мне еще раз, пожалуйста, я обязательно отвечу!"

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
