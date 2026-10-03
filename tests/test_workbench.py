import csv
import io
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.database import Base,get_db
from backend.models import Assessment,Prediction,User
from backend.auth import hash_password
from src.features import FEATURES,FEATURE_ORDER
from src.metrics import metrics

@pytest.fixture(scope="module")
def client():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(email="workbench-admin@example.test", display_name="Workbench Admin",
                         password_hash=hash_password("Workbench password 123!"), role="ADMIN"))
        session.commit()
    def override():
        with Session(engine) as session: yield session
    app.dependency_overrides[get_db]=override
    with TestClient(app) as raw_client:
        login_response=raw_client.post("/api/auth/login", json={"email":"workbench-admin@example.test","password":"Workbench password 123!"})
        assert login_response.status_code == 200, login_response.text
        assert raw_client.get("/api/auth/me").json()["role"] == "ADMIN"
        class AuthenticatedClient:
            def __init__(self, wrapped): self.wrapped=wrapped
            def post(self, path, *args, **kwargs):
                headers=dict(kwargs.get("headers") or {})
                headers.setdefault("X-CSRF-Token", self.wrapped.cookies.get("clarity_csrf"))
                kwargs["headers"]=headers
                return self.wrapped.post(path, *args, **kwargs)
            def __getattr__(self, name): return getattr(self.wrapped, name)
        yield AuthenticatedClient(raw_client)
    app.dependency_overrides.clear();engine.dispose()

@pytest.fixture
def patient(): return {k:v["default"] for k,v in FEATURES.items()}

def test_health_and_ui(client):
    assert client.get("/health").json()["status"]=="ok"
    assert "Evidence, made visible" in client.get("/").text
    assert client.get("/static/script.js").status_code==200
    assert client.get("/api/meta").json()["feature_order"]==FEATURE_ORDER

@pytest.mark.parametrize("field,value",[("age",17),("age",54.5),("cp",0),("thal",4),("ca",4),("fbs",2),("chol",0),("oldpeak",-1),("sex",None),("chol",""),("oldpeak","NaN")])
def test_invalid_inputs_not_saved(client,patient,field,value):
    total=client.get("/api/history").json()["total"]
    patient[field]=value
    assert client.post("/api/predict",json=patient).status_code==422
    assert client.get("/api/history").json()["total"]==total

def test_extra_field_rejected(client,patient):
    assert client.post("/api/predict",json={**patient,"target":1}).status_code==422

def test_prediction_explanation_persistence(client,patient):
    response=client.post("/api/predict",json=patient)
    assert response.status_code==200,response.text
    result=response.json();e=result["explanation"]
    assert e["status"]=="available"
    assert len(e["factors"])==13
    assert abs(e["base_value"]+sum(f["shap_contribution"] for f in e["factors"])-result["probability"])<1e-6
    assert 0<=result["probability"]<=1
    assert len(result["model_comparison"])==3
    saved=client.get(f"/api/history/{result['assessment_id']}").json()
    assert saved["explanation"]==e
    assert saved["features"]==patient
    assert saved["model_version"]==result["model_version"]
    assert client.get(f"/predictions/{result['prediction_id']}").status_code==200
    assert client.get("/api/history/999999").status_code==404

def test_split_and_training_only_reference(client):
    b=app.state.ml.bundle
    assert not set(b["train_ids"])&set(b["test_ids"])
    assert len(b["train_ids"])+len(b["test_ids"])==b["report"]["dataset"]["rows"]
    for _,row in b["background"].iterrows(): assert (b["train_X"]==row).all(axis=1).any()
    assert len(b["oof_y"])==len(b["train_ids"])
    winner=max(b["report"]["candidates"],key=lambda k:b["report"]["candidates"][k]["cv_roc_auc_mean"])
    assert b["report"]["selected_model"]==winner

def test_report_reconstructs_test_metrics(client):
    report=client.get("/api/evaluation").json()
    cases=report["test_cases"]
    actual=metrics([c["actual"] for c in cases],[c["probability"] for c in cases])
    assert actual==report["active_test"]
    assert sum(map(sum,actual["confusion_matrix"]))==60
    assert report["test_intervals"]["roc_auc"]["low"]<=actual["roc_auc"]<=report["test_intervals"]["roc_auc"]["high"]

