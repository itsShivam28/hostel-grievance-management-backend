from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.enums import ComplaintCategory

WorkmanName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
ContactNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9][0-9\s-]{6,18}$"),
]


class WorkmanCreate(BaseModel):
    name: WorkmanName
    contact: ContactNumber
    category: ComplaintCategory


class WorkmanContact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    contact: str


class WorkmanRead(WorkmanContact):
    id: int
    category: ComplaintCategory
