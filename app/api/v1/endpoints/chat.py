from fastapi import APIRouter, Depends, responses
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import Users
from app.services.chat_service import ChatService
from fastapi.responses import StreamingResponse

router = APIRouter()


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


@router.get("/chat")
def chat(
    message: str = "hello who are you?",
    service: ChatService = Depends(get_chat_service),
):
    response = service.chat_response(message)
    return {"response": response}


@router.get("/chat/stream")
def chat_stream(
    message: str = "what's your name",
    service: ChatService = Depends(get_chat_service),
    current_user: Users = Depends(get_current_user),
):
    return StreamingResponse(
        service.stream_chat_response(user_id=current_user.id, user_message=message),
        media_type="text/plain",
    )


@router.get("/chat/history")
def chat_history(
    limit: int = 10,
    offset: int = 0,
    service: ChatService = Depends(get_chat_service),
    current_user: Users = Depends(get_current_user),
):
    return service.get_chat_history(user_id=current_user.id, limit=limit, offset=offset)
