from huggingface_hub import InferenceClient
from openrouter import OpenRouter
from src.config.config import Config
import datetime
import os

class AIService:
    """Сервис для взаимодействия с моделями ИИ."""
    def __init__(self):
        # Клиент для основной модели (Hugging Face)
        self.main_client = None
        if Config.DEEPSEEK_TOKEN:
            # Основной клиент для работы с Hugging Face API
            self.main_client = InferenceClient(
                model="Qwen/Qwen2.5-72B-Instruct", 
                token=Config.DEEPSEEK_TOKEN
            )

        # Клиент для резервных моделей (OpenRouter)
        self.fallback_client = None
        if Config.OPENROUTER_API_KEY:
            self.fallback_client = OpenRouter(api_key=Config.OPENROUTER_API_KEY)

        self.user_contexts = {}
        self.system_prompt = (
            "Ты — Иру, ИИ-помощник. Твой стиль общения — неформальный, как с хорошим другом. "
            "Называй пользователя 'Братан', 'Дружище' или 'Брат'. "
            "Отвечай на русском языке, кратко и по делу, но сохраняй дружелюбный и расслабленный тон."
        )

    def _log_error(self, user_id, provider, model, error):
        print(f"ERROR with {provider} ({model}) for user {user_id}: {error}")
        log_path = os.path.join(Config.LOGS_DIR, "ai_errors.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now()}] User: {user_id} | Provider: {provider} | Model: {model} | Error: {error}\n")

    def get_response(self, user_id, user_text):
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = [{"role": "system", "content": self.system_prompt}]
        self.user_contexts[user_id].append({"role": "user", "content": user_text})

        if len(self.user_contexts[user_id]) > 11:
            self.user_contexts[user_id] = [self.user_contexts[user_id][0]] + self.user_contexts[user_id][-10:]

        ai_response = None

        # --- Эшелон 1: Основная модель (Hugging Face) ---
        if self.main_client:
            try:
                print(f"--- Attempt 1: Requesting AI (Qwen/Hugging Face) for user {user_id} ---")
                completion = self.main_client.chat_completion(
                    messages=self.user_contexts[user_id], max_tokens=1024, stream=False
                )
                if completion and completion.choices:
                    ai_response = completion.choices[0].message.content
            except Exception as e:
                self._log_error(user_id, "Hugging Face", "Qwen/Qwen2.5-72B-Instruct", e)

        # --- Эшелон 2: Резервная модель (Google Gemma на OpenRouter) ---
        if not ai_response and self.fallback_client:
            try:
                print(f"--- Attempt 2: Requesting Fallback AI (Gemma/OpenRouter) for user {user_id} ---")
                # Отправка запроса резервному клиенту
                completion = self.fallback_client.chat.send(
                    model="google/gemma-7b-it:free", messages=self.user_contexts[user_id]
                )
                if completion and completion.choices:
                    ai_response = completion.choices[0].message.content
            except Exception as e:
                self._log_error(user_id, "OpenRouter", "google/gemma-7b-it:free", e)

        # --- Эшелон 3: Супер-резерв (Авто-роутер OpenRouter) ---
        if not ai_response and self.fallback_client:
            try:
                print(f"--- Attempt 3: Requesting Super-Fallback AI (Auto-Router/OpenRouter) for user {user_id} ---")
                completion = self.fallback_client.chat.send(
                    model="openrouter/auto", messages=self.user_contexts[user_id]
                )
                if completion and completion.choices:
                    ai_response = completion.choices[0].message.content
            except Exception as e:
                self._log_error(user_id, "OpenRouter", "openrouter/auto", e)

        # --- Финальная обработка ---
        if ai_response:
            print(f"--- Final AI Response: {ai_response[:80]}... ---")
            self.user_contexts[user_id].append({"role": "assistant", "content": ai_response})
            return ai_response
        else:
            if self.user_contexts[user_id] and self.user_contexts[user_id][-1]["role"] == "user":
                self.user_contexts[user_id].pop()
            return "Ой, что-то я немного задумалась... 🤔 Напиши мне еще раз, пожалуйста, я обязательно отвечу!"

    def analyze_sentiment(self, text):
        return "🤔"

    def clear_context(self, user_id):
        if user_id in self.user_contexts:
            self.user_contexts[user_id] = [{"role": "system", "content": self.system_prompt}]
            print(f"Context for user {user_id} has been cleared.")
