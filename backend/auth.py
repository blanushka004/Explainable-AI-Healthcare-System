"""Session authentication, password hashing, and centralized authorization."""
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError
from .database import get_db
from .models import SessionToken, User

SESSION_COOKIE = "clarity_session"
CSRF_COOKIE = "clarity_csrf"
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "8"))
PASSWORDS = PasswordHasher()

def _now():
    return datetime.now(timezone.utc)

def _active_until(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value > _now()

def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def normalize_email(email: str) -> str:
    return email.strip().casefold()

def hash_password(password: str) -> str:
    return PASSWORDS.hash(password)

def verify_password(stored: str, password: str) -> bool:
    try:
        return PASSWORDS.verify(stored, password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False

def cookie_secure(request: Request) -> bool:
    configured = os.getenv("COOKIE_SECURE")
    if configured is not None:
        return configured.lower() in {"1", "true", "yes"}
    return request.url.scheme == "https"

def set_auth_cookies(response: Response, request: Request, raw_token: str, csrf: str):
    secure = cookie_secure(request)
    response.set_cookie(SESSION_COOKIE, raw_token, httponly=True, secure=secure,
                        samesite="lax", max_age=SESSION_DAYS * 86400, path="/")
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=secure,
                        samesite="lax", max_age=SESSION_DAYS * 86400, path="/")

def clear_auth_cookies(response: Response, request: Request):
    response.delete_cookie(SESSION_COOKIE, secure=cookie_secure(request), samesite="lax", path="/")
    response.delete_cookie(CSRF_COOKIE, secure=cookie_secure(request), samesite="lax", path="/")

def create_session(db: Session, user: User) -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    db.add(SessionToken(user_id=user.id, token_hash=_digest(raw), csrf_hash=_digest(csrf),
                        expires_at=_now() + timedelta(days=SESSION_DAYS)))
    db.commit()
    return raw, csrf

def current_user(session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
                 db: Session = Depends(get_db)) -> User:
    if not session_cookie:
        raise HTTPException(401, "Authentication required")
    record = db.scalar(select(SessionToken).where(SessionToken.token_hash == _digest(session_cookie)))
    if not record or record.revoked_at or not _active_until(record.expires_at):
        raise HTTPException(401, "Authentication required")
    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Authentication required")
    record.last_seen_at = _now()
    db.commit()
    return user

def csrf_protect(request: Request, csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
                 session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
                 csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE)] = None,
                 db: Session = Depends(get_db)):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if not session_cookie or not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(403, "CSRF validation failed")
    record = db.scalar(select(SessionToken).where(SessionToken.token_hash == _digest(session_cookie)))
    if not record or not hmac.compare_digest(record.csrf_hash, _digest(csrf_header)):
        raise HTTPException(403, "CSRF validation failed")

def require_user(user: User = Depends(current_user)) -> User:
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "ADMIN":
        raise HTTPException(403, "Administrator access required")
    return user

def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"

def throttle_key(request: Request, email: str) -> str:
    return f"{request.client.host if request.client else 'unknown'}:{normalize_email(email)}"

_LOGIN_FAILURES: dict[str, list[float]] = {}
def login_allowed(key: str) -> bool:
    now = time.time()
    failures = [stamp for stamp in _LOGIN_FAILURES.get(key, []) if now - stamp < 900]
    _LOGIN_FAILURES[key] = failures
    return len(failures) < 5

def note_login_failure(key: str):
    _LOGIN_FAILURES.setdefault(key, []).append(time.time())

def clear_login_failures(key: str):
    _LOGIN_FAILURES.pop(key, None)

CurrentUser = Annotated[User, Depends(require_user)]
AdminUser = Annotated[User, Depends(require_admin)]
CSRF = Annotated[None, Depends(csrf_protect)]
