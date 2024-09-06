import asyncio
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor

# Function to clean the bot's response synchronously
def clean_response_sync(text:str):
    # Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    cleaned_text = soup.get_text()

    # Remove Markdown links [text](url)
    cleaned_text = re.sub(r'\[.*?\]\(.*?\)', '', cleaned_text)

    # Optional: Remove extra whitespace
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return cleaned_text

# Asynchronous wrapper for cleaning response
async def clean_response_async(text):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, clean_response_sync, text)
