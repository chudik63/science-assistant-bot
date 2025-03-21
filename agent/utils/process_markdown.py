import markdown
from bs4 import BeautifulSoup

def remove_markdown_symbols(text):
    html = markdown.markdown(text)
    plain_text = BeautifulSoup(html, "html.parser").get_text()
    plain_text = plain_text.replace("\\", "\n")
    return plain_text