from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.crud import complaint as complaint_crud
from app.crud import workman as workman_crud
from app.models import Complaint, ComplaintStatus, User


def _lock_student_complaint(db: Session, student: User, complaint_id: int) -> Complaint:
    complaint = complaint_crud.get_for_student(db, complaint_id, student.id, for_update=True)
    if complaint is None:
        raise NotFoundError("Complaint not found")
    return complaint


def _lock_hostel_complaint(db: Session, warden: User, complaint_id: int) -> Complaint:
    complaint = complaint_crud.get_for_hostel(db, complaint_id, warden.hostel_name, for_update=True)
    if complaint is None:
        raise NotFoundError("Complaint not found")
    return complaint


def assign_workman(db: Session, *, warden: User, complaint_id: int, workman_id: int) -> Complaint:
    complaint = _lock_hostel_complaint(db, warden, complaint_id)
    if complaint.status is not ComplaintStatus.PENDING:
        raise ConflictError("A workman can only be assigned to a pending complaint")

    workman = workman_crud.get(db, workman_id)
    if workman is None:
        raise NotFoundError("Workman not found")

    complaint.assigned_workman = workman
    complaint.status = ComplaintStatus.WORKING
    db.commit()
    return complaint


def verify_resolution(db: Session, *, student: User, complaint_id: int) -> Complaint:
    complaint = _lock_student_complaint(db, student, complaint_id)
    if complaint.status is not ComplaintStatus.WORKING:
        raise ConflictError(
            f"Only complaints being worked on can be verified (current status: {complaint.status})"
        )

    complaint.student_verified = True
    complaint.status = ComplaintStatus.RESOLVED
    db.commit()
    return complaint


def close_complaint(db: Session, *, warden: User, complaint_id: int) -> Complaint:
    complaint = _lock_hostel_complaint(db, warden, complaint_id)
    if complaint.status is ComplaintStatus.CLOSED:
        raise ConflictError("Complaint is already closed")
    if not complaint.student_verified:
        raise ConflictError("Complaint cannot be closed until the student verifies the work")

    complaint.status = ComplaintStatus.CLOSED
    db.commit()
    return complaint
