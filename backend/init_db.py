from .database import Base, engine
from . import models  # noqa: F401 - registers the Prediction table

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")
