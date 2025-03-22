import re
from typing import List
from langchain_core.documents.base import Document
from transformers import pipeline
from langchain_huggingface import HuggingFaceEmbeddings
import torch

# Модель, делающая саммаризацию текста
# Используем device='cpu', чтобы не было конфликтов при запуске на других ноутах
# Выгоднее было бы использовать cuda (windows) или mps (macos), но не у всех доступна cuda :(
device = 'cpu'

if torch.cuda.is_available():
    device = 'cuda'
elif torch.mps.is_available():
    device = 'mps'

model_summary = "facebook/bart-large-cnn"
model_embedding = "sentence-transformers/all-MiniLM-L6-v2"

summarizer = pipeline(task="summarization", model=model_summary,
                      device=device)

embedding_model = HuggingFaceEmbeddings(model_name=model_embedding)


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
