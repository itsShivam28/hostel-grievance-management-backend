from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.columns import enum_column
from app.models.enums import ComplaintCategory

if TYPE_CHECKING:
    from app.models.complaint import Complaint


class Workman(Base):
    __tablename__ = "workmen"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(20))
    category: Mapped[ComplaintCategory] = mapped_column(enum_column(ComplaintCategory))

    complaints: Mapped[list["Complaint"]] = relationship(back_populates="assigned_workman")
