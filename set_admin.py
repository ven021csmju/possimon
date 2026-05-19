from sqlalchemy.orm import Session
from database import SessionLocal
import models
import sys

def set_user_admin(email: str):
    db: Session = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"❌ Error: User with email '{email}' not found.")
            return

        user.role = "admin"
        db.commit()
        print(f"✅ Success: User '{email}' is now an 'admin'.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_admin.py <your_email>")
    else:
        email = sys.argv[1]
        set_user_admin(email)
