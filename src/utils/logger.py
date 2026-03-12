import os
import datetime
from src.config.config import Config

def log_message(user_id, username, message_type, content, response=None):
    log_file = os.path.join(Config.LOGS_DIR, "chat_history.log")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = (
        f"[{timestamp}] User: {username} ({user_id}) | Type: {message_type}\n"
        f"Input: {content}\n"
    )
    if response:
        log_entry += f"Response: {response}\n"
    log_entry += "-" * 50 + "\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)
