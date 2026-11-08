from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCredentialsError, PermissionDeniedError
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.database import get_db
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    user = user_crud.get_by_id(db, decode_access_token(token))
    if user is None:
        raise InvalidCredentialsError("Could not validate credentials")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    def check_role(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise PermissionDeniedError("You do not have permission to perform this action")
        return user

    return check_role


CurrentStudent = Annotated[User, Depends(require_roles(UserRole.STUDENT))]
CurrentWarden = Annotated[User, Depends(require_roles(UserRole.WARDEN))]
