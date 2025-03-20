from smolagents import ToolCallingAgent, HfApiModel, DuckDuckGoSearchTool, tool
from smolagents.tools import Tool

from transformers import pipeline
from typing import Any, List, Dict
from transformers import MarianMTModel, MarianTokenizer

# Для Юпитера
# import IPython
# IPython.display.clear_output(wait=True)

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents.base import Document


# два след. импорта для получения текущего времени
import datetime
import pytz

# начальный промпт написан в *yaml файле
import yaml

import os

# Хуйня для парсинга
import re
import time
import requests
from selenium import webdriver
from xml.etree import ElementTree as ET
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# from agents.pdf_download import download_pdf

# from PyPDF2 import PdfReader

# Беру свой токен из HugginFace, так как для импорта любой моделей он требуется
TOKEN = "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"
os.environ["HF_TOKEN"] = TOKEN
# os.environ["TOKENIZERS_PARALLELISM"] = "false" # Отключил параллелизм, дабы избежать варнингов
# Модель из HugginFace. Импортируем Qwen2.5. Мозг Агента
model = HfApiModel(
    max_tokens=5000,
    temperature=0.5,
    model_id='Qwen/Qwen2.5-Coder-32B-Instruct',
    custom_role_conversions=None
)

# Инициализируем Embeddings для упрощенного поиска
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Модель, делающая саммаризацию текста
# Используем device='cpu', чтобы не было конфликтов при запуске на других ноутах
# Выгоднее было бы использовать cuda (windows) или mps (macos), но не у всех доступна cuda :(
summarizer = pipeline(task="summarization", model="facebook/bart-large-cnn", device='cpu')

# Разделитель нашего файла. Разделяет его на документы, дабы векторизовать файлик
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

# Инициализируем модель, которая переводит с русского языка на английский
model_from_russian_to_english = "Helsinki-NLP/opus-mt-ru-en"
tokenizer_russian = MarianTokenizer.from_pretrained(model_from_russian_to_english)
model_russian = MarianMTModel.from_pretrained(model_from_russian_to_english)

# Инициализируем моедель, которая с английского переводит на русский
model_from_english_to_russian = "Helsinki-NLP/opus-mt-en-ru"
tokenizer_english = MarianTokenizer.from_pretrained(model_from_english_to_russian)
model_english = MarianMTModel.from_pretrained(model_from_english_to_russian)


