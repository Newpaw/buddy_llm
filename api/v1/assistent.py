from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import uuid
from typing import List
from depedencies.common import get_buddy_service
from core.config import settings
from services.text_cleaner import clean_response_async
from services.buddy_service import BuddyClient
import logging

# Initialize FastAPI
app = FastAPI()

# Setup logging
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

class Conversation(BaseModel):
    conversation_id: str

class Message(BaseModel):
    user_message: str

class BotResponse(BaseModel):
    bot_reply: str

class MessageItem(BaseModel):
    sender: str  # 'user' nebo 'bot'
    message: str

class ConversationItem(BaseModel):
    conversation_id: str
    messages: List[MessageItem]

class ConversationsResponse(BaseModel):
    conversations: List[ConversationItem]

class MessagesResponse(BaseModel):
    conversation_id: str
    messages: List[MessageItem]

# Dependency for verifying API Key
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

@app.get("/")
async def root():
    return {"message": "Pho, bo!"}

@app.post("/start_conversation", response_model=Conversation, dependencies=[Depends(verify_api_key)])
async def start_conversation(buddy_client: BuddyClient = Depends(get_buddy_service)):
    conversation_id = str(uuid.uuid4())  # Generate a unique conversation ID
    await buddy_client.start_conversation(conversation_id)
    return {"conversation_id": conversation_id}

@app.post("/send_message/{conversation_id}", response_model=BotResponse, dependencies=[Depends(verify_api_key)])
async def send_message(conversation_id: str, message: Message, buddy_client: BuddyClient = Depends(get_buddy_service)):
    try:
        # Add user message to history
        await buddy_client.add_message(conversation_id, "user", message.user_message)
        
        # Call the chat API and get bot response
        response: dict = await buddy_client.call_chat_api(conversation_id)
        bot_reply = response.get('text', 'No response')
        cleared_bot_reply = await clean_response_async(bot_reply)
        
        # Add bot response to history
        await buddy_client.add_message(conversation_id, "bot", cleared_bot_reply)
        
        return {"bot_reply": cleared_bot_reply}
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))

# Nový endpoint pro získání všech konverzací a jejich zpráv
@app.get("/conversations", response_model=ConversationsResponse, dependencies=[Depends(verify_api_key)])
async def get_all_conversations(buddy_client: BuddyClient = Depends(get_buddy_service)):
    try:
        conversations = await buddy_client.get_all_conversations()
        conversations_response = []
        for conv in conversations:
            messages = conv.get('messages', [])
            message_items = []
            for msg in messages:
                user_message = msg.get('user')
                bot_message = msg.get('bot')
                if user_message:
                    message_items.append(MessageItem(sender='user', message=user_message))
                if bot_message:
                    message_items.append(MessageItem(sender='bot', message=bot_message))
            conversations_response.append(ConversationItem(conversation_id=conv['conversation_id'], messages=message_items))
        return {"conversations": conversations_response}
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))

# Nový endpoint pro získání zpráv pro konkrétní konverzaci
@app.get("/conversation/{conversation_id}/messages", response_model=MessagesResponse, dependencies=[Depends(verify_api_key)])
async def get_conversation_messages(conversation_id: str, buddy_client: BuddyClient = Depends(get_buddy_service)):
    try:
        # Ověření existence konverzace
        conversation_exists = await buddy_client.check_conversation_exists(conversation_id)
        if not conversation_exists:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = await buddy_client.get_messages(conversation_id)
        message_items = []
        for msg in messages:
            user_message = msg.get('user')
            bot_message = msg.get('bot')
            if user_message:
                message_items.append(MessageItem(sender='user', message=user_message))
            if bot_message:
                message_items.append(MessageItem(sender='bot', message=bot_message))
        return {"conversation_id": conversation_id, "messages": message_items}
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
