from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Workman
from app.schemas.workman import WorkmanCreate


def get(db: Session, workman_id: int) -> Workman | None:
    return db.get(Workman, workman_id)


def list_all(db: Session) -> Sequence[Workman]:
    return db.scalars(select(Workman).order_by(Workman.name, Workman.id)).all()


def create(db: Session, payload: WorkmanCreate) -> Workman:
    workman = Workman(**payload.model_dump())
    db.add(workman)
    db.commit()
    return workman
