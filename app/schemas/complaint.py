from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, HttpUrl, StringConstraints

from app.models import Complaint, ComplaintCategory, ComplaintStatus
from app.schemas.workman import WorkmanContact, WorkmanRead

ComplaintDescription = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)
]


class ComplaintCreate(BaseModel):
    category: ComplaintCategory
    description: ComplaintDescription
    photo_url: HttpUrl | None = None


class WorkmanAssignment(BaseModel):
    workman_id: int


class _ComplaintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostel_name: str
    category: ComplaintCategory
    description: str
    photo_url: str | None
    status: ComplaintStatus
    is_urgent: bool
    student_verified: bool
    created_at: datetime
    updated_at: datetime


class StudentComplaintRead(_ComplaintRead):
    point_of_contact: WorkmanContact | None = None

    @classmethod
    def from_complaint(cls, complaint: Complaint) -> Self:
        view = cls.model_validate(complaint)
        if complaint.status is ComplaintStatus.WORKING and complaint.assigned_workman is not None:
            view.point_of_contact = WorkmanContact.model_validate(complaint.assigned_workman)
        return view


class WardenComplaintRead(_ComplaintRead):
    student_id: int
    assigned_workman: WorkmanRead | None
