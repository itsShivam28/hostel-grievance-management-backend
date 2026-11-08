from typing import Annotated

from fastapi import APIRouter, Query, status

from app.crud import complaint as complaint_crud
from app.crud import workman as workman_crud
from app.dependencies.auth import CurrentWarden, DbSession
from app.dependencies.pagination import Page
from app.models import ComplaintStatus
from app.schemas.complaint import WardenComplaintRead, WorkmanAssignment
from app.schemas.workman import WorkmanCreate, WorkmanRead
from app.services import complaint_workflow

router = APIRouter(prefix="/warden", tags=["warden"])


@router.get("/complaints")
def list_hostel_complaints(
    warden: CurrentWarden,
    db: DbSession,
    page: Page,
    status_filter: Annotated[ComplaintStatus | None, Query(alias="status")] = None,
) -> list[WardenComplaintRead]:
    complaints = complaint_crud.list_for_hostel(
        db,
        warden.hostel_name,
        status=status_filter,
        offset=page.offset,
        limit=page.limit,
    )
    return [WardenComplaintRead.model_validate(complaint) for complaint in complaints]


@router.post("/complaints/{complaint_id}/assign")
def assign_workman(
    complaint_id: int,
    payload: WorkmanAssignment,
    warden: CurrentWarden,
    db: DbSession,
) -> WardenComplaintRead:
    complaint = complaint_workflow.assign_workman(
        db, warden=warden, complaint_id=complaint_id, workman_id=payload.workman_id
    )
    return WardenComplaintRead.model_validate(complaint)


@router.post("/complaints/{complaint_id}/close")
def close_complaint(complaint_id: int, warden: CurrentWarden, db: DbSession) -> WardenComplaintRead:
    complaint = complaint_workflow.close_complaint(db, warden=warden, complaint_id=complaint_id)
    return WardenComplaintRead.model_validate(complaint)


@router.get("/workmen")
def list_workmen(_: CurrentWarden, db: DbSession) -> list[WorkmanRead]:
    return [WorkmanRead.model_validate(workman) for workman in workman_crud.list_all(db)]


@router.post("/workmen", status_code=status.HTTP_201_CREATED)
def create_workman(payload: WorkmanCreate, _: CurrentWarden, db: DbSession) -> WorkmanRead:
    return WorkmanRead.model_validate(workman_crud.create(db, payload))
