import os
# import time
from typing import List, Dict
from smolagents.tools import tool

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
from datetime import datetime

# from utils.pdf_utils import download_pdf
from agent.utils.pdf_utils import from_pdf_to_vector
from agent.utils.summarization import summarize_text_article


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run browser in headless mode
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def download_pdf_pubmed(url, output_filename, referer_url, cookies):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": referer_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    try:
        response = requests.get(url, headers=headers, cookies=cookies, stream=True)

        if response.status_code == 200:
            with open(output_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"PDF successfully downloaded: {output_filename}")
        else:
            print(f"Error downloading PDF: {response.status_code}")
            print(f"URL: {url}")
    except Exception as e:
        print(f"Error downloading PDF: {str(e)}")


@tool
def scrape_pubmed_pdfs(query: str, start_date: str = None, end_date: str = None, max_articles: int = 5, summarize: bool = True, sort_by: str = "relevance") -> List[Dict]:
    """
    YOU MUST SEND PDF_URL
    A tool that searches for articles on PubMed Central (PMC) based on a query and optionally generates summaries,
    with the ability to filter by publication date range.

    This function queries PubMed Central to retrieve scholarly articles matching the provided search query.
    It supports filtering articles by a specific date range, downloading PDFs of the articles, converting them
    into vector representations, and generating summaries if requested. The function handles errors gracefully,
    including retries for network issues and validation of input parameters.

    Args:
        query: str, The search query for finding articles on PubMed Central. This can be a topic, keyword, or phrase
                     (e.g., "cancer research", "machine learning in biology").
        start_date: str, Optional start date for filtering articles. Must be in "YYYY/MM/DD" format.
                      If provided, only articles published on or after this date will be included in the results.
        end_date: str, Optional end date for filtering articles. Must be in "YYYY/MM/DD" format.
                    If provided, only articles published on or before this date will be included in the results.
        max_articles: int, The maximum number of articles to return. Must be between 1 and 5 (inclusive).
                           This limit ensures manageable processing times and avoids overloading the system.
        summarize: bool, A flag indicating whether to generate summaries for the retrieved articles. If True,
                          the function will process the downloaded PDFs to extract and summarize key information.
        sort_by: str, The sorting criterion for the results. Options are:
                       - "relevance" (default): Sort by relevance to the query.
                       - "date": Sort by the publication date in descending order (most recent first).

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary contains the following keys:
            - 'title' (str): The title of the article.
            - 'link' (str): The URL of the article's page on PubMed Central.
            - 'local_pdf_path' (str): The local file path where the PDF has been downloaded.
            - 'summary' (str): A summary of the article's content (if `summarize` is True); otherwise, an empty string.

    Raises:
        ValueError: If `max_articles` is less than 1 or greater than 5, if `sort_by` is not one of the allowed values,
                    or if `start_date` or `end_date` are not in the correct format.
        RuntimeError: If there are repeated failures in fetching data from PubMed Central after multiple retry attempts.

    Notes:
        - The function uses Selenium WebDriver to interact with the PubMed Central website and retrieve article links.
        - PDFs are downloaded into a local "downloads" directory, which is created if it does not already exist.
        - Summaries are generated using similarity search over vectorized PDF content, followed by text summarization techniques.
        - If a PDF download fails, the corresponding article is skipped, and the function proceeds with the next result.
        - Date format must be YYYY/MM/DD.
        - To avoid deadlocks or performance issues caused by parallelism in the `tokenizers` library, the environment variable
          `TOKENIZERS_PARALLELISM` is set to `false` internally.

    Example Usage:
        # Search for articles on "gene editing" between 2020/01/01 and 2021/12/31, sorted by relevance, and generate summaries
        results = scrape_pubmed_pdfs(query="gene editing", start_date="2020/01/01", end_date="2021/12/31",
                                     max_articles=3, summarize=True, sort_by="relevance")
        for result in results:
            print(f"Title: {result['title']}")
            print(f"Link: {result['link']}")
            print(f"Local PDF Path: {result['local_pdf_path']}")
            print(f"Summary: {result['summary']}\n")

        # Search for articles on "CRISPR technology" published after 2022/01/01, sorted by publication date
        results = scrape_pubmed_pdfs(query="CRISPR technology", start_date="2022/01/01", max_articles=5,
                                     summarize=False, sort_by="date")
        for result in results:
            print(f"Title: {result['title']}")
            print(f"Link: {result['link']}")
            print(f"Local PDF Path: {result['local_pdf_path']}\n")
    """
    driver = init_driver()
    try:
        if sort_by not in ["relevance", "date"]:
            raise ValueError("Неверный параметр сортировки. Допустимые значения: 'relevance' или 'date'.")

        sort_param = "" if sort_by == "relevance" else "&sort=pubdate"
        date_filter = ""

        if start_date:
            try:
                datetime.strptime(start_date, "%Y/%m/%d")
            except ValueError:
                raise ValueError("Неверный формат даты начала. Используйте формат YYYY/MM/DD.")
            date_filter += f"&DateFrom={start_date}"

        if end_date:
            try:
                datetime.strptime(end_date, "%Y/%m/%d")
            except ValueError:
                raise ValueError("Неверный формат даты окончания. Используйте формат YYYY/MM/DD.")
            date_filter += f"&DateTo={end_date}"

        search_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={query}{sort_param}{date_filter}"
        driver.get(search_url)

        articles = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".rprt"))
        )

        article_data = []
        for article in articles:
            title = article.find_element(By.CSS_SELECTOR, ".title a").text
            link = article.find_element(By.CSS_SELECTOR, ".title a").get_attribute("href")
            article_data.append({"title": title, "link": link})

        os.makedirs("downloads", exist_ok=True)
        article_data = article_data[:max_articles]
        for i, article in enumerate(article_data[:max_articles]):
            driver.get(article["link"])
            selenium_cookies = driver.get_cookies()
            requests_cookies = {c['name']: c['value'] for c in selenium_cookies}
            try:
                pdf_element = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    "//a[contains(translate(@href, 'PDF', 'pdf'), 'pdf') or "
                                                    "contains(translate(., 'PDF', 'pdf'), 'pdf')]"))
                )
                pdf_url = pdf_element.get_attribute("href")
                if not pdf_url.startswith("http"):
                    base_url = "/".join(article["link"].split("/")[:5])
                    pdf_url = f"{base_url}/{pdf_url.lstrip('/')}"

                pdf_path = os.path.join("downloads", pdf_url.split("/")[-1])
                article_data[i]["local_pdf_path"] = pdf_path
                try:
                    download_pdf_pubmed(pdf_url, pdf_path, article["link"], requests_cookies)
                except Exception as e:
                    print(f"Failed to download PDF: {e}")
                    continue
                try:
                    summary_text = ""
                    if summarize:
                        vector = from_pdf_to_vector(pdf_path)
                        documents = vector.similarity_search(query)
                        summary_text = summarize_text_article(documents)
                    article_data[i]["summary"] = summary_text
                except Exception as e:
                    print(f"Ошибка в саммари: {e}")

            except Exception as e:
                print(f"Ошибка: {str(e)}")

        return article_data

    finally:
        driver.quit()
