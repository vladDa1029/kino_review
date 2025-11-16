from app.domain.exceptions.base import ApplicationError


class InvalidCredentialsError(ApplicationError):
    """Ошибка слоя use case."""


class UserAlreadyError(ApplicationError):
    """Ошибка пользователь уже существует"""
