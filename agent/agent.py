import logging
import os
import yaml
from smolagents import ToolCallingAgent, HfApiModel, DuckDuckGoSearchTool
# from langchain_huggingface import HuggingFaceEmbeddings

from agent.tools.arxiv_search import search_arxiv
from agent.tools.pubmed_scrape import scrape_pubmed_pdfs, driver
# from agent.tools.time_tool import get_current_time_in_timezone
from agent.tools.final_answer_tool import FinalAnswerTool

from agent.utils.process_markdown import remove_markdown_symbols
# from agent.utils.translation import translate, tokenizer_russian, model_russian


class Agent:
    def __init__(self, token: str):
        os.environ["HF_TOKEN"] = token
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        # Модель из HugginFace. Импортируем Qwen2.5. Мозг Агента
        model = HfApiModel(
            max_tokens=5000,
            temperature=0.5,
            model_id='Qwen/Qwen2.5-Coder-32B-Instruct',
            # model_id='Qwen/Qwen2.5-7B-Instruct',
            custom_role_conversions=None
        )

        # embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        final_answer = FinalAnswerTool()
        web_search = DuckDuckGoSearchTool()

        try:
            with open("agent/prompts.yaml", 'r') as stream:
                prompt_templates = yaml.safe_load(stream)
        except FileNotFoundError:
            prompt_templates = {}

        self.agent = ToolCallingAgent(
            model=model,
            tools=[final_answer,
                web_search,
                # get_current_time_in_timezone,
                search_arxiv,
                scrape_pubmed_pdfs],
            max_steps=7,
            verbosity_level=1,
            grammar=None,
            planning_interval=None,
            name="AndrewSolver",
            description=None,
            prompt_templates=prompt_templates
        )
        # self.agent.visualize()

    def run_agent(self, message: str) -> str:
        """
        Runs the agent with the given message and returns the result.
        """
        try:
            result = self.agent.run(message)
            logging.info("OK")
            return remove_markdown_symbols(result.replace("\\n", "\n"))
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            return f"Произошла ошибка. Повторите попытку чуть позже."

    def __del__(self):
        driver.quit()
