import logging
from database import engine, Base, SessionLocal
from seed import seed_data
import models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_db")

def reset_database():
    logger.info("⚠️ Dropping all tables...")
    try:
        # Drop all tables in reverse order of creation to handle foreign keys
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ All tables dropped successfully.")
        
        logger.info("🛠 Creating all tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables created successfully.")

        db = SessionLocal()
        try:
            logger.info("🌱 Seeding initial data...")
            seed_data(db)
            logger.info("✅ Database reset and seeded successfully!")
            logger.info("🔑 Test Users:")
            logger.info("   - Admin: admin / admin123")
            logger.info("   - Staff: cashier01 / cashier123")
            logger.info("   - Customer: john_doe / password123")
        except Exception as e:
            logger.error(f"❌ Error during seeding: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Critical error during database reset: {e}")

if __name__ == "__main__":
    reset_database()
