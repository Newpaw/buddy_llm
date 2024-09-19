import asyncio
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
import unicodedata
import emoji
from urllib.parse import urlparse

# Function to remove emojis using demojize and regex
def remove_emoji(text):
    '''
    Remove all emojis from the input text using the emoji library's demojize function.
    '''
    demojized_text = emoji.demojize(text)
    clean_text = re.sub(r':[^:\s]+:', '', demojized_text)
    return clean_text

def normalize_unicode(text):
    '''
    Normalize Unicode characters in the input text to their canonical form.
    '''
    return unicodedata.normalize('NFKC', text)

def extract_domain(url):
    '''
    Extract the first and second level domain from a URL.
    
    Args:
        url (str): The URL to extract the domain from.
    
    Returns:
        str: The extracted domain (e.g., 'o2.cz').
    '''
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        if not hostname:
            # If the URL does not contain a scheme, try adding 'http://' and parse again
            parsed_url = urlparse('http://' + url)
            hostname = parsed_url.hostname
            if not hostname:
                return url  # If we still cannot get the hostname, return the original text

        parts = hostname.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])  # Getting the last two parts of the domain
        else:
            return hostname  # If the domain does not have enough parts, return it whole
    except Exception as e:
        # In case of an error, return the original text
        return url

def clean_response_sync(text: str):
    '''
    Clean the input text by removing HTML tags, URLs (replaced by their domains), emojis, unwanted characters, and expanding abbreviations.
    
    Args:
        text (str): The input text to be cleaned.
    
    Returns:
        str: The cleaned text.
    '''

    # 1. Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    cleaned_text = soup.get_text()

    # 2. Remove Markdown links [text](url) and keep only the text
    cleaned_text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'\1', cleaned_text)

    # 3. Remove brackets containing URLs, e.g., [https://o2.cz]
    # This step removes the entire content of the brackets if it contains a URL
    cleaned_text = re.sub(r'\[(https?://\S+|www\.\S+)\]', '', cleaned_text)

    # 4. Replace plain URLs (http, https, www) with their domains
    def replace_url_with_domain(match):
        url = match.group(0)
        domain = extract_domain(url)
        return domain

    url_pattern = re.compile(r'(https?://\S+|www\.\S+)')
    cleaned_text = url_pattern.sub(replace_url_with_domain, cleaned_text)

    # 5. Remove remaining brackets (parentheses, curly braces, square brackets)
    cleaned_text = re.sub(r'\(.*?\)|\{.*?\}|\[.*?\]', '', cleaned_text)

    # 6. Remove unwanted special characters, but keep basic punctuation
    cleaned_text = re.sub(r'[^\w\s.,!?]', '', cleaned_text)

    # 7. Remove emojis
    cleaned_text = remove_emoji(cleaned_text)

    # 8. Normalize Unicode characters
    cleaned_text = normalize_unicode(cleaned_text)

    # 9. Remove extra spaces and trim the text
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # 10. Replace multiple punctuation marks with a single one
    cleaned_text = re.sub(r'\.{2,}', '.', cleaned_text)
    cleaned_text = re.sub(r'\!{2,}', '!', cleaned_text)
    cleaned_text = re.sub(r'\?{2,}', '?', cleaned_text)

    # 11. Expand abbreviations
    abbreviations = {
        "např.": "například",
        "atd.": "a tak dále",
        "ap.": "aproximativně",
        "Kč" : "korun",
        "O2" : "ou two"  
    }
    for abbr, full in abbreviations.items():
        cleaned_text = re.sub(r'\b' + re.escape(abbr) + r'\b', full, cleaned_text)

    return cleaned_text

# Asynchronous wrapper for cleaning response
async def clean_response_async(text):
    '''
        Asynchronously clean the input text by running the clean_response_sync function in a thread pool.
    '''
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, clean_response_sync, text)

# Example usage
#if __name__ == "__main__":
#    sample_texts = [
#        "https://o2.cz",
#        "Navštivte naši stránku https://o2.cz pro více informací.",
#        "Zkontrolujte www.o2.cz a kontaktujte nás!",
#        "Toto je text bez URL.",
#        "Emojis 😊 a URL https://www.example.com/test?param=1",
#        "[https://o2.cz] ap.",
#        "Další URL: http://subdomain.example.co.uk/path",
#        "[www.example.com] atd.",
#        "Text před [https://o2.cz] a text za."
#    ]
#    
#    for sample_text in sample_texts:
#        cleaned = asyncio.run(clean_response_async(sample_text))
#        print(f"Původní text: '{sample_text}'")
#        print(f"Čistý text: '{cleaned}'\n")
