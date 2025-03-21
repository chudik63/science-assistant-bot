from aiogram import Bot, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
from agent.tools.arxiv_search import brief_search_arxiv
from repository.repository import Repository
from models.Classes_for_db import FilterSettings
from datetime import date

sources = [
    "PubMed", "arXiv"
]


class Settings(StatesGroup):
    authors = State()
    topics = State()
    types = State()
    sources = State()
    links = State()


class SettingsHandlers:
    def __init__(self, router: Router, repository: Repository):
        self.router = router
        self.repository = repository

        self.router.message.register(self.fill_settings, Command('settings'))
        self.router.message.register(self.add_authors, Settings.authors)
        self.router.message.register(self.add_topics, Settings.topics)
        self.router.message.register(self.add_types, Settings.types)
        self.router.message.register(self.add_sources, Settings.sources)
        self.router.message.register(self.add_links_for_fav_articles, Settings.links)

    async def fill_settings(self, message: Message, state: FSMContext):
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
        await message.answer('Введите типы публикаций, которые могут быть вам интересны:')

    async def add_types(self, message: Message, state: FSMContext):
        if not message.text.isalpha():
            await message.answer("Пожалуйста, введите корректные типы.")
            return

        await state.update_data(types=message.text)
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
        await state.set_state(Settings.links)
        await callback.message.answer(f"Теперь мы можем подобрать для вас любимые статьи по предпочтениям:\n")
        # data = await state.get_data()
        # await state.clear()

        # settings = FilterSettings(callback.from_user.id, data.get("keywords"), data.get("authors"), data.get("topics"),
        #                         data.get("types"), data.get("time_interval"), data.get("sources"))

        # self.repository.add_filter_settings(settings)
        # await callback.message.answer(f"Ваши предпочтения сохранены!\n")

    async def add_links_for_fav_articles(self, message: Message, state: FSMContext):
        data = await state.get_data()
        id_user = message.from_user.id
        authors = data.get("authors")
        topics = data.get("topics")
        types = data.get("types")
        sources = data.get("sources")
        today = date.today()
        if today.month > 2:
            end_date = today.replace(month=today.month - 2)
        else:
            end_date = today.replace(year=today.year - 1, month=today.month + 10)

        # Форматируем дату в строку
        end_date_str = end_date.strftime("%Y-%m-%d")
        user_settings_query = FilterSettings(user_id=id_user, authors=authors, topics=topics,
                                             types=types, sources=sources, links=[])
        list_of_dicts_of_links = []
        if sources == "arXiv":
            list_of_dicts_of_links = brief_search_arxiv(user_settings_query,
                                                        start_date=date.today().strftime("%Y-%m-%d"),
                                                        end_date=end_date_str)
        else:

            '''функция для pubMed'''
        '''
        надо написать функцию, которая по этим пользовательским данным парсит ссылки по новым с arxiv или pubmed
        далее мы записываем эти ссылки в БД
        Потом мы через apsheduler заново запускаем эти функции парсинга, сверяем ссылки на статьи и если отличается, то присылаем уведомление пользователю 
        о новых статьях в тг или почту.
        '''
        self.repository.add_filter_settings(settings_with_links)
        '''apscheduler - раз в день будет делать проверку статей База данных с колонкой ссылок, там для каждого 
        пользователя хранится 5 его лобимых статей Apsheduler раз в несколько минут будет запускать arxiv и pubmed 
        парсеры и получать ссылки по предпочтениям пользователя Если он найдёт ссылки, которые будут отличаться от 
        того, что уже есть в базе, то он будет в тг и по почте отправлять уведомления пользователю
        
        пользовтель пишет - я получаю id  добавляю его сразу в 2 бд. Либо при заполнении анкеты  
        
        '''
