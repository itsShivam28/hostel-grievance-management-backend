from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InvalidCredentialsError
from app.core.security import hash_password, verify_password
from app.crud import user as user_crud
from app.models import User, UserRole
from app.schemas.user import StudentRegistration, WardenCreation


@lru_cache
def _decoy_password_hash() -> str:
    return hash_password("decoy-password-for-constant-time-checks")


def _create_account(
    db: Session, payload: StudentRegistration | WardenCreation, role: UserRole
) -> User:
    if user_crud.get_by_email(db, payload.email) is not None:
        raise ConflictError("Email is already registered")
    return user_crud.create(
        db,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role,
        hostel_name=payload.hostel_name,
    )


def register_student(db: Session, payload: StudentRegistration) -> User:
    return _create_account(db, payload, UserRole.STUDENT)


def create_warden(db: Session, payload: WardenCreation) -> User:
    return _create_account(db, payload, UserRole.WARDEN)


def authenticate(db: Session, email: str, password: str) -> User:
    user = user_crud.get_by_email(db, email.strip().lower())
    stored_hash = user.hashed_password if user is not None else _decoy_password_hash()
    password_matches = verify_password(password, stored_hash)
    if user is None or not password_matches:
        raise InvalidCredentialsError("Incorrect email or password")
    return user
