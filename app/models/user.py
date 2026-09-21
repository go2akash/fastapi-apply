import uuid
from sqlalchemy import String
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.config.database import Base


class Users(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        unique=True, primary_key=True, nullable=False, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(10))
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hash_password: Mapped[str] = mapped_column(String, nullable=False)

    address: Mapped["Address"] = relationship("Address", back_populates="user")
    chat_memory: Mapped[list["ChatMemory"]] = relationship(
        "ChatMemory", back_populates="user"
    )
