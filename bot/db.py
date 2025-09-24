from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings

# Создаём движок и фабрику сессий
engine = create_async_engine(settings.db_dsn, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Базовый класс для моделей
class Base(DeclarativeBase):
    pass


# Генератор сессий
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

# Ссылка на функцию для удобного импорта
async_session = get_session
