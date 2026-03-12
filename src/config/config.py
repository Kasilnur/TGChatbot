import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DEEPSEEK_TOKEN = os.getenv("DEEPSEEK_TOKEN")
    VOICE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'VoiceData')
    LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    VOICE_HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'voice_history')

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not found in .env")
        if not cls.DEEPSEEK_TOKEN:
            raise ValueError("DEEPSEEK_TOKEN not found in .env")
        os.makedirs(cls.VOICE_DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.VOICE_HISTORY_DIR, exist_ok=True)
