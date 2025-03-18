from aiogram import Bot, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

from repository.repository import Repository

class Registration(StatesGroup):
    name = State()
    email = State()
    phone = State()
    timezone = State()

class RegistrationHandlers:
    def __init__(self, router: Router, repository: Repository):
        self.router = router
        self.repository = repository
        self.router.message.register(self.start_registration, Command('registration'))
        self.router.message.register(self.add_name, Registration.name)

    async def start_registration(self, message: Message, state: FSMContext):
        user = self.repository.get_user_by_id(message.from_user.id)
        if user:
            await message.answer('Вы уже зарегистрированы.')
            return
        await state.set_state(Registration.name)
        await message.answer('Введите ваше имя:')
    
    async def add_name(message: Message, state: FSMContext):
        if not message.text.isalpha():
            await message.answer("Пожалуйста, введите имя буквами.")
            return
        if  len(message.text) > 20:
            await message.answer("Имя слишком длинное.")
            return

        await state.update_data(name=message.text)
        await state.set_state(Registration.age)
        await message.answer('Введите ваш возраст:')
    




# @registration_router.callback_query(Registration.timezone)
# async def add_timezone(callback: CallbackQuery, bot: Bot, scheduler: AsyncIOScheduler, state: FSMContext):
#     timezone = callback.data
#     await state.update_data(timezone=timezone)
#     await callback.message.answer(f"Часовой пояс установлен: {timezone}.")
#     await callback.message.edit_reply_markup(reply_markup=None)

#     data = await state.get_data()
#     await state.clear()

#     await repository.add_user(
#         user_id=callback.from_user.id,
#         name=data.get("name"),
#         age=int(data.get("age")),
#         gender=data.get("gender"),
#         height=int(data.get("height")),
#         weight=int(data.get("weight")),
#         timezone=data.get("timezone")
#     )

#     await callback.message.answer(f"Приятно познакомиться, {data.get('name')}!\nТеперь каждый день вечером вам будет предложено пройти анкетирование для отслеживание вашего состояния.\nКаждую неделю вы сможете смотреть отчет и получать мою рецензию!")
#     await callback.message.answer(
#         "Выберите, что вас интересует:",
#         reply_markup=recommendation_keyboard
#     )


#     scheduler.add_job(
#         daily_survey.send_daily_survey,
#         #trigger=DailyTrigger(hour=20, minute=0, second=0, timezone=ZoneInfo(timezone)),
#         'interval',
#         seconds=180,
#         args=[callback.from_user.id, bot, state],
#         max_instances=30
#     )

#     scheduler.add_job(
#         review.send_review_survey,
#         #trigger=IntervalTrigger(days=30)
#         'interval',
#         seconds=600,
#         args=[callback.from_user.id, bot, state],
#         max_instances=30
#     )