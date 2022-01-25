from typing import Optional
from fastapi import Query, Depends


class CommonQueryPagination:
    def __init__(
        self,
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, gt=0, le=100),
    ):

        self.page = page
        self.limit = limit


class CommonQuerySelectFields:
    def __init__(self, fields: Optional[str] = Query(default=None)):
        self.fields = fields


class CommonQueryFilter:
    def __init__(
        self, sortBy: str = Query(default="id"), sortType: str = Query(default="asc")
    ):
        self.sortBy = sortBy
        self.sortType = sortType


class CommonQueryGetter:
    def __init__(
        self,
        fields: Optional[str] = Query(default=None),
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, gt=0, le=100),
        sortBy: str = Query(default="id"),
        sortType: str = Query(default="asc"),
    ):
        self.fields = fields
        self.page = page
        self.limit = limit
        self.sortBy = sortBy
        self.sortType = sortType
