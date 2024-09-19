import asyncio
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
import unicodedata
import emoji
from urllib.parse import urlparse

# Funkce pro odstranění emoji pomocí demojize a regex
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
            # Pokud URL neobsahuje schéma, zkuste přidat 'http://' a znovu analyzovat
            parsed_url = urlparse('http://' + url)
            hostname = parsed_url.hostname
            if not hostname:
                return url  # Pokud stále nemůžeme získat hostname, vraťte původní text

        parts = hostname.split('.')
        if len(parts) >= 2:
            return '.'.join(parts[-2:])  # Získání posledních dvou částí domény
        else:
            return hostname  # Pokud doména nemá dostatek částí, vraťte ji celou
    except Exception as e:
        # V případě chyby vrátíme původní text
        return url

def clean_response_sync(text: str):
    '''
    Clean the input text by removing HTML tags, URLs (replaced by their domains), emojis, unwanted characters, and expanding abbreviations.
    
    Args:
        text (str): The input text to be cleaned.
    
    Returns:
        str: The cleaned text.
    '''

    # 1. Odstranění HTML tagů
    soup = BeautifulSoup(text, "html.parser")
    cleaned_text = soup.get_text()

    # 2. Odstranění Markdown odkazů [text](url) a zachování pouze textu
    cleaned_text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'\1', cleaned_text)

    # 3. Odstranění závorek obsahujících URL, např. [https://o2.cz]
    # Tento krok odstraní celé obsah závorek, pokud obsahuje URL
    cleaned_text = re.sub(r'\[(https?://\S+|www\.\S+)\]', '', cleaned_text)

    # 4. Nahrazení čistých URL (http, https, www) jejich doménami
    def replace_url_with_domain(match):
        url = match.group(0)
        domain = extract_domain(url)
        return domain

    url_pattern = re.compile(r'(https?://\S+|www\.\S+)')
    cleaned_text = url_pattern.sub(replace_url_with_domain, cleaned_text)

    # 5. Odstranění zbývajících závorek (parentheses, curly braces, square brackets)
    cleaned_text = re.sub(r'\(.*?\)|\{.*?\}|\[.*?\]', '', cleaned_text)

    # 6. Odstranění nežádoucích speciálních znaků, ale ponechání základní interpunkce
    cleaned_text = re.sub(r'[^\w\s.,!?]', '', cleaned_text)

    # 7. Odstranění emoji
    cleaned_text = remove_emoji(cleaned_text)

    # 8. Normalizace Unicode znaků
    cleaned_text = normalize_unicode(cleaned_text)

    # 9. Odstranění nadbytečných mezer a ořezání textu
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # 10. Nahrazení vícenásobných interpunkčních znamének jedním
    cleaned_text = re.sub(r'\.{2,}', '.', cleaned_text)
    cleaned_text = re.sub(r'\!{2,}', '!', cleaned_text)
    cleaned_text = re.sub(r'\?{2,}', '?', cleaned_text)

    # 11. Rozšíření zkratek
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

# Asynchronní obal pro čištění odpovědi
async def clean_response_async(text):
    '''
        Asynchronously clean the input text by running the clean_response_sync function in a thread pool.
    '''
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, clean_response_sync, text)

# Příklad použití
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
