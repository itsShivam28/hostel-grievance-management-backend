from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Complaint, ComplaintStatus, User
from app.schemas.complaint import ComplaintCreate

LOAD_ASSIGNED_WORKMAN = selectinload(Complaint.assigned_workman)


def create(db: Session, *, student: User, payload: ComplaintCreate) -> Complaint:
    complaint = Complaint(
        student_id=student.id,
        hostel_name=student.hostel_name,
        category=payload.category,
        description=payload.description,
        photo_url=str(payload.photo_url) if payload.photo_url else None,
    )
    db.add(complaint)
    db.commit()
    return complaint


def get_for_student(
    db: Session, complaint_id: int, student_id: int, *, for_update: bool = False
) -> Complaint | None:
    query = (
        select(Complaint)
        .options(LOAD_ASSIGNED_WORKMAN)
        .where(Complaint.id == complaint_id, Complaint.student_id == student_id)
    )
    if for_update:
        query = query.with_for_update(of=Complaint)
    return db.scalar(query)


def get_for_hostel(
    db: Session, complaint_id: int, hostel_name: str, *, for_update: bool = False
) -> Complaint | None:
    query = (
        select(Complaint)
        .options(LOAD_ASSIGNED_WORKMAN)
        .where(Complaint.id == complaint_id, Complaint.hostel_name == hostel_name)
    )
    if for_update:
        query = query.with_for_update(of=Complaint)
    return db.scalar(query)


def list_for_student(
    db: Session, student_id: int, *, offset: int, limit: int
) -> Sequence[Complaint]:
    query = (
        select(Complaint)
        .options(LOAD_ASSIGNED_WORKMAN)
        .where(Complaint.student_id == student_id)
        .order_by(Complaint.created_at.desc(), Complaint.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return db.scalars(query).all()


def list_for_hostel(
    db: Session,
    hostel_name: str,
    *,
    status: ComplaintStatus | None,
    offset: int,
    limit: int,
) -> Sequence[Complaint]:
    query = (
        select(Complaint).options(LOAD_ASSIGNED_WORKMAN).where(Complaint.hostel_name == hostel_name)
    )
    if status is not None:
        query = query.where(Complaint.status == status)
    query = (
        query.order_by(Complaint.is_urgent.desc(), Complaint.created_at.desc(), Complaint.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return db.scalars(query).all()
