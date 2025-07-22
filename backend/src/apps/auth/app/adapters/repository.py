import abc
from app.domain import entities


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, user: entities.User):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference) -> entities.User:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        self.session = session

    def add(self, user: entities.User):
        self.session.add(user)

    def get(self, reference):
        return self.session.query(entities.User).filter_by(email=reference).one()

    def list(self):
        return self.session.query(entities.User).all()
