from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import json

router = APIRouter(tags=["chat"])

class ChatMessage(BaseModel):
    message: str
    model: Optional[str] = "gpt-3.5-turbo"
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    model: str
    usage: dict = {}

@router.post("/message", response_model=ChatResponse)
async def chat_message(chat_msg: ChatMessage):
    # Placeholder implementation
    await asyncio.sleep(0.1)  # Simulate processing
    return ChatResponse(
        response=f"This is a placeholder response to: {chat_msg.message}",
        model=chat_msg.model,
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )

@router.get("/models")
async def get_models():
    return {
        "models": [
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
            {"id": "gpt-4", "name": "GPT-4"},
            {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet"}
        ]
    }

@router.get("/health")
async def chat_health():
    return {"status": "ok", "service": "chat"}