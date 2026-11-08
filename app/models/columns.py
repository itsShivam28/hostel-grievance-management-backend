from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Enum


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_column(enum_class: type[StrEnum]) -> Enum:
    return Enum(
        enum_class,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
