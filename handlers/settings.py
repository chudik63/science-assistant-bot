from aiogram import Bot, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

from repository.repository import Repository
from models.models import FilterSettings

sources = ["PubMed", "arXiv"]
publication_types = ["Science", "General research", "Information", "Practical and analytical"]


class Settings(StatesGroup):
    keywords = State()
    authors = State()
    topics = State()
    types = State()
    time_interval = State()
    sources = State()


class SettingsHandlers:
    def __init__(self, router: Router, repository: Repository):
        self.router = router
        self.repository = repository

        self.router.message.register(self.show_settings, Command('settings'))
        self.router.message.register(self.show_settings, Command('edit_settings'))
        self.router.message.register(self.add_keywords, Settings.keywords)
        self.router.message.register(self.add_authors, Settings.authors)
        self.router.message.register(self.add_topics, Settings.topics)
        self.router.callback_query.register(self.add_types, Settings.types)  # Изменено
        self.router.message.register(self.add_interval, Settings.time_interval)
        self.router.message.register(self.add_sources, Settings.sources)

    async def show_settings(self, message: Message):
        settings = self.repository.get_filter_settings(message.from_user.id)
        if settings:
            settings_text = (
                f"Ваши настройки поиска.\n"
                f"Ключевые слова: {settings.keywords}\n"
                f"Авторы: {settings.authors}\n"
                f"Темы публикаций: {settings.topics}\n"
                f"Типы публикаций: {settings.types}\n"
                f"Интервал поиска: {settings.time_interval}\n"
                f"Источники: {settings.sources}\n"
                "Чтобы изменить настройки введите /edit_settings"
            )
            await message.answer(settings_text)
            return

        await message.answer("Ваши настройки не заданы. Хотите установить? -> /edit_settings")

    async def fill_settings(self, message: Message, state: FSMContext):
        await state.set_state(Settings.keywords)
        await message.answer('Введите ключевые слова, по которым нужно проводить поиск:')

    async def add_keywords(self, message: Message, state: FSMContext):
        await state.update_data(keywords=message.text)
        await state.set_state(Settings.authors)
        await message.answer('Введите авторов, публикации которых хотели бы получать:')

    async def add_authors(self, message: Message, state: FSMContext):
        await state.update_data(authors=message.text)
        await state.set_state(Settings.topics)
        await message.answer('Введите темы публикаций, которые могут быть вам интересны:')

    async def add_topics(self, message: Message, state: FSMContext):
        if not message.text.isalpha():
            await message.answer("Пожалуйста, введите корректные темы.")
            return

        await state.update_data(topics=message.text)
        await state.set_state(Settings.types)

        # Клавиатура с типами публикаций
        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=ptype, callback_data=ptype)] for ptype in publication_types
            ]
        )

        await message.answer('Выберите тип публикаций:', reply_markup=buttons)

    async def add_types(self, callback: CallbackQuery, state: FSMContext):
        selected_type = callback.data
        await state.update_data(types=selected_type)
        await callback.message.edit_reply_markup(reply_markup=None)

        await state.set_state(Settings.time_interval)
        await callback.message.answer('Введите временной интервал, в течение которого вас интересуют публикации:')

    async def add_interval(self, message: Message, state: FSMContext):
        await state.update_data(time_interval=message.text)
        await state.set_state(Settings.sources)

        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=s, callback_data=s)] for s in sources
            ]
        )

        await message.answer('Выберите источники, которые мне стоит проверять на наличие интересных публикаций:',
                             reply_markup=buttons)

    async def add_sources(self, callback: CallbackQuery, state: FSMContext):
        source = callback.data
        await state.update_data(sources=source)
        await callback.message.edit_reply_markup(reply_markup=None)

        data = await state.get_data()
        await state.clear()

        settings = FilterSettings(
            callback.from_user.id, data.get("keywords"), data.get("authors"), data.get("topics"),
            data.get("types"), data.get("time_interval"), data.get("sources")
        )

        self.repository.add_filter_settings(settings)
        await callback.message.answer(f"Ваши предпочтения сохранены!\n")
