from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.columns import enum_column, utcnow
from app.models.enums import ComplaintCategory, ComplaintStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workman import Workman


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (Index("ix_complaints_hostel_name_status", "hostel_name", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    hostel_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[ComplaintCategory] = mapped_column(enum_column(ComplaintCategory))
    description: Mapped[str] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[ComplaintStatus] = mapped_column(
        enum_column(ComplaintStatus), default=ComplaintStatus.PENDING
    )
    assigned_workman_id: Mapped[int | None] = mapped_column(
        ForeignKey("workmen.id", ondelete="SET NULL")
    )
    is_urgent: Mapped[bool] = mapped_column(default=False)
    student_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    student: Mapped["User"] = relationship(back_populates="complaints")
    assigned_workman: Mapped["Workman | None"] = relationship(back_populates="complaints")
