import asyncio
from utils import config
from database import Database
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agent import Agent
from handlers import ProfileHandlers, SettingsHandlers, AgentHandlers
from repository.repository import Repository
from pytz import timezone
from handlers.apsheduler.apsheduler_db import check_and_send_updates
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Начать работу с ботом"),
        BotCommand(command="/registration", description="Пройти регистрацию"),
        BotCommand(command="/profile", description="Ваши данные"),
        BotCommand(command="/settings", description="Настройки поиска"),
        BotCommand(command="edit_settings", description="Изменение настроек поиска"),
    ]
    await bot.set_my_commands(commands)

async def main():
    # Infrastructure
    cfg = config.load()
    scheduler = AsyncIOScheduler(timezone=timezone('Europe/Moscow'))
    scheduler.add_job(check_and_send_updates, "interval", minutes=10)
    db = Database(cfg.postgres_db, cfg.postgres_user, cfg.postgres_password, cfg.postgres_host, cfg.postgres_port)

    # Agent
    agent = Agent(cfg.huggin_token)

    # Repository & handlers
    repository = Repository(db)

    router = Router()
    ProfileHandlers(router, repository)
    SettingsHandlers(router, repository)
    AgentHandlers(router, agent)

    # Bot
    telegram_bot = Bot(token=cfg.telegram_token)

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)

    await set_commands(telegram_bot) 

    print("Бот запущен. Ожидаем сообщений...")

    await dispatcher.start_polling(telegram_bot)

    db.close()

if __name__ == "__main__":
    asyncio.run(main())