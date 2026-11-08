from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.columns import enum_column
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.complaint import Complaint


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole))
    hostel_name: Mapped[str] = mapped_column(String(100))

    complaints: Mapped[list["Complaint"]] = relationship(back_populates="student")
