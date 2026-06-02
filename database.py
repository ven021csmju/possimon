from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings



db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine_args = {}
if db_url.startswith("postgresql"):
    engine_args["pool_pre_ping"] = True
    # Render and many cloud providers require SSL
    engine_args["connect_args"] = {"sslmode": "require"}

engine = create_engine(db_url, **engine_args)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()