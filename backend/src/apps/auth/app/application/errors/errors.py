from app.domain.errors.base import ApplicationError


class InvalidCredentialsError(ApplicationError):
    """Ошибка слоя use case."""


class UserAlreadyError(ApplicationError):
    """Ошибка пользователь уже существует"""


class PasswordOrLogInincorrectError(ApplicationError):
    """Пароль или логин не верные"""
