from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Complaint, ComplaintStatus
from app.models.columns import utcnow

AuthHeaders = dict[str, str]


def file_complaint(client: TestClient, headers: AuthHeaders, **overrides: Any) -> dict[str, Any]:
    payload = {"category": "Electricity", "description": "Tube light is not working"} | overrides
    response = client.post("/student/complaints", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return dict(response.json())


def assign(
    client: TestClient, warden: AuthHeaders, complaint_id: int, workman_id: int
) -> dict[str, Any]:
    response = client.post(
        f"/warden/complaints/{complaint_id}/assign",
        json={"workman_id": workman_id},
        headers=warden,
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def set_age(db: Session, complaint_id: int, age: timedelta) -> None:
    db.execute(
        update(Complaint).where(Complaint.id == complaint_id).values(created_at=utcnow() - age)
    )
    db.commit()


def set_status(db: Session, complaint_id: int, status: ComplaintStatus) -> None:
    db.execute(update(Complaint).where(Complaint.id == complaint_id).values(status=status))
    db.commit()
