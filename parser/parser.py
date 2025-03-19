from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests


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

