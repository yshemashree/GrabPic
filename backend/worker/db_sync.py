from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

engine = create_engine(get_settings().sync_database_url, pool_pre_ping=True)
SyncSession = sessionmaker(engine, expire_on_commit=False)
