import httpx
import json
import logging
import aioredis
from core.config import settings
from typing import List

log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

logging.basicConfig(level=log_level)
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
                logger.debug(f"Calling API with data: {serialized_data}")
                logger.debug(f"API URL: {self.api_url} and headers: {self.headers}")
                response = await client.post(self.api_url, headers=self.headers, data=serialized_data)
                response.raise_for_status()
                logger.info(f"API call with conversation {conversation_id} successful.")
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
            
    async def get_all_conversations(self) -> List[dict]:
        """Retrieve all conversations and their messages."""
        try:
            conversations = []
            # Použijeme SCAN pro iteraci přes všechny klíče v Redis
            async for key in self.redis.scan_iter(match='*'):
                try:
                    messages_json = await self.redis.get(key)
                    if messages_json is not None:
                        messages = json.loads(messages_json)
                        # Ověříme, zda se jedná o seznam zpráv
                        if isinstance(messages, list):
                            conversations.append({
                                "conversation_id": key,
                                "messages": messages
                            })
                        else:
                            logger.warning(f"Data for key {key} není seznam zpráv.")
                    else:
                        logger.warning(f"Key {key} neobsahuje žádná data.")
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON for conversation {key}.")
                except Exception as e:
                    logger.error(f"Error retrieving conversation {key}: {e}")
            logger.info(f"Retrieved {len(conversations)} conversations.")
            return conversations
        except Exception as e:
            logger.error(f"Failed to retrieve all conversations: {e}")
            raise RuntimeError(f"Failed to retrieve all conversations: {e}")
        
    async def get_messages(self, conversation_id: str) -> List[dict]:
        """Get all messages for a specific conversation."""
        try:
            messages_json = await self.redis.get(conversation_id)
            if messages_json:
                messages = json.loads(messages_json)
                return messages
            else:
                logger.warning(f"No messages found for conversation {conversation_id}.")
                return []
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            raise

    async def check_conversation_exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists."""
        exists = await self.redis.exists(conversation_id)
        return exists == 1