import structlog

from app.application.common.filters import Filter
from app.application.common.pagination import Pagination
from app.application.common.sorting import Sorting
from app.infrastructure.adapters.repository import UserSqlAlchemyRepository
from dataclasses import dataclass


log = structlog.get_logger(__file__)


@dataclass
class ListUserQuery:
    sorting: Sorting | None = None
    filters: Filter | None = None
    pagination: Pagination | None


# INFO: Хочется абстракцию но пока не надо(1 объект).
class AdminGetAllHandler:
    def __init__(self, repo: UserSqlAlchemyRepository):
        self._repo = repo

    def __call__(self, param: ListUserQuery):
        pass  # WARN: ДОПИСАТЬ
