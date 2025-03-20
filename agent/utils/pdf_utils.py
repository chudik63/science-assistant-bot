# import os
import requests

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings


# Инициализируем Embeddings для упрощенного поиска
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)


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
