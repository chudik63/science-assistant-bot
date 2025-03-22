from aiogram import Bot, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
from agent.tools.arxiv_search import brief_search_arxiv, brief_search_arxiv_by_authors
from repository.repository import Repository
from models.Classes_for_db import FilterSettings
from datetime import date
from deep_translator import GoogleTranslator
import asyncio
from parser.parser import scrape_pubmed_pdfs_by_type, scrape_pubmed_pdfs, scrape_pubmed_pdfs_by_author
sources = [
    "PubMed", "arXiv"
]
publication_types = ["Science", "General research", "Information", "Practical and analytical"]

class Settings(StatesGroup):
    authors = State()
    topics = State()
    types = State()
    sources = State()

class SettingsHandlers:
    def __init__(self, router: Router, repository: Repository):
        self.router = router
        self.repository = repository

        self.router.message.register(self.fill_settings, Command('search'))
        self.router.message.register(self.add_authors, Settings.authors)
        self.router.message.register(self.add_topics, Settings.topics)
        self.router.callback_query.register(self.add_types, Settings.types)
        self.router.callback_query.register(self.add_sources, Settings.sources)

        self.is_thinking = False

    async def fill_settings(self, message: Message, state: FSMContext):
        await state.set_state(Settings.authors)
        await message.answer('Введите авторов, публикации которых хотели бы получать:')

    async def add_authors(self, message: Message, state: FSMContext):
        await state.update_data(authors=message.text)
        await state.set_state(Settings.topics)
        await message.answer('Введите темы публикаций, которые могут быть вам интересны:')

    async def add_topics(self, message: Message, state: FSMContext):
        await state.update_data(topics=message.text)
        await state.set_state(Settings.types)
        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=ptype, callback_data=ptype)] for ptype in publication_types
            ]
        )

        await message.answer('Выберите тип публикаций:', reply_markup=buttons)

    async def add_types(self, callback: CallbackQuery, state: FSMContext):
        type = callback.data
        if not type.isalpha():
            await callback.message.answer("Пожалуйста, введите корректные типы.")
            return

        await state.update_data(types=type)
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.set_state(Settings.sources)
        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=s, callback_data=s)] for s in sources
            ]
        )

        await callback.message.answer('Выберите источники, которые мне стоит проверять на наличие интересных публикаций:',
                             reply_markup=buttons)

    async def add_sources(self, callback: CallbackQuery, state: FSMContext):
        source = callback.data
        await state.update_data(sources=source)
        await callback.message.edit_reply_markup(reply_markup=None)

        self.is_thinking = True
        thinking_task = asyncio.create_task(self.simulate_thinking(callback.message))

        loop = asyncio.get_running_loop()

        data = await state.get_data()
        
        result = await loop.run_in_executor(None, self.add_links_for_fav_articles, callback.from_user.id, data)

        self.is_thinking = False  
        await thinking_task

        await callback.message.answer(result)
        await callback.message.answer("Как только появятся новинки, я вам обязательно сообщу!")
        await state.clear()

    def add_links_for_fav_articles(self, user_id: int, data):
        authors = data.get("authors")
        authors_translated_en = GoogleTranslator(source="ru", target="en").translate(authors)
        topics = data.get("topics")
        topics_translated_en = GoogleTranslator(source="ru", target="en").translate(topics)
        types = data.get("types")
        sources = data.get("sources")

        # Форматируем дату в строку
        user_settings_query = FilterSettings(user_id=user_id, authors=authors_translated_en, topics=topics_translated_en,
                                             types=types, sources=sources, links=[])
        list_of_links = []
        if sources == "arXiv":
            list_of_links = brief_search_arxiv(user_settings_query, max_results=3)
            list_of_links.extend(brief_search_arxiv_by_authors(user_settings_query, max_results=3))
            for l in list_of_links:
                print(f"Links for arXiv: {l}\n")
        elif sources == "PubMed":
            list_of_links = scrape_pubmed_pdfs(topics_translated_en, max_articles=3)
            list_of_links.extend(scrape_pubmed_pdfs_by_author(authors_translated_en, max_articles=3))
            list_of_links.extend(scrape_pubmed_pdfs_by_type(types, max_articles=2))
            for l in list_of_links:
                print(f"Links for PubMed: {l}\n")

        user_settings_query.links = list_of_links
        
        self.repository.add_filter_settings(user_settings_query)
        if list_of_links:
            articles_message = "Вот список статей по заданным характеристикам:\n\n"
            articles_message += "\n".join(list_of_links)
        else:
            articles_message = "К сожалению, по вашим параметрам статей не найдено."

        return articles_message

    async def simulate_thinking(self, message: Message):
        thinking = "Подбираем для вас любимые статьи по предпочтениям"
        dot = "."
        think = await message.answer(thinking)
        c = 1
        while self.is_thinking:
            if c == 4:
                c = 0
            await asyncio.sleep(1)
            await think.edit_text(thinking + dot * c)
            c += 1
        # По завершении анимации можно удалить сообщение
        await think.delete()