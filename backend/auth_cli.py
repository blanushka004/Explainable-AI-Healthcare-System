"""Create an administrator without putting credentials in source or logs."""
import getpass
from backend.database import Base, engine, SessionLocal
from backend import models
from backend.auth import hash_password, normalize_email

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    email = normalize_email(input("Admin email: "))
    display_name = input("Display name: ").strip()
    password = getpass.getpass("Admin password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not email or "@" not in email or not display_name:
        raise SystemExit("A valid email and display name are required.")
    if len(password) < 12 or password != confirmation:
        raise SystemExit("Passwords must match and contain at least 12 characters.")
    with SessionLocal() as db:
        if db.query(models.User).filter_by(email=email).first():
            raise SystemExit("That email is already registered.")
        db.add(models.User(email=email, display_name=display_name,
                           password_hash=hash_password(password), role="ADMIN", is_active=True))
        db.commit()
    print("Administrator account created.")
