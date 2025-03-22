import os
import logging
from typing import List, Dict

from smolagents.tools import tool

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

import requests
from requests.exceptions import RequestException
from datetime import datetime

from agent.utils.pdf_utils import from_pdf_to_vector
from agent.utils.summarization import summarize_text_article

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run browser in headless mode
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver
    except WebDriverException as e:
        logging.error(f"Failed to initialize WebDriver: {e}")
        raise

driver = init_driver()


def download_pdf_pubmed(url, output_filename, referer_url, cookies):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": referer_url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    try:
        with requests.get(url, headers=headers, cookies=cookies, stream=True) as response:
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            with open(output_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"PDF successfully downloaded: {output_filename}")
            return True
    except RequestException as e:
        logging.error(f"Error downloading PDF from {url}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error downloading PDF from {url}: {e}")
        return False


@tool
def scrape_pubmed_pdfs(query: str, start_date: str = None, end_date: str = None, max_articles: int = 5, summarize: bool = True, sort_by: str = "relevance") -> List[Dict]:
    """
    YOU MUST SEND PDF_URL

    This tool searches for articles on PubMed Central (PMC) based on a query and optionally generates summaries.

    PubMed is a free resource supporting the search and retrieval of biomedical and life sciences literature with the aim of improving health–both globally and personally.

    This function queries PubMed Central to retrieve scholarly articles matching the provided search query.
    It supports filtering articles by a specific date range and generating summaries if requested.
    The function is designed to handle errors gracefully.

    Args:
        query: str, The search query for finding articles on PubMed Central.
        start_date: str, Optional start date for filtering articles (YYYY/MM/DD).
        end_date: str, Optional end date for filtering articles (YYYY/MM/DD).
        max_articles: int, The maximum number of articles to return (1-5).
        summarize: bool, A flag indicating whether to generate summaries.
        sort_by: str, The sorting criterion ("relevance", "date").

    Returns:
        List[Dict]: A list of dictionaries with article details, including title, link, pdf_url (if available),
                    summary (if requested), and error (if any).  The agent MUST prioritize returning the 'pdf_url'
                    whenever possible.

    Raises:
        ValueError: If `max_articles` is out of range or date formats are incorrect.
        RuntimeError: If there are repeated failures in fetching data from PubMed Central.
    """
    if not 1 <= max_articles <= 5:
        raise ValueError("`max_articles` must be between 1 and 5 (inclusive).")

    if sort_by not in ["relevance", "date"]:
        raise ValueError("Неверный параметр сортировки. Допустимые значения: 'relevance' или 'date'.")

    # driver = init_driver()
    try:
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
            try:
                title = article.find_element(By.CSS_SELECTOR, ".title a").text
                link = article.find_element(By.CSS_SELECTOR, ".title a").get_attribute("href")
                article_data.append({"title": title, "link": link})
            except Exception as e:
                logging.warning(f"Failed to extract title or link from article: {e}")
                continue

        os.makedirs("downloads", exist_ok=True)
        article_data = article_data[:max_articles]
        for i, article in enumerate(article_data[:max_articles]):
            article_result = {"title": article["title"], "link": article["link"]} # Initialize result dictionary

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

                article_result["pdf_url"] = pdf_url  # Add pdf_url to result
                pdf_path = os.path.join("downloads", pdf_url.split("/")[-1])

                if download_pdf_pubmed(pdf_url, pdf_path, article["link"], requests_cookies):
                    try:
                        summary_text = ""
                        if summarize:
                            vector = from_pdf_to_vector(pdf_path)
                            documents = vector.similarity_search(query)
                            summary_text = summarize_text_article(documents)
                        article_result["summary"] = summary_text  # Add summary to result
                    except Exception as e:
                        logging.error(f"Error generating summary for {article['title']}: {e}")
                        article_result["error"] = f"Error generating summary: {e}"  # Add error message
                    finally:
                        try:
                            os.remove(pdf_path)  # Clean up PDF after summary or error
                        except OSError as e:
                            logging.warning(f"Could not delete PDF {pdf_path}: {e}")
                else:
                    article_result["error"] = "Failed to download PDF" # Add error message
            except Exception as e:
                logging.error(f"Error processing article {article['title']}: {e}")
                article_result["error"] = str(e)  # Add error message
            finally:
                article_data[i] = article_result # Update article data with the result

        return article_data

    except Exception as e:
        logging.exception("An unexpected error occurred:")
        raise # Re-raise the exception after logging
    # finally:
    #     driver.quit()
