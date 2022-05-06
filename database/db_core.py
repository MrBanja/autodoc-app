from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from utils.config import get_config

Base = declarative_base()
Engine = create_async_engine(get_config().db.uri())
Session = sessionmaker(Engine, expire_on_commit=False, class_=AsyncSession)