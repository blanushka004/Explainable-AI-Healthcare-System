import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.database import Base, get_db
from backend.main import app
from backend.models import User, Assessment, Prediction, SessionToken
from backend.auth import hash_password, _digest
from src.features import FEATURES

@pytest.fixture(scope="module")
def security_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def override():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[get_db] = override
    with Session(engine) as db:
        db.add(User(email="admin@example.test", display_name="Admin", password_hash=hash_password("Admin password 123!"), role="ADMIN"))
        db.commit()
    with TestClient(app) as client:
        client.test_engine = engine
        yield client
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.fixture
def patient():
    return {key: definition["default"] for key, definition in FEATURES.items()}

def login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()

def test_public_registration_normalizes_email_and_rejects_role(security_client):
    response = security_client.post("/api/auth/register", json={"email": " User@Example.Test ", "display_name": "User", "password": "User password 123!", "role": "ADMIN"})
    assert response.status_code == 400
    response = security_client.post("/api/auth/register", json={"email": " User@Example.Test ", "display_name": "User", "password": "User password 123!"})
    assert response.status_code == 200
    assert response.json()["role"] == "USER"
    assert "password" not in response.json()
    duplicate = security_client.post("/api/auth/register", json={"email": "user@example.test", "display_name": "Other", "password": "Other password 123!"})
    assert duplicate.status_code == 409

def test_anonymous_and_user_admin_boundaries(security_client):
    security_client.cookies.clear()
    assert security_client.get("/api/meta").status_code == 401
    assert security_client.get("/api/evaluation").status_code == 401
    login(security_client, "user@example.test", "User password 123!")
    assert security_client.get("/api/evaluation").status_code == 403
    assert security_client.get("/api/threshold").status_code == 403
    assert security_client.get("/api/global-shap").status_code == 403
    assert security_client.get("/api/versions").status_code == 403
    assert security_client.post("/api/predict", json={}).status_code == 403

def test_admin_can_read_evaluation_and_user_can_save_owned_record(security_client, patient):
    login(security_client, "admin@example.test", "Admin password 123!")
    assert security_client.get("/api/evaluation").status_code == 200
    security_client.post("/api/auth/logout", headers={"X-CSRF-Token": security_client.cookies.get("clarity_csrf")})
    login(security_client, "user@example.test", "User password 123!")
    response = security_client.post("/api/predict", json=patient, headers={"X-CSRF-Token": security_client.cookies.get("clarity_csrf")})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "model_comparison" not in body
    assert "model_version" not in body
    assert "recommendation_rule_version" not in body
    assert body["recommendations"]["status"] == "stored"
    assert body["recommendations"]["cards"]
    assert {"rule", "priority", "category"}.isdisjoint(body["recommendations"]["cards"][0])
    assert body["input_support"]["status"] == "available"
    assert body["input_support"]["flagged"] is False
    assert security_client.get("/api/history").json()["total"] == 1
    assert security_client.get(f"/api/history/{body['assessment_id']}").status_code == 200

