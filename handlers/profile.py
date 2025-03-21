from aiogram import Bot, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

from repository.repository import Repository
from utils.email import valid
from models.Classes_for_db import User

timezones = [
    "Europe/Moscow", "Europe/Samara", "Asia/Yekaterinburg", "Asia/Novosibirsk",
    "Asia/Krasnoyarsk", "Asia/Irkutsk", "Asia/Vladivostok", "Asia/Kamchatka"
]

class Registration(StatesGroup):
    name = State()
    email = State()
    timezone = State()

class Edit(StatesGroup):
    name = State()
    email = State()
    timezone = State()

class ProfileHandlers:
    def __init__(self, router: Router, repository: Repository):
        self.router = router
        self.repository = repository

        self.router.message.register(self.start_registration, Command('registration'))
        self.router.message.register(self.add_name, Registration.name)
        self.router.message.register(self.add_email, Registration.email)
        self.router.callback_query.register(self.add_timezone, Registration.timezone)

        self.router.message.register(self.show_profile, Command('profile'))

    async def start_registration(self, message: Message, state: FSMContext):
        user = self.repository.get_user_by_id(message.from_user.id)
        if user:
            await message.answer('Вы уже зарегистрированы.')
            return
        await state.set_state(Registration.name)
        await message.answer('Введите ваше имя:')
    
    async def add_name(self, message: Message, state: FSMContext):
        if not message.text.isalpha():
            await message.answer("Пожалуйста, введите имя буквами.")
            return
        if  len(message.text) > 20:
            await message.answer("Имя слишком длинное.")
            return

        await state.update_data(name=message.text)
        await state.set_state(Registration.email)
        await message.answer('Введите вашу почту:')

    async def add_email(self, message: Message, state: FSMContext):
        if not valid.is_valid_email(message.text):
            await message.answer("Введите почту в корректном формате.")
            return
        if  len(message.text) > 100:
            await message.answer("Почта слишком длинная.")
            return

        await state.update_data(email=message.text)
        await state.set_state(Registration.timezone)

        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=tz, callback_data=tz)] for tz in timezones
            ]
        )
        await message.answer("Выберите ваш часовой пояс:", reply_markup=buttons)
        
    async def add_timezone(self, callback: CallbackQuery, bot: Bot, state: FSMContext):
        timezone = callback.data
        await state.update_data(timezone=timezone)
        await callback.message.answer(f"Часовой пояс установлен: {timezone}.")
        await callback.message.edit_reply_markup(reply_markup=None)

        data = await state.get_data()
        await state.clear()

        user = User(callback.from_user.id, data.get("name"), data.get("email"), data.get("timezone"))

        self.repository.add_user(user)

        await callback.message.answer(f"Приятно познакомиться, {data.get('name')}!\nТеперь предлагаю выбрать тебе настройки поиска. Для этого введи комманду /settings")
    
    async def show_profile(self,  message: Message):
        user_id = message.from_user.id

        user = self.repository.get_user_by_id(user_id)

        profile_text = (
            f"Ваш профиль:\n"
            f"Имя: {user.name}\n"
            f"Почта: {user.email}\n"
            f"Временная зона: {user.timezone}\n"
        )

        await message.answer(profile_text)