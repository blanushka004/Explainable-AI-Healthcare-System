"""Local single-user ML research workbench. Start with python -m uvicorn backend.main:app."""
import csv
import hmac
import io
import json
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from .database import Base, engine, get_db, ensure_legacy_columns
from .models import Prediction, Assessment, User, SessionToken
from .contracts import PatientInput, SimulationInput, RegisterInput, LoginInput
from .auth import (AdminUser, CurrentUser, CSRF, clear_auth_cookies, clear_login_failures,
                   create_session, csrf_protect, current_user, hash_password, login_allowed,
                   no_store, normalize_email, note_login_failure, set_auth_cookies,
                   verify_password, SESSION_COOKIE, SESSION_DAYS, _digest)
from .engine import InferenceEngine, DISCLAIMER
from src.features import FEATURE_ORDER, FEATURES, NUMERIC
from src.metrics import metrics

ROOT=Path(__file__).resolve().parents[1]
logger=logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    ensure_legacy_columns()
    try:
        app.state.ml=InferenceEngine();app.state.model_error=None
    except Exception:
        logger.exception("Model initialization failed")
        app.state.ml=None;app.state.model_error="Model unavailable. Run python -m src.train_model, then restart the server."
    yield

app=FastAPI(title="Explainable Healthcare Â· ML Workbench",version="3.0.0",lifespan=lifespan,
            docs_url=None, redoc_url=None, openapi_url=None)

# Same-origin frontend removes the previous hardcoded API URL and null-origin CORS.
app.mount("/static",StaticFiles(directory=ROOT/"frontend"),name="static")
@app.get("/",include_in_schema=False)
def index(): return FileResponse(ROOT/"frontend/index.html")

@app.get("/api/auth/csrf")
def csrf_seed(request: Request, response: Response, session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE), db: Session = Depends(get_db)):
    """Issue a CSRF token bound to the active session when one exists.

    A browser can retain a session cookie while losing or replacing its readable
    CSRF cookie. In that case the old implementation issued an unbound random
    token, so the next legitimate assessment was rejected. Rotate only the
    session-bound CSRF secret; never rotate a valid token on an ordinary reload.
    """
    token = request.cookies.get("clarity_csrf")
    if session_cookie:
        record = db.scalar(select(SessionToken).where(SessionToken.token_hash == _digest(session_cookie)))
        if record is not None and record.revoked_at is None:
            if not token or not hmac.compare_digest(record.csrf_hash, _digest(token)):
                token = secrets.token_urlsafe(32)
                record.csrf_hash = _digest(token)
                db.commit()
    if not token:
        token = secrets.token_urlsafe(32)
    cookie_setting = os.getenv("COOKIE_SECURE")
    secure = request.url.scheme == "https" if cookie_setting is None else cookie_setting.lower() in {"1", "true", "yes"}
    response.set_cookie("clarity_csrf", token, httponly=False, secure=secure, samesite="lax", max_age=SESSION_DAYS * 86400, path="/")
    no_store(response)
    return {"csrf_token": token}

@app.post("/api/auth/register")
def register(payload: RegisterInput, request: Request, response: Response, db: Session = Depends(get_db)):
    if payload.role is not None:
        raise HTTPException(400, "Public registration cannot set an account role")
    email = normalize_email(str(payload.email))
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Unable to create account with those details")
    user = User(email=email, display_name=payload.display_name.strip(), password_hash=hash_password(payload.password), role="USER", is_active=True)
    db.add(user)
    try:
        db.commit(); db.refresh(user)
        raw, csrf = create_session(db, user)
    except SQLAlchemyError:
        db.rollback(); raise HTTPException(409, "Unable to create account with those details")
    set_auth_cookies(response, request, raw, csrf); no_store(response)
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role,
            "csrf_token": csrf}

@app.post("/api/auth/login")
def login(payload: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    key = f"{request.client.host if request.client else 'unknown'}:{normalize_email(str(payload.email))}"
    if not login_allowed(key):
        raise HTTPException(429, "Authentication temporarily unavailable")
    user = db.scalar(select(User).where(User.email == normalize_email(str(payload.email))))
    if user is None or not getattr(user, "is_active", False) or not verify_password(str(getattr(user, "password_hash", "")), payload.password):
        note_login_failure(key); raise HTTPException(401, "Invalid email or password")
    clear_login_failures(key)
    raw, csrf = create_session(db, user); set_auth_cookies(response, request, raw, csrf); no_store(response)
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role,
            "csrf_token": csrf}

