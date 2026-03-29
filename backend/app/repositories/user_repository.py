from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def list_users(db: Session, limit: int = 50, offset: int = 0) -> list[User]:
    return (
        db.query(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def create(
    db: Session,
    *,
    username: str,
    email: str | None,
    password_hash: str,
    role: str,
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def set_active_status(db: Session, user: User, is_active: bool) -> User:
    user.is_active = is_active
    db.flush()
    return user


def refresh(db: Session, user: User) -> User:
    db.refresh(user)
    return user