from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from models.Classes_for_db import FilterSettings
import time
import re
from urllib.parse import quote


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def download_pdf(url, output_filename, referer_url, cookies):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": referer_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    response = requests.get(url, headers=headers, cookies=cookies, stream=True)

    if response.status_code == 200:
        with open(output_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"PDF успешно скачан: {output_filename}")
    else:
        print(f"Ошибка при скачивании PDF: {response.status_code}")
        print(f"URL: {url}")
'''
Передаётся либо count = 2
    Если передаётся 2, то нужно искать по одной новой статье по теме или автору
Передаётся либо count = 5 для первого раза
    Если передаётся 5, то нужно искать по 3 по топику и 2 по автору
'''


def scrape_pubmed_pdfs_by_author(author_name, max_articles=5):
    driver = init_driver()
    article_links = []  # Инициализация списка для ссылок

    try:
        list_author_name = author_name.split(" ")
        author_name_formatted = "+".join(list_author_name)
        search_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={author_name_formatted}&sort=pubdate"

        driver.get(search_url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".rprt"))
        )

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        articles = driver.find_elements(By.CSS_SELECTOR, ".rprt")
        article_data = []

        for article in articles:
            try:
                title = article.find_element(By.CSS_SELECTOR, ".title a").text
                link = article.find_element(By.CSS_SELECTOR, ".title a").get_attribute("href")
                authors_section = article.find_element(By.CSS_SELECTOR, ".desc").text

                authors = re.split(r'\d{4}', authors_section)[0].strip()
                authors = authors.replace(';', ',').split(',')
                authors = [a.strip() for a in authors if a.strip()]

                article_data.append({
                    "title": title,
                    "link": link,
                    "authors": authors
                })

            except Exception as e:
                print("Ошибка парсинга статьи:", str(e))

        author_name_lower = author_name.lower()
        relevant_articles = []
        for article in article_data:
            for author in article["authors"]:
                if author_name_lower in author.lower():
                    relevant_articles.append(article)
                    break

        relevant_articles = relevant_articles[:max_articles]

        # Основное изменение: сохраняем ссылки перед обработкой
        for i, article in enumerate(relevant_articles):
            article_links.append(article["link"])  # Сохраняем ссылку

            print(f"\nОбрабатываем статью {i + 1}:")
            print("Заголовок:", article['title'])
            print("Ссылка:", article['link'])

            try:
                driver.get(article["link"])
                selenium_cookies = driver.get_cookies()
                requests_cookies = {c['name']: c['value'] for c in selenium_cookies}

                pdf_element = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    "//a[contains(translate(@href, 'PDF', 'pdf'), 'pdf')]"))
                )

                pdf_url = pdf_element.get_attribute("href")

                if not pdf_url.startswith("http"):
                    base_url = "/".join(article["link"].split("/")[:5])
                    pdf_url = f"{base_url}/{pdf_url.lstrip('/')}"

                download_pdf(pdf_url, f"author_article_{i + 1}.pdf", article["link"], requests_cookies)

            except Exception as e:
                print(f"Ошибка обработки: {str(e)}")

            driver.back()
            time.sleep(1)

    finally:
        driver.quit()

    print("\nВсе собранные ссылки:")
    for link in article_links:
        print(link)

    return article_links  # Возвращаем список ссылок
def scrape_pubmed_pdfs(query, max_articles=5):
    driver = init_driver()
    try:
        # Добавляем сортировку по дате публикации
        search_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={query}&sort=pubdate"
        driver.get(search_url)

        # Ждём загрузки статей
        selenium_cookies = driver.get_cookies()
        requests_cookies = {c['name']: c['value'] for c in selenium_cookies}

        articles = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".rprt"))
        )

        # Собираем ссылки на статьи и их заголовки
        article_data = []
        for article in articles:
            title = article.find_element(By.CSS_SELECTOR, ".title a").text
            link = article.find_element(By.CSS_SELECTOR, ".title a").get_attribute("href")
            article_data.append({"title": title, "link": link})

        # Фильтруем статьи по релевантности
        relevant_articles = [
                                article for article in article_data
                                if query.lower() in article["title"].lower()
                            ][:max_articles]

        # Если релевантных статей меньше, чем нужно, выводим предупреждение
        if len(relevant_articles) < max_articles:
            print(f"Найдено только {len(relevant_articles)} релевантных статей.")

        for i, article in enumerate(relevant_articles):
            print(f"\nОбрабатываем статью {i + 1}: {article['title']}")
            driver.get(article["link"])

            # Обновляем куки для каждой статьи
            selenium_cookies = driver.get_cookies()
            requests_cookies = {c['name']: c['value'] for c in selenium_cookies}

            try:
                # Ищем ссылку на PDF
                pdf_element = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    "//a[contains(translate(@href, 'PDF', 'pdf'), 'pdf') or "
                                                    "contains(translate(., 'PDF', 'pdf'), 'pdf')]"))
                )

                pdf_url = pdf_element.get_attribute("href")

                # Если ссылка относительная, делаем её абсолютной
                if not pdf_url.startswith("http"):
                    base_url = "/".join(article["link"].split("/")[:5])
                    pdf_url = f"{base_url}/{pdf_url.lstrip('/')}"

                print(f"Найдена PDF ссылка: {pdf_url}")
                download_pdf(pdf_url, f"article_{i + 1}.pdf", article["link"], requests_cookies)

            except Exception as e:
                print(f"Ошибка: {str(e)}")

    finally:
        driver.quit()


def scrape_pubmed_pdfs_by_type(type_query, max_articles=5):
    driver = init_driver()
    try:
        formatted_type = quote(type_query)
        search_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={formatted_type}&sort=pubdate"
        driver.get(search_url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".rprt"))
        )

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        articles = driver.find_elements(By.CSS_SELECTOR, ".rprt")
        relevant_articles = [
            {
                "title": article.find_element(By.CSS_SELECTOR, ".title a").text,
                "link": article.find_element(By.CSS_SELECTOR, ".title a").get_attribute("href")
            }
            for article in articles[:max_articles]
        ]

        print(f"Processing {len(relevant_articles)} articles")

        # Основное исправление: весь блок обработки статьи внутри цикла
        for i, article in enumerate(relevant_articles):
            print(f"\nArticle {i + 1}:")
            print("Title:", article['title'])
            print("Link:", article['link'])

            try:
                driver.get(article["link"])
                selenium_cookies = driver.get_cookies()
                requests_cookies = {c['name']: c['value'] for c in selenium_cookies}

                # Поиск PDF с улучшенным селектором
                pdf_element = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.pdf')]"))
                )

                pdf_url = pdf_element.get_attribute("href")
                if not pdf_url.startswith("http"):
                    pdf_url = f"https://www.ncbi.nlm.nih.gov{pdf_url}"

                download_pdf(
                    pdf_url,
                    f"article_{i + 1}_{article['title'][:50]}.pdf",  # Уникальное имя файла
                    article["link"],
                    requests_cookies
                )
                print(f"Successfully downloaded: {article['title']}")

            except Exception as e:
                print(f"Failed to process article {i + 1}: {str(e)}")

            # Возврат на страницу результатов для надежности
            driver.back()
            time.sleep(1)  # Небольшая пауза для стабилизации

    finally:
        driver.quit()

#scrape_pubmed_pdfs_by_type(type_query="information article", max_articles=3)
#scrape_pubmed_pdfs_by_author(author_name="John Doe", max_articles=3)
#scrape_pubmed_pdfs("cancer", max_articles=5)