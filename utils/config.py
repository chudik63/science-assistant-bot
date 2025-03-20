import os
from dotenv import load_dotenv

class Config:
    def __init__(self, env):
        self.postgres_password = env.get('POSTGRES_PASSWORD', None)
        self.postgres_user = env.get('POSTGRES_USER', None)
        self.postgres_db = env.get('POSTGRES_DB', None)
        self.postgres_port = env.get('POSTGRES_PORT', None)
        self.postgres_host = env.get('POSTGRES_HOST', None)
        self.telegram_token = env.get('TELEGRAM_TOKEN', None)
        self.huggin_token = env.get('HUGGIN_TOKEN', None)

def load():
    load_dotenv()

    env = {
        'POSTGRES_PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'POSTGRES_USER': os.getenv('POSTGRES_USER'),
        'POSTGRES_DB': os.getenv('POSTGRES_DB'),
        'POSTGRES_PORT': os.getenv('POSTGRES_PORT'),
        'POSTGRES_HOST': os.getenv('POSTGRES_HOST'),
        'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN'),
        'HUGGIN_TOKEN': os.getenv('HUGGIN_TOKEN')
    }

    return Config(env)