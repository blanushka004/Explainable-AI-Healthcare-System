"""Compatibility interface. New endpoints share app.state.ml instead."""
from functools import lru_cache
from backend.engine import InferenceEngine
from src.features import FEATURE_ORDER as REQUIRED_FEATURE_ORDER
@lru_cache(maxsize=1)
def get_engine(): return InferenceEngine()
def predict_patient(patient_data): return get_engine().assess(patient_data)
