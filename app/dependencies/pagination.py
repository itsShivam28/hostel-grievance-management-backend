from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query


@dataclass(frozen=True, slots=True)
class PageParams:
    offset: int
    limit: int


def get_page_params(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PageParams:
    return PageParams(offset=offset, limit=limit)


Page = Annotated[PageParams, Depends(get_page_params)]
