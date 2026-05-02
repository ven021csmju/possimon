import os
from sqlalchemy import create_engine, text
from database import Base, SessionLocal
from seed import seed_data
import models # Ensure models are registered

def migrate():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("Dropping existing products and wines tables for clean inheritance setup...")
        # Drop dependent tables first
        conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS ratings CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS wine_grapes CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS wines CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS products CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS orders CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS addresses CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS payments CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS regions CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS countries CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS wineries CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS grapes CASCADE;"))
        conn.commit()
        print("Tables dropped.")

    print("Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    print("Seeding new data...")
    db = SessionLocal()
    try:
        seed_data(db)
        print("Data seeded successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

if __name__ == "__main__":
    migrate()
