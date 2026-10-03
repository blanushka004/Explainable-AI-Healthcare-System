"""Compatibility helpers; contributions use probability units for every model."""
import numpy as np
from .prediction import get_engine, REQUIRED_FEATURE_ORDER

def get_shap_contributions(patient_data):
    e=get_engine().explain(tuple(patient_data.iloc[0][k] for k in REQUIRED_FEATURE_ORDER))
    return np.array([f["shap_contribution"] for f in e["factors"]])

def get_risk_factors(patient_data,contributions):
    factors=[{"feature":k,"patient_value":float(patient_data.iloc[0][k]),"shap_contribution":float(v)} for k,v in zip(REQUIRED_FEATURE_ORDER,contributions)]
    return sorted([f for f in factors if f["shap_contribution"]>0],key=lambda f:-f["shap_contribution"]),sorted([f for f in factors if f["shap_contribution"]<0],key=lambda f:f["shap_contribution"])
