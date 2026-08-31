from pydantic import BaseModel, ConfigDict
from datetime import datetime


class PredictionCreate(BaseModel):
    age: int
    sex: int
    cp: int
    trestbps: int
    chol: int
    fbs: int
    restecg: int
    thalach: int
    exang: int
    oldpeak: float
    slope: int
    ca: int
    thal: int

    prediction: str
    probability: float
    risk_level: str


class PredictionResponse(PredictionCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
