from backend.database import Base, engine, ensure_legacy_columns
from backend import models
if __name__ == "__main__":
    Base.metadata.create_all(engine)
    ensure_legacy_columns()
    print("Database tables are ready. Existing records were retained.")
