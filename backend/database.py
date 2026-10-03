"""SQLite quick start; set DATABASE_URL for PostgreSQL."""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/".env")
DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///"+str(ROOT/"healthcare.db"))
engine=create_engine(DATABASE_URL,pool_pre_ping=True,
    connect_args={"check_same_thread":False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal=sessionmaker(bind=engine,autoflush=False)
Base=declarative_base()
def get_db():
    with SessionLocal() as db: yield db

def ensure_legacy_columns():
    """Add nullable ownership columns without rewriting existing SQLite or PostgreSQL data."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    with engine.begin() as connection:
        if "predictions" in tables and "user_id" not in {c["name"] for c in inspector.get_columns("predictions")}:
            connection.execute(text("ALTER TABLE predictions ADD COLUMN user_id INTEGER"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_predictions_user_id ON predictions (user_id)"))
        if "assessments_v2" in tables and "user_id" not in {c["name"] for c in inspector.get_columns("assessments_v2")}:
            connection.execute(text("ALTER TABLE assessments_v2 ADD COLUMN user_id INTEGER"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_assessments_v2_user_id ON assessments_v2 (user_id)"))
