"""Export a full probability-space explanation. python -m src.explain examples/patient.json"""
import argparse
import json
from pathlib import Path
from backend.contracts import PatientInput
from backend.engine import InferenceEngine
from src.features import FEATURE_ORDER
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("input",type=Path);parser.add_argument("--output",type=Path,default=Path("reports/shap-explanation.json"));args=parser.parse_args()
    patient=PatientInput.model_validate(json.loads(args.input.read_text())).model_dump()
    result=InferenceEngine().explain(tuple(patient[k] for k in FEATURE_ORDER))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2))
    print("Saved",args.output)