def download_pdf(pdf_url: str, save_path: str) -> None:
    """
    Download a PDF file from a given URL and save it to the specified path.

    Parameters:
        pdf_url (str): The URL of the PDF file to download.
        save_path (str): The file path where the PDF will be saved.

    Raises:
        ValueError: If the response from the server is not successful (status code not 200).
    """
    response = requests.get(pdf_url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
    else:
        raise ValueError(f"Could not download PDF: {response.status_code}")


def from_pdf_to_vector(pdf_path: str) -> InMemoryVectorStore:
    """
    Extract text from a given PDF file and convert it into a vector store.

    This function loads text from a PDF file specified by `pdf_path`, splits the text
    into smaller documents, and creates an in-memory vector store using those documents.

    Args:
        pdf_path (str): The path to the PDF file from which to extract text.

    Returns:
        InMemoryVectorStore: An in-memory vector store populated with
        vectorized representations of the extracted documents.

    Raises:
        FileNotFoundError: If the specified PDF file does not exist.
        ValueError: If the PDF file cannot be processed.
    """
    text_loader = PyPDFLoader(pdf_path)
    text_contents = [doc.page_content for doc in text_loader.load()]

    split_documents = splitter.create_documents(text_contents)
    vector_store = InMemoryVectorStore.from_documents(split_documents, embedding_model)

    return vector_store


def summarize_text_article(documents: List[Document],
                           percent_to_keep: float = 0.2) -> str:
    """
    Generate a summary of the given documents.

    This function extracts text from a list of Document objects,
    and uses a summarization model to generate a concise summary
    while keeping a specified percentage of the original text.
    The percentage to keep can be defined through the
    `percent_to_keep` parameter, allowing for control over
    the length of the summary.

    Args:
        documents (List[Document]): A list of Document objects
            containing the text to be summarized.
        percent_to_keep (float, optional): The percentage of the original
            text length to retain in the summary (default is 0.2, which
            means 20%).

    Returns:
        str: The generated summary of the documents, which reflects
        the most important points based on the provided content.

    Raises:
        ValueError: If the list of documents is empty or if
        the calculated target length is invalid.
    """

    context = "\n".join([re.sub(r'\s+', ' ', doc.page_content).strip() for doc in documents])
    original_length = len(context.split())
    target_length = int(original_length * percent_to_keep)
    target_length = max(30, min(target_length, 1024))

    summary = summarizer(context, max_length=target_length,
                         min_length=max(30, int(target_length * 0.8)),
                         do_sample=False)
    return summary[0]["summary_text"]


@tool
def search_arxiv(query: str, max_results: int, summarize: bool, sort_by: str = "relevance") -> List[Dict]:
    """
    YOU MUST SEND PDF_URL

    A tool that searches for articles on arXiv based on a query and optionally generates summaries.

    This function queries the arXiv API to retrieve scholarly articles matching the provided search query.
    It supports downloading PDFs of the articles, converting them into vector representations, and generating
    summaries if requested. The function is designed to handle errors gracefully, including retries for network
    issues and validation of input parameters.

    Args:
        query: str, The search query for finding articles on arXiv. This can be a topic, keyword, or phrase
                     (e.g., "quantum computing", "machine learning applications").
        max_results: int, The maximum number of articles to return. Must be between 1 and 5 (inclusive).
                           This limit ensures manageable processing times and avoids overloading the system.
        summarize: bool, A flag indicating whether to generate summaries for the retrieved articles. If True,
                          the function will process the downloaded PDFs to extract and summarize key information.
        sort_by: str The sorting criterion for the results. Options are:
                       - "relevance" (default): Sort by relevance to the query.
                       - "lastUpdatedDate": Sort by the last updated date.
                       - "submittedDate": Sort by the submission date.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary contains the following keys:
            - 'title' (str): The title of the article.
            - 'pdf_url' (str): The URL of the article's PDF on arXiv.
            - 'local_pdf_path' (str): The local file path where the PDF has been downloaded.
            - 'summary' (str): A summary of the article's content (if `summarize` is True); otherwise, an empty string.

    Raises:
        ValueError: If `max_results` is less than 1 or greater than 5.
        RuntimeError: If there are repeated failures in fetching data from arXiv after multiple retry attempts.

    Notes:
        - The function uses exponential backoff for retrying failed requests to the arXiv API.
        - PDFs are downloaded into a local "downloads" directory, which is created if it does not already exist.
        - Summaries are generated using similarity search over vectorized PDF content, followed by text summarization techniques.
        - If a PDF download fails, the corresponding article is skipped, and the function proceeds with the next result.

    Example Usage:
        # Search for 3 articles on "neural networks" sorted by relevance and generate summaries
        results = search_arxiv(query="neural networks", max_results=3, summarize=True, sort_by="relevance")
        for result in results:
            print(f"Title: {result['title']}")
            print(f"PDF URL: {result['pdf_url']}")
            print(f"Summary: {result['summary']}\n")

        # Search for 5 articles on "attention in machine learning" sorted by submission date
        results = search_arxiv(query="attention in machine learning", max_results=5, summarize=False, sort_by="submittedDate")
        for result in results:
            print(f"Title: {result['title']}")
            print(f"PDF URL: {result['pdf_url']}\n")
    """
    print("In process of finding articles...")
    max_results = min(max_results, 5)

    # Validate sort_by parameter
    valid_sort_options = {"relevance", "lastUpdatedDate", "submittedDate"}
    if sort_by not in valid_sort_options:
        raise ValueError(f"Invalid sort_by value. Must be one of: {', '.join(valid_sort_options)}.")

    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending"
    }

    for attempt in range(5):
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            break
        except (requests.exceptions.RequestException, ConnectionResetError) as e:
            if attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Error fetching data from arXiv after {attempt + 1} attempts: {e}")

    root = ET.fromstring(response.content)
    entries = []
    os.makedirs("downloads", exist_ok=True)

    for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
        title = entry.find('{http://www.w3.org/2005/Atom}title').text
        pdf_url = entry.find('{http://www.w3.org/2005/Atom}link[@title="pdf"]').attrib['href']

        pdf_filename = pdf_url.split("/")[-1] + ".pdf"
        pdf_path = os.path.join("downloads", pdf_filename)
        try:
            download_pdf(pdf_url, pdf_path)
        except Exception as e:
            print(f"Failed to download PDF: {e}")
            continue

        summary_text = ""
        if summarize:
            vector = from_pdf_to_vector(pdf_path)
            documents = vector.similarity_search(query)
            summary_text = summarize_text_article(documents)

        entries.append({
            'title': title,
            'pdf_url': pdf_url,
            'local_pdf_path': pdf_path,
            'summary': summary_text
        })

    return entries


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Запуск браузера в фоновом режиме
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
            print(f"PDF успешно скачан: {output_filename}")
        else:
            print(f"Ошибка при скачивании PDF: {response.status_code}")
            print(f"URL: {url}")
    except Exception as e:
        print(f"Ошибка при скачивании PDF: {str(e)}")


