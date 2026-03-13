import os
import datetime
import shutil
import speech_recognition as sr
from pydub import AudioSegment
from src.config.config import Config
from src.utils.logger import log_message

class VoiceService:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def handle_voice(self, bot, message, ai_service):
        try:
            file_info = bot.get_file(message.voice.file_id)
            downloaded_voice = bot.download_file(file_info.file_path)

            user_id = message.from_user.id
            username = message.from_user.username or message.from_user.first_name
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Временные пути
            ogg_path = os.path.join(Config.VOICE_DATA_DIR, f'temp_{user_id}.ogg')
            wav_path = os.path.join(Config.VOICE_DATA_DIR, f'temp_{user_id}.wav')

            # Постоянный путь для хранения
            history_filename = f"{timestamp}_{user_id}.ogg"
            history_path = os.path.join(Config.VOICE_HISTORY_DIR, history_filename)

            with open(ogg_path, 'wb') as voice:
                voice.write(downloaded_voice)

            # Сохраняем копию в историю
            shutil.copy2(ogg_path, history_path)

            # Конвертация ogg в wav
            audio = AudioSegment.from_file(ogg_path)
            audio.export(wav_path, format="wav")

            # Распознавание речи
            with sr.AudioFile(wav_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language="ru-RU")
                
                bot.reply_to(message, f"Вы сказали: {text}\n\nПечатает... ✍️")
                
                ai_response = ai_service.get_response(user_id, text)
                
                # Логируем запрос и ответ
                log_message(user_id, username, "VOICE", text, ai_response)
                
                bot.send_message(message.chat.id, ai_response)
                
        except sr.UnknownValueError:
            bot.reply_to(message, "Я не смог разобрать, что вы сказали 😔")
        except sr.RequestError:
            bot.reply_to(message, "Сервис распознавания речи временно недоступен 🛠")
        except Exception as e:
            print(f"Voice handling error: {e}")
            bot.reply_to(message, "Произошла ошибка при обработке голосового сообщения.")
        finally:
            # Очистка
            if os.path.exists(ogg_path): os.remove(ogg_path)
            if os.path.exists(wav_path): os.remove(wav_path)
