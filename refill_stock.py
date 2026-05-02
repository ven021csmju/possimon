import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def refill_stock():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Refilling stock for all products...")
        conn.execute(text("UPDATE products SET stock = 100;"))
        conn.commit()
        print("All products now have 100 stock.")

if __name__ == "__main__":
    refill_stock()
