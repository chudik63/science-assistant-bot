import os
import yaml
import re
# import datetime
# import pytz
# from typing import Any

from smolagents import ToolCallingAgent, HfApiModel, DuckDuckGoSearchTool
# from smolagents.tools import Tool

from langchain_huggingface import HuggingFaceEmbeddings

from agent.tools.arxiv_search import search_arxiv
from agent.tools.pubmed_scrape import scrape_pubmed_pdfs
from agent.tools.time_tool import get_current_time_in_timezone
from agent.tools.final_answer_tool import FinalAnswerTool

from agent.utils.translation import translate, tokenizer_russian, model_russian


# Беру свой токен из HugginFace, так как для импорта любой моделей он требуется
TOKEN = "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"
os.environ["HF_TOKEN"] = TOKEN
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Модель из HugginFace. Импортируем Qwen2.5. Мозг Агента
model = HfApiModel(
    max_tokens=5000,
    temperature=0.5,
    model_id='Qwen/Qwen2.5-Coder-32B-Instruct',
    custom_role_conversions=None
)

# Инициализируем Embeddings для упрощенного поиска
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

try:
    with open("agent/prompts.yaml", 'r') as stream:
        prompt_templates = yaml.safe_load(stream)
except FileNotFoundError:
    prompt_templates = {}


final_answer = FinalAnswerTool()
web_search = DuckDuckGoSearchTool()

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


def run_agent(message: str) -> str:
    """
    Runs the agent with the given message and returns the result.
    """
    russian_word_pattern = r'\b[а-яА-ЯёЁ]+\b'
    matches = re.findall(russian_word_pattern, message)
    if matches:
        message = translate(message, tokenizer_russian, model_russian)
    try:
        result = agent.run(message)
        return result.replace("\\n", "\n")
    except Exception as e:
        return f"Возникла ошибка: {e}"


if __name__ == '__main__':
    results = []
    for i in range(10):
        message = input() + "\nIf there is a query linked with article then send the user a pdf_url. It's so important"
        result = run_agent(message)
        results.append(result)
    print(results)
