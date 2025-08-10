from abc import ABC
from dataclasses import dataclass, field
from datetime import UTC, datetime
import re
from typing import   NewType
from uuid import UUID


BaseUserId =NewType('BaseUserId', UUID) 

@dataclass
class Base(ABC):
    oid: BaseUserId

    def __eq__(self, other) -> bool:
        if isinstance(other, Base):
            return other.oid == self.oid
        return False

    def __hash__(self):
        return hash(self.oid)


@dataclass
class User(Base):
    username: str
    email: str
    password: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    create_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self):
        self.validate_email()
        self.validate_password()
        self.validate_username()

    def validate_username(self):
        if not self.email:
            raise ValueError("Име не должно быть пустым")

    def validate_email(self) -> None:
        if not self.email:
            raise ValueError("Почта не должна быть пустой")

        email_validate_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_validate_pattern, self.email):
            raise ValueError(f"Почта не валидна {self.email}")

    def validate_password(self) -> None:
        if not self.password:
            raise ValueError("Пароль должен быть введён")

        value_length = len(self.password)

        if value_length not in range(3, 100):
            raise ValueError(
                f"Длина пароля от 3 до 100 символов а у вас {self.password}"
            )

    def __str__(self):
        return f"User is : oid {self.oid} ; username {self.username}"


# # Aggregate
# @dataclass(eq=False)
# class UserTokensAggregate:
#     user: User  # корень агрегата
#     _ref_tokens: List[RefreshTokenJti] = field(default_factory=list)

#     def issue_new_token(self) -> RefreshTokenJti:
#         token = RefreshTokenJti()
#         if token in self._ref_tokens:
#             return self.issue_new_token()  
#         self._ref_tokens.append(token)
#         return token

#     def revoke_token(self, jti: RefreshTokenJti):
   
#         if jti not in self._ref_tokens:
#             raise ValueError("Token not found in active sessions")
#         self._ref_tokens.remove(jti)

#     def revoke_all(self):
#         self._ref_tokens = []

#     def is_token_active(self, jti: RefreshTokenJti) -> bool:
#         return jti in self._ref_tokens

#     def _get_active_tokens(self) -> List[RefreshTokenJti]:
#         return self._ref_tokens.copy()
