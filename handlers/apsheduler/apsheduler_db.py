from aiogram import Bot
from repository.repository import Repository
from parser.parser import scrape_pubmed_pdfs_by_type, scrape_pubmed_pdfs, scrape_pubmed_pdfs_by_author
from models.Classes_for_db import FilterSettings
from agent.tools.arxiv_search import brief_search_arxiv, brief_search_arxiv_by_authors

async def check_and_send_updates(bot: Bot, repository: Repository):
    users_info = await repository.get_all_users_settings()
    for us_info in users_info:
        user_id = us_info[0]
        source = us_info[4]  # Источник (например, "PubMed" или "arXiv")
        old_links = us_info[5]
        if us_info[4] == "PubMed":
            new_links = scrape_pubmed_pdfs(us_info[2], max_articles=3)
            new_links.extend(scrape_pubmed_pdfs_by_author(us_info[1], max_articles=3))
            new_links.extend(scrape_pubmed_pdfs_by_type(us_info[3], max_articles=2))
            new_links = list(set(new_links))
            if new_links != old_links:
                await repository.update_links(user_id, new_links)
                for link in new_links:
                    if link not in old_links:
                        message_text = f"Новая статья на PubMed: {link}"
                        await bot.send_message(chat_id=user_id, text=message_text)
            else:
                print(f"Новых статей не было найдено")
        elif us_info[4] == "arXiv":
            user_settings_query = FilterSettings(user_id=user_id, authors=us_info[1],
                                                 topics=us_info[2],
                                                 types=us_info[3], sources=us_info[4], links=[])
            new_links = brief_search_arxiv(user_settings_query, max_results=3)
            new_links.extend(brief_search_arxiv_by_authors(user_settings_query, max_results=3))
            new_links = list(set(new_links))
            if new_links != old_links:
                await repository.update_links(user_id, new_links)
                for link in new_links:
                    if link not in old_links:
                        message_text = f"Новая статья на PubMed: {link}"
                        await bot.send_message(chat_id=user_id, text=message_text)
            else:
                print(f"Новых статей не было найдено")