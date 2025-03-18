import asyncio
from utils import config
from database.postgres import Database
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Начать работу с ботом"),
        BotCommand(command="/registration", description="Пройти регистрацию"),
        BotCommand(command="/edit", description="Подкорректируйте данные"),
        BotCommand(command="/profile", description="Ваши данные"),
    ]
    await bot.set_my_commands(commands)

async def main():
    # Infrastructure
    cfg = config.load()

    db = Database(cfg.postgres_db, cfg.postgres_user, cfg.postgres_password, cfg.postgres_host, cfg.postgres_port)

    # Bot
    telegram_bot = Bot(token=cfg.telegram_token)

    dispatcher = Dispatcher(storage=MemoryStorage())

    await set_commands(telegram_bot) 

    print("Бот запущен. Ожидаем сообщений...")

    await dispatcher.start_polling(telegram_bot)

    db.close()

if __name__ == "__main__":
    asyncio.run(main())