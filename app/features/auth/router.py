import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config.settings import get_settings
from app.core.db.session import get_db
from app.features.auth.jwt import create_access_token
from app.features.auth.password import hash_password, verify_password
from app.features.auth.schemas import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignUpRequest,
    TokenResponse,
)
from app.features.users.repository import (
    create_user,
    get_user_by_email,
    get_user_by_reset_token,
    set_reset_token,
    update_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignUpRequest, db: Session = Depends(get_db)) -> MessageResponse:
    email = body.email.lower()
    if get_user_by_email(db, email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    create_user(db, email, hash_password(body.password))
    return MessageResponse(message="Account created. Please log in.")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = get_user_by_email(db, body.email.lower())
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    settings = get_settings()
    token = create_access_token(user.id, settings)
    return TokenResponse(access_token=token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    settings = get_settings()
    user = get_user_by_email(db, body.email.lower())
    if user is None:
        return ForgotPasswordResponse(
            message="If that email is registered, a reset link has been sent.",
            reset_token=None,
        )
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.password_reset_expire_hours)
    set_reset_token(db, user, token, expires)
    reset_token = token if settings.auth_expose_reset_token else None
    return ForgotPasswordResponse(
        message="If that email is registered, a reset link has been sent.",
        reset_token=reset_token,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    user = get_user_by_email(db, body.email.lower())
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset request")
    if body.reset_token is None:
        update_password(db, user, hash_password(body.new_password))
        return MessageResponse(message="Password updated")
    if user.reset_token is None or user.reset_token != body.reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token")
    if user.reset_token_expires_at is None or user.reset_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token expired")
    token_user = get_user_by_reset_token(db, body.reset_token)
    if token_user is None or token_user.id != user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset request")
    update_password(db, user, hash_password(body.new_password))
    return MessageResponse(message="Password updated")
