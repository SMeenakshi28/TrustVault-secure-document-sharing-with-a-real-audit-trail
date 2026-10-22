
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User

email = input("Enter the first test account's email: ").strip().lower()

with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == email))

    if not user:
        print("Account not found. Check the email and try again.")
    else:
        user.role = "owner"
        db.commit()
        print("Test account role updated to owner.")
