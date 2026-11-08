import asyncio
from datetime import timedelta
from typing import Protocol

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.crud import complaint as complaint_crud
from app.models import Complaint, ComplaintStatus
from app.models.columns import utcnow
from app.services.urgency import flag_overdue_complaints, run_periodic_urgency_check
from tests.conftest import StudentFactory
from tests.helpers import file_complaint, set_age, set_status


class AgedComplaintFactory(Protocol):
    def __call__(
        self, age: timedelta, status: ComplaintStatus = ComplaintStatus.PENDING
    ) -> int: ...


def _is_urgent(db: Session, complaint_id: int) -> bool:
    complaint = db.get(Complaint, complaint_id)
    assert complaint is not None
    db.refresh(complaint)
    return complaint.is_urgent


@pytest.fixture
def file_aged_complaint(
    client: TestClient, make_student: StudentFactory, db: Session
) -> AgedComplaintFactory:
    headers = make_student()

    def factory(age: timedelta, status: ComplaintStatus = ComplaintStatus.PENDING) -> int:
        complaint_id: int = file_complaint(client, headers)["id"]
        set_age(db, complaint_id, age)
        set_status(db, complaint_id, status)
        return complaint_id

    return factory


def test_complaint_older_than_a_week_becomes_urgent(
    file_aged_complaint: AgedComplaintFactory, db: Session
) -> None:
    complaint_id = file_aged_complaint(timedelta(days=7, minutes=1))

    flagged = flag_overdue_complaints(db)

    assert flagged == 1
    assert _is_urgent(db, complaint_id)


def test_complaint_just_under_a_week_old_stays_normal(
    file_aged_complaint: AgedComplaintFactory, db: Session
) -> None:
    complaint_id = file_aged_complaint(timedelta(days=6, hours=23))

    flagged = flag_overdue_complaints(db)

    assert flagged == 0
    assert not _is_urgent(db, complaint_id)


@pytest.mark.parametrize(
    "status", [ComplaintStatus.PENDING, ComplaintStatus.WORKING, ComplaintStatus.RESOLVED]
)
def test_every_unclosed_status_is_eligible(
    file_aged_complaint: AgedComplaintFactory, db: Session, status: ComplaintStatus
) -> None:
    complaint_id = file_aged_complaint(timedelta(days=10), status)

    flag_overdue_complaints(db)

    assert _is_urgent(db, complaint_id)


def test_closed_complaints_are_never_flagged(
    file_aged_complaint: AgedComplaintFactory, db: Session
) -> None:
    complaint_id = file_aged_complaint(timedelta(days=30), ComplaintStatus.CLOSED)

    flagged = flag_overdue_complaints(db)

    assert flagged == 0
    assert not _is_urgent(db, complaint_id)


def test_sweep_only_touches_overdue_complaints_and_is_idempotent(
    file_aged_complaint: AgedComplaintFactory, db: Session
) -> None:
    old = file_aged_complaint(timedelta(days=8))
    fresh = file_aged_complaint(timedelta(days=1))

    assert flag_overdue_complaints(db) == 1
    assert flag_overdue_complaints(db) == 0
    assert _is_urgent(db, old)
    assert not _is_urgent(db, fresh)


def test_reference_time_can_be_injected(
    file_aged_complaint: AgedComplaintFactory, db: Session
) -> None:
    complaint_id = file_aged_complaint(timedelta(days=2))

    assert flag_overdue_complaints(db) == 0
    assert flag_overdue_complaints(db, now=utcnow() + timedelta(days=6)) == 1
    assert _is_urgent(db, complaint_id)


def test_urgent_complaints_surface_first_for_wardens(
    file_aged_complaint: AgedComplaintFactory, db: Session
) -> None:
    older = file_aged_complaint(timedelta(days=9))
    newer = file_aged_complaint(timedelta(days=1))
    flag_overdue_complaints(db)

    listed = complaint_crud.list_for_hostel(db, "HOSTEL A", status=None, offset=0, limit=10)

    assert [complaint.id for complaint in listed] == [older, newer]
    assert listed[0].is_urgent and not listed[1].is_urgent


def test_background_loop_flags_complaints_and_stops_cleanly(
    file_aged_complaint: AgedComplaintFactory,
    db: Session,
    session_factory: sessionmaker[Session],
) -> None:
    complaint_id = file_aged_complaint(timedelta(days=9))

    async def run_loop_briefly() -> None:
        task = asyncio.create_task(
            run_periodic_urgency_check(session_factory, interval_seconds=0.05)
        )
        await asyncio.sleep(0.5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_loop_briefly())

    assert _is_urgent(db, complaint_id)


def test_background_loop_survives_a_failing_cycle() -> None:
    attempts = 0

    def flaky_session_factory() -> Session:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("database temporarily unavailable")

    async def run_loop_briefly() -> None:
        task = asyncio.create_task(
            run_periodic_urgency_check(flaky_session_factory, interval_seconds=0.05)
        )
        await asyncio.sleep(0.3)
        assert not task.done()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_loop_briefly())

    assert attempts >= 2
