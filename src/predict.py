"""Predict a JSON record with the active version. python -m src.predict examples/patient.json"""
import argparse
import json
from pathlib import Path
from backend.contracts import PatientInput
from backend.engine import InferenceEngine
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("input",type=Path);args=parser.parse_args()
    patient=PatientInput.model_validate(json.loads(args.input.read_text()))
    print(json.dumps(InferenceEngine().assess(patient.model_dump()),indent=2,allow_nan=False))
