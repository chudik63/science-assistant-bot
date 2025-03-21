import os
import time
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from smolagents.tools import tool
from datetime import datetime

from agent.utils.pdf_utils import download_pdf, from_pdf_to_vector
from agent.utils.summarization import summarize_text_article


@tool
def search_arxiv(query: str, max_results: int, summarize: bool, sort_by: str = "relevance",
                 sort_order: str = "descending",  # Added sort_order parameter
                 start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
    """
    YOU MUST SEND PDF_URL

    A tool that searches for articles on arXiv based on a query and optionally generates summaries.

    This function queries the arXiv API to retrieve scholarly articles matching the provided search query.
    It supports downloading PDFs of the articles, converting them into vector representations, and generating
    summaries if requested. The function is designed to handle errors gracefully, including retries for network
    issues and validation of input parameters.


    Args:
        query: str, The search query for finding articles on arXiv.
        max_results: int, The maximum number of articles to return (1-5).
        summarize: bool, A flag indicating whether to generate summaries.
        sort_by: str, The sorting criterion ("relevance", "lastUpdatedDate", "submittedDate").
        sort_order: str, The sorting order ("ascending", "descending").
        start_date: Optional[str], The start date for filtering articles (YYYY-MM-DD).
        end_date: Optional[str], The end date for filtering articles (YYYY-MM-DD).

    Returns:
        List[Dict]: A list of dictionaries with article details.

    Raises:
        ValueError: If `max_results` is out of range or date formats are incorrect.
        RuntimeError: If there are repeated failures in fetching data from arXiv.
    """
    print("In process of finding articles...")

    # Validate max_results
    if not 1 <= max_results <= 5:
        raise ValueError("max_results must be between 1 and 5")

    # Validate sort_by parameter
    valid_sort_options = {"relevance", "lastUpdatedDate", "submittedDate"}
    if sort_by not in valid_sort_options:
        raise ValueError(f"Invalid sort_by value. Must be one of: {', '.join(valid_sort_options)}.")

    # Validate sort_order parameter
    valid_sort_orders = {"ascending", "descending"}
    if sort_order not in valid_sort_orders:
        raise ValueError(f"Invalid sort_order value. Must be one of: {', '.join(valid_sort_orders)}.")

    # Validate date formats
    if start_date:
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("start_date must be in YYYY-MM-DD format")
    if end_date:
        try:
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("end_date must be in YYYY-MM-DD format")

    base_url = "http://export.arxiv.org/api/query"
    search_query = f"({query})"

    # Add date range filter if provided
    if start_date and end_date:
        search_query = f"({query} AND submittedDate:[{start_date} TO {end_date}])"
    elif start_date:
        # articles from start_date until today
        search_query = f"({query} AND submittedDate:[{start_date} TO TODAY])"
    elif end_date:
        # articles from the beginning until end_date
        search_query = f"({query} AND submittedDate:[1991-01-01 TO {end_date}])"

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": sort_order
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
            try:
                vector = from_pdf_to_vector(pdf_path)
                documents = vector.similarity_search(query)
                summary_text = summarize_text_article(documents)
            except Exception as e:
                print(f"Failed to summarize PDF: {e}")
                summary_text = "Summary unavailable due to processing error."
        os.remove(pdf_path)
        entries.append({
            'title': title,
            'pdf_url': pdf_url,
            # 'local_pdf_path': pdf_path,
            'summary': summary_text
        })

    return entries
