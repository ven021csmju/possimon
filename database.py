from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings
import ssl



db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine_args = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

if db_url.startswith("postgresql"):
    # Render and many cloud providers require SSL
    # Add connect_timeout to avoid hanging during handshake
    engine_args["connect_args"] = {
        "sslmode": "require",
        "connect_timeout": 10
    }

engine = create_engine(db_url, **engine_args)
SessionLocal = sessionmaker(bind=engine)

async_db_url = db_url
if async_db_url.startswith("postgresql://"):
    async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif async_db_url.startswith("sqlite:///"):
    async_db_url = async_db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

async_engine_args = {"pool_pre_ping": True}
if async_db_url.startswith("postgresql+asyncpg"):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async_engine_args["connect_args"] = {"ssl": ssl_context}

async_engine = create_async_engine(async_db_url, **async_engine_args)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

Base = declarative_base()


async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
