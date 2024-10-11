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


bot_env = Config()
