import asyncio
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
import unicodedata
import emoji

# Funkce pro odstranění emoji pomocí demojize a regex
def remove_emoji(text):
    '''
    Remove all emojis from the input text using the emoji library's replace_emoji function.
    '''
    demojized_text = emoji.demojize(text)
    clean_text = re.sub(r':[^:\s]+:', '', demojized_text)
    return clean_text

def normalize_unicode(text):
    '''
    Normalize Unicode characters in the input text to their canonical form.
    '''
    return unicodedata.normalize('NFKC', text)


def clean_response_sync(text: str):
    '''
    Clean the input text by removing HTML tags, URLs, emojis, unwanted characters, and expanding abbreviations.
    
    Args:
        text (str): The input text to be cleaned.
    
    Returns:
        str: The cleaned text.
    '''

    # Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    cleaned_text = soup.get_text()

    # Remove Markdown links [text](url)
    cleaned_text = re.sub(r'\[.*?\]\(.*?\)', '', cleaned_text)

    # Remove plain URLs (http, https, www)
    cleaned_text = re.sub(r'http\S+|www\.\S+', '', cleaned_text)

    # Remove text within any brackets (parentheses, curly braces, square brackets)
    cleaned_text = re.sub(r'\(.*?\)|\{.*?\}|\[.*?\]', '', cleaned_text)

    # Remove unwanted special characters but keep basic punctuation
    cleaned_text = re.sub(r'[^\w\s.,!?]', '', cleaned_text)

    cleaned_text = remove_emoji(cleaned_text)

    # Normalize Unicode characters
    cleaned_text = normalize_unicode(cleaned_text)

    # Remove unwanted special characters but keep basic punctuation
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # Replace multiple punctuation marks with single ones
    cleaned_text = re.sub(r'\.{2,}', '.', cleaned_text)
    cleaned_text = re.sub(r'\!{2,}', '!', cleaned_text)
    cleaned_text = re.sub(r'\?{2,}', '?', cleaned_text)

    abbreviations = {
        "např.": "například",
        "atd.": "a tak dále",
        "ap.": "aproximativně",
        "Kč" : "korun",
    }
    for abbr, full in abbreviations.items():
        cleaned_text = re.sub(r'\b' + re.escape(abbr) + r'\b', full, cleaned_text)

    return cleaned_text

# Asynchronní obal pro čištění odpovědi
async def clean_response_async(text):
    '''
        Asynchronously clean the input text by running the clean_response_sync function in a thread pool.
    '''
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, clean_response_sync, text)
