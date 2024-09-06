import httpx
import json
import logging
import aioredis
from core.config import settings


# Configure the logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BuddyClient:
    def __init__(self, api_url, api_key, client_name, redis_url=settings.REDIS_URL):
        self.api_url = api_url
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.client_name = client_name
        self.redis = aioredis.from_url(redis_url, decode_responses=True, socket_connect_timeout=20, socket_timeout=20)

    async def start_conversation(self, conversation_id):
        """Initialize a new conversation."""
        try:
            if await self.redis.exists(conversation_id):
                logger.warning(f"Conversation {conversation_id} already exists.")
            await self.redis.set(conversation_id, json.dumps([]))
            logger.info(f"Conversation {conversation_id} started.")
        except Exception as e:
            logger.error(f"Failed to start conversation {conversation_id}: {e}")
            raise

    async def add_message(self, conversation_id, user_message, bot_message=None):
        """Add a message to the conversation history."""
        try:
            if not await self.redis.exists(conversation_id):
                logger.error(f"Conversation {conversation_id} not found.")
                raise ValueError("Conversation not found. Please start a conversation first.")
            
            history = json.loads(await self.redis.get(conversation_id))
            history.append({"user": user_message, "bot": bot_message})
            await self.redis.set(conversation_id, json.dumps(history))
            logger.debug(f"Added message to history: {user_message}, {bot_message}")
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            raise

    async def call_chat_api(self, conversation_id, overrides=None):
        """Send the conversation history to the API and receive a response asynchronously."""
        if not await self.redis.exists(conversation_id):
            logger.error(f"Conversation {conversation_id} not found.")
            raise ValueError("Conversation not started. Please start a conversation first.")

        history = json.loads(await self.redis.get(conversation_id))

        data = {
            "id": conversation_id,
            "client": self.client_name,
            "history": history,
            "overrides": overrides or {}
        }

        serialized_data = json.dumps(data, separators=(',', ':'), ensure_ascii=False)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.api_url, headers=self.headers, data=serialized_data)
                response.raise_for_status()
                logger.info("API call successful.")
                return response.json()
            except httpx.HTTPStatusError as http_err:
                error_content = response.text if response.content else "No content"
                logger.error(f"HTTP error occurred: {http_err}, Content: {error_content}")
                raise RuntimeError(f"HTTP error occurred: {http_err}, Content: {error_content}")
            except httpx.RequestError as req_err:
                logger.error(f"Request error occurred: {req_err}")
                raise RuntimeError(f"Request error occurred: {req_err}")
            except Exception as err:
                logger.error(f"An error occurred: {err}")
                raise RuntimeError(f"An error occurred: {err}")
