# TODO: Доделать все действия после.
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin

from src.settings.config import get_settings
from src.users.dependensy import get_user_db
from src.users.models import User
from src.users.hash import password_helper

settings = get_settings()


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = settings.auth.PRIVATE_KEY
    reset_password_token_lifetime_seconds = settings.auth.refresh_token_time
    verification_token_secret = settings.auth.PUBLIC_KEY
    verification_token_lifetime_seconds = settings.auth.access_token_time

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db, password_helper)
