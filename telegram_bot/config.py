import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str = os.getenv('BOT_TOKEN')
    api_token: str = os.getenv('NEURAL_API_TOKEN')
    host_post: str = os.getenv('API_URL_PROCESS')
    host_get: str = os.getenv('API_URL_CHECK')
    db_path: str = os.getenv('DB_PATH', './db.sqlite3')
    sentry_dsn: str = os.getenv('SENTRY_DSN', '')
    admin_chat_id: str = os.getenv('ADMIN_CHAT_ID', '')


bot_env = Config()
