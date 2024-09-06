from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import uuid
from depedencies.common import get_buddy_service
from core.config import settings
from services.text_cleaner import clean_response_async


# Initialize FastAPI
app = FastAPI()


class Conversation(BaseModel):
    conversation_id: str


class Message(BaseModel):
    user_message: str

class BotResponse(BaseModel):
    bot_reply: str

# Dependency for verifying API Key
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")


@app.get("/")
async def root():
    return {"message": "Pho, bo!"}


@app.post("/start_conversation", response_model=Conversation, dependencies=[Depends(verify_api_key)])
async def start_conversation():
    conversation_id = str(uuid.uuid4())  # Generate a unique conversation ID
    await get_buddy_service().start_conversation(conversation_id)
    return {"conversation_id": conversation_id}

@app.post("/send_message/{conversation_id}", response_model=BotResponse, dependencies=[Depends(verify_api_key)])
async def send_message(conversation_id: str, message: Message):
    try:
        # Add user message to history
        await get_buddy_service().add_message(conversation_id, message.user_message)
        
        # Call the chat API and get bot response
        response = await get_buddy_service().call_chat_api(conversation_id)
        bot_reply = response.get('text', 'No response')
        cleared_bot_reply = await clean_response_async(bot_reply)
        
        # Add bot response to history
        await get_buddy_service().add_message(conversation_id, message.user_message, cleared_bot_reply)
        
        return {"bot_reply": cleared_bot_reply}
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
