from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.core.config import get_settings
from app.models.enums import UserRole
from app.schemas.types import HostelName, Password


class _NewAccount(BaseModel):
    email: EmailStr
    password: Password
    hostel_name: HostelName

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class StudentRegistration(_NewAccount):
    @field_validator("email")
    @classmethod
    def require_institute_domain(cls, value: str) -> str:
        required_suffix = f"@{get_settings().student_email_domain}"
        if not value.endswith(required_suffix):
            raise ValueError(f"Email must belong to {required_suffix}")
        return value


class WardenCreation(_NewAccount):
    pass


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    hostel_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