@app.post("/api/auth/logout", dependencies=[Depends(csrf_protect)])
def logout(request: Request, response: Response, user: CurrentUser, session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE), db: Session = Depends(get_db)):
    if session_cookie:
        record = db.scalar(select(SessionToken).where(SessionToken.token_hash == _digest(session_cookie), SessionToken.user_id == user.id))
        if record is not None: setattr(record, "revoked_at", datetime.now(timezone.utc)); db.commit()
    clear_auth_cookies(response, request); no_store(response); return {"status": "signed_out"}

@app.get("/api/auth/me")
def me(response: Response, user: CurrentUser):
    no_store(response); return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role}


def ml(request:Request):
    if request.app.state.ml is None: raise HTTPException(503,request.app.state.model_error)
    return request.app.state.ml

@app.get("/health")
def health(request:Request,db:Session=Depends(get_db)):
    try: db.execute(select(1))
    except SQLAlchemyError: raise HTTPException(503,"Database unavailable")
    if request.app.state.ml is None: raise HTTPException(503,request.app.state.model_error)
    return {"status":"ok","database":"ok","model_version":request.app.state.ml.version}

@app.get("/api/meta")
def metadata(response: Response, user: CurrentUser, model=Depends(ml)):
    no_store(response)
    result = {"features":FEATURES,"feature_order":FEATURE_ORDER,"disclaimer":DISCLAIMER,
              "mode":"Authenticated educational research workspace"}
    if getattr(user, "role", "USER") == "ADMIN":
        result.update({"model_version": model.version, "selected_model": model.report["selected_model"],
                       "calibrated": model.report["calibrated"]})
    return result

@app.get("/api/evaluation")
def evaluation(user: AdminUser, response: Response, model=Depends(ml)):
    no_store(response)
    return model.report

@app.get("/api/threshold")
def threshold(user: AdminUser, value:float=Query(.5,ge=.01,le=.99), model=Depends(ml)):
    return {"population":"Training out-of-fold predictions", "metrics":metrics(model.bundle["oof_y"],model.bundle["oof_probability"],value),
            "note":"Exploration only; this does not change the deployed 0.5 decision threshold."}

@app.get("/api/global-shap")
def global_shap(user: AdminUser, model=Depends(ml)):
    try: return model.global_shap()
    except Exception:
        logger.exception("Global SHAP failed");raise HTTPException(503,"Global SHAP is unavailable")

@app.get("/api/versions")
def versions(user: AdminUser, model=Depends(ml)):
    versions=[]
    for p in sorted((ROOT/"models/versions").glob("*/evaluation.json"),reverse=True):
        report=json.loads(p.read_text())
        versions.append({k:report[k] for k in ["version","created_at","selected_model","calibrated","active_test","dataset","seed"]})
    return {"active":model.version,"versions":versions,"note":"Compare metrics only when dataset hash and evaluation split/seed match. Restart after training to load the new active version."}

@app.get("/admin/openapi.json", include_in_schema=False)
def admin_openapi(user: AdminUser):
    return app.openapi()

@app.get("/admin/docs", include_in_schema=False)
def admin_docs(user: AdminUser):
    return get_swagger_ui_html(openapi_url="/admin/openapi.json", title="Clarity admin API")


def personal_explanation(explanation: dict[str, Any]) -> dict[str, Any]:
    """Keep a personal SHAP snapshot while withholding internal settings."""
    status = explanation.get("status", "unavailable")
    if status != "available":
        return {"status": status, "factors": [], "note": "Explanation temporarily unavailable."}
    factors = [
        {key: factor[key] for key in ("feature", "label", "patient_value", "shap_contribution", "contribution_pp")}
        for factor in explanation.get("factors", [])
    ]
    return {
        "status": "available",
        "base_value": explanation["base_value"],
        "output_value": explanation["output_value"],
        "factors": factors,
        "note": "These factors explain how the computer model reached this result. They do not show what caused a condition.",
    }
