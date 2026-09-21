from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config.settings import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url)

sessionLocal = sessionmaker(bind=engine)


def get_db():
    with sessionLocal() as session:
        yield session
