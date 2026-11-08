from fastapi import APIRouter, status

from app.crud import complaint as complaint_crud
from app.dependencies.auth import CurrentStudent, DbSession
from app.dependencies.pagination import Page
from app.schemas.complaint import ComplaintCreate, StudentComplaintRead
from app.services import complaint_workflow

router = APIRouter(prefix="/student/complaints", tags=["student"])


@router.post("", status_code=status.HTTP_201_CREATED)
def register_complaint(
    payload: ComplaintCreate, student: CurrentStudent, db: DbSession
) -> StudentComplaintRead:
    complaint = complaint_crud.create(db, student=student, payload=payload)
    return StudentComplaintRead.from_complaint(complaint)


@router.get("")
def list_my_complaints(
    student: CurrentStudent, db: DbSession, page: Page
) -> list[StudentComplaintRead]:
    complaints = complaint_crud.list_for_student(
        db, student.id, offset=page.offset, limit=page.limit
    )
    return [StudentComplaintRead.from_complaint(complaint) for complaint in complaints]


@router.post("/{complaint_id}/verify")
def verify_complaint(
    complaint_id: int, student: CurrentStudent, db: DbSession
) -> StudentComplaintRead:
    complaint = complaint_workflow.verify_resolution(db, student=student, complaint_id=complaint_id)
    return StudentComplaintRead.from_complaint(complaint)