def personal_recommendations(result: dict[str, Any]) -> dict[str, Any]:
    """Expose only saved personal guidance, never rules or internal versions."""
    cards = result.get("recommendations")
    if not isinstance(cards, list):
        return {"status": "not_stored", "cards": []}
    return {
        "status": "stored",
        "cards": [
            {key: card[key] for key in ("title", "explanation", "next_step") if key in card}
            for card in cards[:3] if isinstance(card, dict)
        ],
    }
def user_result(result, record_id, prediction_id, created_at):
    explanation = (personal_explanation(result["explanation"]) if "explanation" in result else {"status": "not_stored", "factors": [], "note": "Explanation was not stored for this assessment."})
    support = result.get("input_support")
    # Older snapshots are usable only when they stored an explicit boolean check.
    support_status = support.get("status", "available" if isinstance(support, dict) and isinstance(support.get("flagged"), bool) else "unavailable") if isinstance(support, dict) else "unavailable"
    return {"assessment_id": record_id, "prediction_id": prediction_id, "created_at": created_at,
            "features": result["features"], "prediction": result["prediction"],
            "prediction_value": result["prediction_value"], "probability": result["probability"],
            "risk_level": result["risk_level"], "risk_summary": result["risk_summary"],
            "explanation": explanation, "explainability_status": result.get("explainability_status", explanation["status"]),
            "recommendations": personal_recommendations(result),
            "factors_increasing_risk": sorted([factor for factor in explanation["factors"] if factor["shap_contribution"] > 0], key=lambda factor: -factor["shap_contribution"]),
            "factors_decreasing_risk": sorted([factor for factor in explanation["factors"] if factor["shap_contribution"] < 0], key=lambda factor: factor["shap_contribution"]),
            "input_support": {"status": support_status,
                              "flagged": support.get("flagged", False) if support_status == "available" else False,
                              "message": ("Some entered measurements differ from the examples used to train this model. Check the values you entered; the estimate may be less reliable." if support_status == "available" and support.get("flagged", False) else "The measurement check was not available for this assessment." if support_status != "available" else None)},
            "disclaimer": DISCLAIMER}

def save_assessment(data,db,model,user_id):
    result=model.assess(data)
    legacy=Prediction(**data,user_id=user_id,prediction=result["prediction"],probability=result["probability"],risk_level=result["risk_level"])
    try:
        db.add(legacy);db.flush()
        record=Assessment(user_id=user_id,legacy_prediction_id=legacy.id,model_version=model.version,probability=result["probability"],
                          risk_level=result["risk_level"],features=data,result=result)
        db.add(record);db.commit();db.refresh(record)
    except SQLAlchemyError:
        db.rollback();logger.exception("Assessment save failed")
        raise HTTPException(503,"Assessment could not be saved. Check database availability.")
    created_at=record.created_at.isoformat()
    return result, user_result(result, record.id, legacy.id, created_at)

@app.post("/api/predict")
@app.post("/predict",include_in_schema=False)
def predict(patient:PatientInput, user: CurrentUser, _: CSRF, db:Session=Depends(get_db),model=Depends(ml)):
    result, safe = save_assessment(patient.model_dump(),db,model,user.id)
    if getattr(user, "role", "USER") == "ADMIN":
        return {**result, "assessment_id": safe["assessment_id"],
                "prediction_id": safe["prediction_id"], "created_at": safe["created_at"]}
    return safe

@app.post("/api/simulate")
def simulate(payload:SimulationInput, user: AdminUser, _: CSRF, model=Depends(ml)):
    original,modified=payload.original.model_dump(),payload.modified.model_dump()
    allowed=set(NUMERIC)-{"age"}
    changed=[k for k in FEATURE_ORDER if original[k]!=modified[k]]
    if any(k not in allowed for k in changed): raise HTTPException(422,"Only blood pressure, cholesterol, maximum heart rate and ST depression can change in this simulator.")
    before=model.assess(original,explain=False);after=model.assess(modified)
    return {"original_probability":before["probability"],"modified":user_result(after, None, None, None),"changed_features":changed,
            "delta_pp":100*(after["probability"]-before["probability"]),"saved":False,
            "note":"Model sensitivity experiment only. Changed measurements are hypothetical, not recommended interventions or causal effects."}