@tool
def scrape_pubmed_pdfs(query: str, max_articles: int = 5, summarize: bool = True, sort_by: str = "relevance") -> List[Dict]:
    """
    YOU MUST SEND PDF_URL
    A tool that searches for articles on PubMed Central (PMC) based on a query and optionally generates summaries.
    The National Center for Biotechnology Information advances science and health by providing access to biomedical
    and genomic information.

    This function queries PubMed Central to retrieve scholarly articles matching the provided search query.
    It supports downloading PDFs of the articles, converting them into vector representations, and generating
    summaries if requested. The function is designed to handle errors gracefully, including retries for network
    issues and validation of input parameters.

    Args:
        query: str, The search query for finding articles on PubMed Central. This can be a topic, keyword, or phrase
                     (e.g., "cancer research", "machine learning in biology").
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
        ValueError: If `max_articles` is less than 1 or greater than 5, or if `sort_by` is not one of the allowed values.
        RuntimeError: If there are repeated failures in fetching data from PubMed Central after multiple retry attempts.

    Notes:
        - The function uses Selenium WebDriver to interact with the PubMed Central website and retrieve article links.
        - PDFs are downloaded into a local "downloads" directory, which is created if it does not already exist.
        - Summaries are generated using similarity search over vectorized PDF content, followed by text summarization techniques.
        - If a PDF download fails, the corresponding article is skipped, and the function proceeds with the next result.
        - To avoid deadlocks or performance issues caused by parallelism in the `tokenizers` library, the environment variable
          `TOKENIZERS_PARALLELISM` is set to `false` internally.

    Example Usage:
        # Search for 3 articles on "gene editing" sorted by relevance and generate summaries
        results = scrape_pubmed_pdfs(query="gene editing", max_articles=3, summarize=True, sort_by="relevance")
        for result in results:
            print(f"Title: {result['title']}")
            print(f"Link: {result['link']}")
            print(f"Local PDF Path: {result['local_pdf_path']}")
            print(f"Summary: {result['summary']}\n")

        # Search for 5 articles on "CRISPR technology" sorted by publication date
        results = scrape_pubmed_pdfs(query="CRISPR technology", max_articles=5, summarize=False, sort_by="date")
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
        search_url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={query}{sort_param}"
        driver.get(search_url)

        selenium_cookies = driver.get_cookies()
        requests_cookies = {c['name']: c['value'] for c in selenium_cookies}

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


@tool
def get_current_time_in_timezone(timezone: str) -> str:
    """
    A tool that fetches the current local time in a specified timezone.

    Args:
        timezone: A string representing a valid timezone (e.g., 'America/New_York').
    """
    try:
        tz = pytz.timezone(timezone)
        local_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        return f"The current local time in {timezone} is: {local_time}"
    except Exception as e:
        return f"Error fetching time for timezone '{timezone}': {str(e)}"


class FinalAnswerTool(Tool):
    name = "final_answer"
    description = "Provides a final answer to the given problem. If there is a query about finding an article, you should send summary and pdf_url for each article."
    inputs = {'answer': {'type': 'any', 'description': 'The final answer to the problem'}}
    output_type = "any"

    def forward(self, answer: Any) -> Any:
        return answer

    def __init__(self, *args, **kwargs):
        self.is_initialized = False


try:
    with open("prompts.yaml", 'r') as stream:
        prompt_templates = yaml.safe_load(stream)
except FileNotFoundError:
    prompt_templates = {}

final_answer = FinalAnswerTool()
web_search = DuckDuckGoSearchTool()
# prompt_templates['system_prompt'][:100]

agent = ToolCallingAgent(
    model=model,
    tools=[final_answer,
           web_search,
           get_current_time_in_timezone,
           search_arxiv,
           scrape_pubmed_pdfs],
    max_steps=5,
    verbosity_level=1,
    grammar=None,
    planning_interval=None,
    name="AndrewSolver",
    description=None,
    prompt_templates=prompt_templates
)


def translate(text, tokenizer, model):
    """
    Функция для перевода с одного языка на другой.
    """
    tokenized_text = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    translated_tokens = model.generate(**tokenized_text)
    translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    return translated_text




results = []
for i in range(10):
    message = input() + "\nIf there is a query linked with article then send the user a pdf_url. It's so important"
    russian_word_pattern = r'\b[а-яА-ЯёЁ]+\b'
    matches = re.findall(russian_word_pattern, message)
    if matches:
        message = translate(message, tokenizer_russian, model_russian)
    try:
        print(message)
        result = agent.run(message)
        results += [result.replace("\\n", "\n")]
    except Exception as e:
        results += [f"Возникла ошибка: {e}"]

print(results)