def test_csrf_and_logout_revoke_session(security_client, patient):
    login(security_client, "user@example.test", "User password 123!")
    assert security_client.post("/api/predict", json=patient).status_code == 403
    token = security_client.cookies.get("clarity_csrf")
    response = security_client.post("/api/auth/logout", headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    assert security_client.get("/api/auth/me").status_code == 401

def test_assessment_ownership_returns_not_found_for_other_user(security_client, patient):
    login(security_client, "user@example.test", "User password 123!")
    token = security_client.cookies.get("clarity_csrf")
    saved = security_client.post("/api/predict", json=patient, headers={"X-CSRF-Token": token}).json()
    security_client.post("/api/auth/logout", headers={"X-CSRF-Token": security_client.cookies.get("clarity_csrf")})
    security_client.post("/api/auth/register", json={"email": "second@example.test", "display_name": "Second", "password": "Second password 123!"})
    assert security_client.get("/api/history").json()["total"] == 0
    assert security_client.get(f"/api/history/{saved['assessment_id']}").status_code == 404
    assert security_client.get(f"/predictions/{saved['prediction_id']}").status_code == 404

def test_all_admin_routes_reject_regular_users_and_anonymous(security_client, patient):
    security_client.cookies.clear()
    admin_routes = [
        ("/api/evaluation", "get", {}), ("/api/threshold", "get", {}),
        ("/api/global-shap", "get", {}), ("/api/versions", "get", {}),
        ("/admin/docs", "get", {}), ("/admin/openapi.json", "get", {}),
        ("/api/simulate", "post", {"json": {"original": patient, "modified": patient}}),
        ("/api/batch", "post", {"content": "not-a-valid-batch", "headers": {"Content-Type": "text/csv"}}),
    ]
    for path, method, kwargs in admin_routes:
        assert getattr(security_client, method)(path, **kwargs).status_code == 401
    login(security_client, "user@example.test", "User password 123!")
    for path, method, kwargs in admin_routes:
        assert getattr(security_client, method)(path, **kwargs).status_code == 403, path

def test_user_response_history_and_legacy_exports_are_restricted(security_client, patient):
    login(security_client, "user@example.test", "User password 123!")
    token = security_client.cookies.get("clarity_csrf")
    saved = security_client.post("/api/predict", json=patient, headers={"X-CSRF-Token": token}).json()
    forbidden = {"model_version", "selected_model", "model_comparison", "disagreement", "similar_cases", "training_distance_95"}
    assert forbidden.isdisjoint(saved)
    opened = security_client.get(f"/api/history/{saved['assessment_id']}").json()
    assert forbidden.isdisjoint(opened)
    assert forbidden.isdisjoint(security_client.get("/api/history").json()["items"][0])
    assert forbidden.isdisjoint(security_client.get(f"/predictions/{saved['prediction_id']}").json())
    assert forbidden.isdisjoint(saved)

def test_ownerless_records_remain_inaccessible(security_client):
    login(security_client, "user@example.test", "User password 123!")
    history_before = security_client.get("/api/history").json()["total"]
    legacy_before = len(security_client.get("/history").json())
    with Session(security_client.test_engine) as db:
        db.add(Prediction(age=54, sex=1, cp=2, trestbps=130, chol=233, fbs=0, restecg=1,
                          thalach=150, exang=0, oldpeak=1.0, slope=2, ca=0, thal=3,
                          prediction="Model negative", probability=0.2, risk_level="LOW"))
        db.add(Assessment(model_version="ownerless", probability=0.2, risk_level="LOW",
                          features={}, result={}))
        db.commit()
    assert security_client.get("/api/history").json()["total"] == history_before
    assert len(security_client.get("/history").json()) == legacy_before

def test_csrf_survives_reload_and_shared_tabs(security_client, patient):
    login_response = security_client.post("/api/auth/login", json={"email": "user@example.test", "password": "User password 123!"})
    token = login_response.json()["csrf_token"]
    assert security_client.get("/api/auth/csrf").json()["csrf_token"] == token
    assert security_client.get("/api/auth/csrf").json()["csrf_token"] == token
    response = security_client.post("/api/predict", json=patient, headers={"X-CSRF-Token": token})
    assert response.status_code == 200, response.text

def test_expired_and_inactive_sessions_are_rejected(security_client):
    login(security_client, "user@example.test", "User password 123!")
    cookie = security_client.cookies.get("clarity_session")
    with Session(security_client.test_engine) as db:
        session = db.query(SessionToken).filter_by(token_hash=_digest(cookie)).one()
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert security_client.get("/api/auth/me").status_code == 401
    security_client.cookies.clear()
    login(security_client, "user@example.test", "User password 123!")
    with Session(security_client.test_engine) as db:
        user = db.query(User).filter_by(email="user@example.test").one()
        user.is_active = False
        db.commit()
    assert security_client.get("/api/auth/me").status_code == 401

def test_csrf_seed_rebinds_a_missing_cookie_to_the_active_session(security_client, patient):
    registration = security_client.post("/api/auth/register", json={"email": "csrf@example.test", "display_name": "CSRF User", "password": "CSRF password 123!"})
    assert registration.status_code == 200, registration.text
    security_client.cookies.delete("clarity_csrf")
    seed = security_client.get("/api/auth/csrf")
    assert seed.status_code == 200
    token = seed.json()["csrf_token"]
    assert token == security_client.cookies.get("clarity_csrf")
    saved = security_client.post("/api/predict", json=patient, headers={"X-CSRF-Token": token})
    assert saved.status_code == 200, saved.text


def test_user_receives_its_own_complete_personal_shap_snapshot(security_client, patient):
    registration = security_client.post("/api/auth/register", json={"email": "personal@example.test", "display_name": "Personal User", "password": "Personal password 123!"})
    assert registration.status_code == 200, registration.text
    token = security_client.cookies.get("clarity_csrf")
    first = security_client.post("/api/predict", json=patient, headers={"X-CSRF-Token": token})
    assert first.status_code == 200, first.text
    first = first.json()
    changed = {**patient, "chol": 300, "oldpeak": 3.0}
    second = security_client.post("/api/predict", json=changed, headers={"X-CSRF-Token": token})
    assert second.status_code == 200, second.text
    second = second.json()

    forbidden_explanation_keys = {"method", "units", "reconstruction_error", "model_version"}
    for result, submitted in ((first, patient), (second, changed)):
        explanation = result["explanation"]
        assert explanation["status"] == "available"
        assert len(explanation["factors"]) == 13
        assert forbidden_explanation_keys.isdisjoint(explanation)
        assert abs(explanation["base_value"] + sum(f["shap_contribution"] for f in explanation["factors"]) - result["probability"]) < 1e-6
        assert result["features"] == submitted
        assert {factor["feature"]: factor["patient_value"] for factor in explanation["factors"]} == submitted
        reopened = security_client.get(f"/api/history/{result['assessment_id']}")
        assert reopened.status_code == 200
        assert reopened.json()["explanation"] == explanation
        assert forbidden_explanation_keys.isdisjoint(reopened.json())

    assert first["probability"] != second["probability"]
    assert first["explanation"]["factors"] != second["explanation"]["factors"]
