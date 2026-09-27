from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.users.models import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)


def get_user_by_reset_token(db: Session, token: str) -> User | None:
    return db.scalar(select(User).where(User.reset_token == token))


def create_user(db: Session, email: str, hashed_password: str) -> User:
    user = User(email=email.lower(), hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_password(db: Session, user: User, hashed_password: str) -> None:
    user.hashed_password = hashed_password
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()


def set_reset_token(db: Session, user: User, token: str, expires_at: datetime) -> None:
    user.reset_token = token
    user.reset_token_expires_at = expires_at
    db.commit()
