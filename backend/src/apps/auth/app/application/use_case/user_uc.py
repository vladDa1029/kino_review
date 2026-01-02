import structlog

from app.application.common.pagination import Pagination
from app.infrastructure.adapters.repository import UserSqlAlchemyRepository


log = structlog.get_logger(__file__)


class AdminGetAllHandler:
    def __init__(self, user_repo: UserSqlAlchemyRepository, page: Pagination): ...
