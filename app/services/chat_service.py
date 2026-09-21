from fastapi import Depends
from starlette.routing import Host
from app.config.database import get_db
from app.config.settings import settings
from openai import OpenAI
from sqlalchemy.orm import Session
from app.models.chat_memory import ChatMemory
import uuid

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api,
)


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def chat_response(self, user_message: str) -> str:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": user_message}],
        )
        return response.choices[0].message.content

    def _save_chat_message(self, user_id: uuid.UUID, role: str, content: str):
        new_msg = ChatMemory(user_id=user_id, role=role, content=content)
        self.db.add(new_msg)
        self.db.commit()
        return new_msg

    def stream_chat_response(self, user_id: uuid.UUID, user_message: str):
        history = (
            self.db.query(ChatMemory)
            .filter(ChatMemory.user_id == user_id)
            .order_by(ChatMemory.created_at.desc())
            .limit(10)
            .all()
        )
        history.reverse()

        formated_msg = []

        for msg in history:
            formated_msg.append({"role": msg.role, "content": msg.content})

        formated_msg.append({"role": "user", "content": user_message})

        self._save_chat_message(user_id=user_id, role="user", content=user_message)

        stream_response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=formated_msg,
            stream=True,
        )
        collected_tokens = []
        for chunk in stream_response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                collected_tokens.append(token)
                yield token
        full_response = "".join(collected_tokens)
        self._save_chat_message(
            user_id=user_id, role="assistant", content=full_response
        )

    def get_chat_history(self, user_id: uuid.UUID, limit: int, offset: int):
        chat_history = (
            self.db.query(ChatMemory)
            .filter(ChatMemory.user_id == user_id)
            .order_by(ChatMemory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return chat_history.all()
