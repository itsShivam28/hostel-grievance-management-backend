from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import create_access_token
from app.dependencies.auth import CurrentUser, DbSession
from app.schemas.user import StudentRegistration, TokenResponse, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_student(payload: StudentRegistration, db: DbSession) -> UserRead:
    user = auth_service.register_student(db, payload)
    return UserRead.model_validate(user)


@router.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> TokenResponse:
    user = auth_service.authenticate(db, form.username, form.password)
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me")
def read_current_user(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
