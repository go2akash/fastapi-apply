import uuid
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class Address(Base):
    __tablename__ = "address"
    id: Mapped[uuid.UUID] = mapped_column(
        unique=True, nullable=False, primary_key=True, default=uuid.uuid4
    )
    city: Mapped[str] = mapped_column(String(30))
    street_name: Mapped[str] = mapped_column(String(30))
    district: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(30))
    """ 
    inside ForeignKey parameter it always be the database table name 
    as ForeignKey create the database relationship
    and
    then used dot to access rest of the stuff
    """
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    """
        Mapped["Users"] -> Python db table class (responsible for mapping python 
        object relationship)

        relationship("Users") =>This tells SQLAlchemy:
        This relationship points to the 
        mapped class whose name is Users.

        back_populates="address"{this is the file name} -> Python attribute (responsible for creating 
        bidirectional connection between two classes) the "address" is the relationship attribute
        have to match both way same name what you denote as relationship attribute
        """
    # user: this user is relationship attribute have have to match same name on other table
    user: Mapped["Users"] = relationship("Users", back_populates="address")
