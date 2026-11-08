import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Complaint, ComplaintStatus

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


def flag_overdue_complaints(db: Session, *, now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(UTC)) - timedelta(days=get_settings().urgent_after_days)
    statement = (
        update(Complaint)
        .where(
            Complaint.status != ComplaintStatus.CLOSED,
            Complaint.created_at < cutoff,
            Complaint.is_urgent.is_(False),
        )
        .values(is_urgent=True)
        .execution_options(synchronize_session=False)
    )
    result = cast("CursorResult[Any]", db.execute(statement))
    db.commit()
    return result.rowcount


def _sweep_once(session_factory: SessionFactory) -> int:
    with session_factory() as db:
        return flag_overdue_complaints(db)


async def run_periodic_urgency_check(
    session_factory: SessionFactory, *, interval_seconds: float
) -> None:
    while True:
        try:
            flagged = await asyncio.to_thread(_sweep_once, session_factory)
            if flagged:
                logger.info("Marked %d overdue complaint(s) as urgent", flagged)
        except Exception:
            logger.exception("Urgency check failed; will retry on the next cycle")
        await asyncio.sleep(interval_seconds)