@app.post("/api/batch")
async def batch(request:Request, user: AdminUser, _: CSRF, model=Depends(ml)):
    chunks=[];size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>1_000_000: raise HTTPException(413,"CSV must be under 1 MB")
        chunks.append(chunk)
    try:
        content=b"".join(chunks).decode("utf-8-sig")
        reader=csv.DictReader(io.StringIO(content),strict=True)
        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)) or set(reader.fieldnames)!=set(FEATURE_ORDER):
            raise HTTPException(422,"CSV header must contain exactly the 13 unique feature names. Download the template.")
        rows=[]
        for row in reader:
            if len(rows)>=250: raise HTTPException(413,"Maximum 250 rows per batch")
            rows.append(row)
    except (UnicodeDecodeError,csv.Error): raise HTTPException(422,"Invalid UTF-8 CSV")
    if not rows: raise HTTPException(422,"CSV contains no data rows")
    return await run_in_threadpool(process_batch_rows, rows, model)

def process_batch_rows(rows, model):
    results=[]
    # Batch rows never modify saved history.
    for index,row in enumerate(rows,start=2):
        try:
            patient=PatientInput.model_validate(row)
            result=model.assess(patient.model_dump(),explain=False)
            results.append({"row":index,"status":"ok","probability":result["probability"],"prediction":result["prediction"],
                            "risk_level":result["risk_level"],"unusual_input":result["input_support"]["flagged"],
                            "model_disagreement":result["disagreement"]["class_disagreement"]})
        except ValidationError as error:
            results.append({"row":index,"status":"invalid","errors":[{"field":".".join(map(str,e["loc"])),"message":e["msg"]} for e in error.errors()]})
    return {"model_version":model.version,"count":len(results),"valid":sum(x["status"]=="ok" for x in results),
            "results":results,"saved":False,"note":"Batch mode omits SHAP for speed. Use Assessment for a full explanation."}

@app.get("/api/history")
def history(user: CurrentUser, response: Response, skip:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),band:str|None=None,db:Session=Depends(get_db)):
    no_store(response)
    query=select(Assessment).where(Assessment.user_id == user.id)
    if band:
        if band not in {"LOW","MEDIUM","HIGH"}: raise HTTPException(422,"Invalid score band")
        query=query.where(Assessment.risk_level==band)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.scalars(query.order_by(Assessment.id.desc()).offset(skip).limit(limit)).all()
    items=[{"id":x.id,"created_at":x.created_at,"probability":x.probability,"risk_level":x.risk_level} for x in rows]
    if getattr(user, "role", "USER") == "ADMIN":
        items=[{**item,"model_version":row.model_version} for item,row in zip(items,rows)]
    return {"total":total,"skip":skip,"limit":limit,"items":items}

@app.get("/api/history/{record_id}")
def saved_record(record_id:int, user: CurrentUser, response: Response, db:Session=Depends(get_db)):
    no_store(response)
    x=db.scalar(select(Assessment).where(Assessment.id == record_id, Assessment.user_id == user.id))
    if not x: raise HTTPException(404,"Assessment not found")
    if getattr(user, "role", "USER") == "ADMIN":
        result_payload = cast(dict[str, Any], x.result)
        return {**result_payload, "assessment_id": x.id, "prediction_id": x.legacy_prediction_id,
                "created_at": x.created_at.isoformat()}
    return user_result(x.result, x.id, x.legacy_prediction_id, x.created_at.isoformat())

@app.get("/history")
@app.get("/predictions",include_in_schema=False)
def legacy_history(user: CurrentUser, skip:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500),db:Session=Depends(get_db)):
    return db.scalars(select(Prediction).where(Prediction.user_id == user.id).order_by(Prediction.id.desc()).offset(skip).limit(limit)).all()

@app.get("/predictions/{prediction_id}")
def legacy_record(prediction_id:int,user: CurrentUser,db:Session=Depends(get_db)):
    record=db.scalar(select(Prediction).where(Prediction.id == prediction_id, Prediction.user_id == user.id))
    if not record: raise HTTPException(404,"Prediction not found")
    return record


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    logger.error("Database operation failed", exc_info=(type(exc),exc,exc.__traceback__))
    return JSONResponse(status_code=503,content={"detail":"Database operation failed. Check the configured database and server logs."})
