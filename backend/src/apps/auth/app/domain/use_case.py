from typing import  Optional, Protocol


class AuthService(Protocol):

    async def register(self, email: str, password: str, **data: dict) -> dict: ...

    async def login(self, email: str, password: str) -> dict[str, str]: ...

    async def refresh_tokens(self, refresh_token: str) -> dict[str, str]: ...

    async def logout(
        self, user_id: str, refresh_token: Optional[str] = None
    ) -> None: ...