def test_threshold_is_oof_and_does_not_change_model(client,patient):
    model=app.state.ml
    before=float(model.probability(model.frame(patient))[0])
    low=client.get("/api/threshold?value=0.1").json()
    high=client.get("/api/threshold?value=0.9").json()
    assert low["metrics"]["n"]==len(model.training)
    assert low["metrics"]["recall"]>=high["metrics"]["recall"]
    assert low["metrics"]["specificity"]<=high["metrics"]["specificity"]
    assert before==float(model.probability(model.frame(patient))[0])
    assert client.get("/api/threshold?value=1.5").status_code==422

def test_simulation_unsaved_and_immutable_categories(client,patient):
    total=client.get("/api/history").json()["total"]
    same=client.post("/api/simulate",json={"original":patient,"modified":patient}).json()
    assert abs(same["delta_pp"])<1e-8 and same["saved"] is False
    changed={**patient,"chol":300}
    response=client.post("/api/simulate",json={"original":patient,"modified":changed})
    assert response.status_code==200
    assert response.json()["changed_features"]==["chol"]
    assert client.get("/api/history").json()["total"]==total
    assert client.post("/api/simulate",json={"original":patient,"modified":{**patient,"age":70}}).status_code==422

def csv_body(rows):
    f=io.StringIO();writer=csv.DictWriter(f,fieldnames=FEATURE_ORDER);writer.writeheader();writer.writerows(rows);return f.getvalue()

def test_batch_row_errors_and_no_persistence(client,patient):
    total=client.get("/api/history").json()["total"]
    response=client.post("/api/batch",content=csv_body([patient,{**patient,"thal":4}]),headers={"Content-Type":"text/csv"})
    assert response.status_code==200,response.text
    d=response.json();assert d["count"]==2 and d["valid"]==1
    assert d["results"][0]["status"]=="ok" and d["results"][1]["status"]=="invalid"
    assert d["results"][1]["errors"][0]["field"]=="thal"
    assert client.get("/api/history").json()["total"]==total
    expected=float(app.state.ml.probability(app.state.ml.frame(patient))[0])
    assert abs(d["results"][0]["probability"]-expected)<1e-10

def test_batch_limits(client,patient):
    assert client.post("/api/batch",content="age,age\n54,54").status_code==422
    assert client.post("/api/batch",content=",".join(FEATURE_ORDER)).status_code==422
    assert client.post("/api/batch",content=csv_body([patient]*251)).status_code==413
    assert client.post("/api/batch",content="a"*1000001).status_code==413
    assert client.post("/api/batch",content=b"\xff").status_code==422

def test_input_support_and_training_neighbors(client,patient):
    result=app.state.ml.assess({**patient,"chol":600},explain=False)
    assert result["input_support"]["flagged"]
    assert "chol" in [x["feature"] for x in result["input_support"]["outside_training_range"]]
    for case in result["similar_cases"]:
        frame=app.state.ml.training
        assert (frame==pd.Series(case["features"])).all(axis=1).any()

def test_global_shap_and_versions(client):
    response=client.get("/api/global-shap")
    assert response.status_code==200,response.text
    d=response.json();assert d["n"]==24 and len(d["factors"])==13
    assert all(f["mean_absolute_contribution"]>=0 for f in d["factors"])
    versions=client.get("/api/versions").json()
    assert versions["active"] in [v["version"] for v in versions["versions"]]

def test_history_filter(client):
    for band in ["LOW","MEDIUM","HIGH"]:
        d=client.get("/api/history",params={"band":band}).json()
        assert all(x["risk_level"]==band for x in d["items"])
    assert client.get("/api/history?band=BAD").status_code==422


def test_boolean_category_rejected(client,patient):
    assert client.post('/api/predict',json={**patient,'sex':True}).status_code==422


