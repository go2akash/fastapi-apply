from time import timezone
import uuid
from sqlalchemy import Column, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base
import datetime


class ChatMemory(Base):
    __tablename__ = "chatmemory"
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, unique=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime.datetime] = mapped_column(default=func.now())

    user: Mapped["Users"] = relationship("Users", back_populates="chat_memory")
