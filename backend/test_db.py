"""Manual connectivity check: python -m backend.test_db"""
from sqlalchemy import text
from backend.database import engine
if __name__=="__main__":
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connection succeeded.")
