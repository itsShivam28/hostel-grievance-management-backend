from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints

from app.core.security import BCRYPT_MAX_PASSWORD_BYTES


def normalize_hostel_name(value: str) -> str:
    return " ".join(value.split()).upper()


def ensure_bcrypt_compatible(value: str) -> str:
    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must not exceed {BCRYPT_MAX_PASSWORD_BYTES} bytes")
    return value


HostelName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(normalize_hostel_name),
]

Password = Annotated[
    str,
    Field(min_length=8),
    AfterValidator(ensure_bcrypt_compatible),
]
