from transformers import MarianMTModel, MarianTokenizer

# Инициализируем модель, которая переводит с русского языка на английский
model_from_russian_to_english = "Helsinki-NLP/opus-mt-ru-en"
tokenizer_russian = MarianTokenizer.from_pretrained(model_from_russian_to_english)
model_russian = MarianMTModel.from_pretrained(model_from_russian_to_english)

# Инициализируем моедель, которая с английского переводит на русский
model_from_english_to_russian = "Helsinki-NLP/opus-mt-en-ru"
tokenizer_english = MarianTokenizer.from_pretrained(model_from_english_to_russian)
model_english = MarianMTModel.from_pretrained(model_from_english_to_russian)


def translate(text, tokenizer, model):
    """
    Функция для перевода с одного языка на другой.
    """
    tokenized_text = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    translated_tokens = model.generate(**tokenized_text)
    translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
    return translated_text