def test_failed_save_rolls_back_both_tables(client,patient,monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    before=client.get('/api/history').json()['total']
    legacy_before=len(client.get('/history').json())
    def fail_commit(self): raise SQLAlchemyError('Simulated commit failure')
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',fail_commit)
        response=client.post('/api/predict',json=patient)
        assert response.status_code==503
    assert client.get('/api/history').json()['total']==before
    assert len(client.get('/history').json())==legacy_before

def test_shap_failure_keeps_prediction_and_persists_explicit_unavailable_state(client, patient, monkeypatch):
    model = app.state.ml
    def fail_explanation(*_args, **_kwargs):
        raise RuntimeError("simulated SHAP failure")
    monkeypatch.setattr(model, "explain", fail_explanation)
    response = client.post("/api/predict", json=patient)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["explanation"]["status"] == "unavailable"
    assert result["explanation"]["factors"] == []
    assert "temporarily unavailable" in result["explanation"]["note"].lower()
    reopened = client.get(f"/api/history/{result['assessment_id']}")
    assert reopened.status_code == 200
    assert reopened.json()["explanation"] == result["explanation"]


def test_support_preprocessing_is_the_active_prediction_pipeline(client):
    model = app.state.ml
    assert model.preprocessor is model.model.named_steps["preprocess"]

def test_documented_score_band_boundaries_and_independent_measurement_check(client, patient):
    model = app.state.ml
    assert model.risk_level(0.0) == "LOW"
    assert model.risk_level(0.299999) == "LOW"
    assert model.risk_level(0.3) == "MEDIUM"
    assert model.risk_level(0.699999) == "MEDIUM"
    assert model.risk_level(0.7) == "HIGH"

    high_supported = {**patient, "cp": 4, "exang": 1, "oldpeak": 4.0, "ca": 3, "thal": 7, "chol": 300}
    high = model.assess(high_supported, explain=False)
    assert high["risk_level"] == "HIGH"
    assert high["input_support"]["status"] == "available"
    assert high["input_support"]["flagged"] is False

    low_unusual = {**patient, "age": 18, "trestbps": 70, "chol": 600, "thalach": 250, "oldpeak": 0.0, "cp": 1, "ca": 0, "thal": 3}
    low = model.assess(low_unusual, explain=False)
    assert low["risk_level"] == "LOW"
    assert low["input_support"]["status"] == "available"
    assert low["input_support"]["flagged"] is True

def test_saved_recommendations_are_deterministic_and_not_shap_driven(client, patient):
    model = app.state.ml
    input_data = {**patient, "trestbps": 130, "chol": 240, "fbs": 1}
    result = model.assess(input_data, explain=False)
    assert result["recommendation_rule_version"] == "guidance-2026-09-09-v1"
    cards = result["recommendations"]
    assert [card["title"] for card in cards] == [
        "Review your report", "Discuss your blood pressure", "Discuss your cholesterol results"
    ]
    assert all("SHAP" not in " ".join(card.values()) for card in cards)
    assert all("medication" not in " ".join(card.values()).lower() for card in cards)

    response = client.post("/api/predict", json=input_data)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved["recommendations"] == cards
    reopened = client.get(f"/api/history/{saved['assessment_id']}")
    assert reopened.status_code == 200
    assert reopened.json()["recommendations"] == cards

    from backend.main import user_result
    safe = user_result(result, 1, 1, "2026-09-09T00:00:00+00:00")
    assert safe["recommendations"] == {
        "status": "stored",
        "cards": [{key: card[key] for key in ("title", "explanation", "next_step")} for card in cards],
    }


def test_legacy_support_snapshot_with_explicit_boolean_is_not_unavailable(client, patient):
    from backend.main import user_result
    result = app.state.ml.assess(patient, explain=False)
    del result["input_support"]["status"]
    safe = user_result(result, 1, 1, "2026-09-09T00:00:00+00:00")
    assert safe["input_support"]["status"] == "available"
    assert safe["input_support"]["flagged"] is False

def test_user_renderer_uses_one_complete_waterfall_without_duplicates():
    script = (Path(__file__).parents[1] / "frontend" / "script.js").read_text(encoding="utf-8")
    start = script.index("function renderUserAssessment(data){")
    end = script.index("function renderAdminAssessment(data){", start)
    user_renderer = script[start:end]
    assert user_renderer.count("waterfall(explanation,{reference:\"Starting score\",final:\"Assessment score\",user:true,values:data.features})") == 1
    assert "contributionChart(" not in user_renderer
    assert "influenceGroups(" not in user_renderer
    assert "Show all 13 factors" not in user_renderer
    assert "recommendationCards(data.recommendations)" in user_renderer
    assert "Download report" in user_renderer
    assert "Edit measurements" not in user_renderer
