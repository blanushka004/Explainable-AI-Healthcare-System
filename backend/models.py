from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func

from .database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)

    age = Column(Integer)
    sex = Column(Integer)
    cp = Column(Integer)
    trestbps = Column(Integer)
    chol = Column(Integer)
    fbs = Column(Integer)
    restecg = Column(Integer)
    thalach = Column(Integer)
    exang = Column(Integer)
    oldpeak = Column(Float)
    slope = Column(Integer)
    ca = Column(Integer)
    thal = Column(Integer)

    prediction = Column(String)
    probability = Column(Float)
    risk_level = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
