from passlib.context import CryptContext

crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordHasher:
    def __init__(self):
        self.pwd_context = crypt_context

    def hash_password(self, password: str) -> str:
        """Хеширует пароль с использованием bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверяет, соответствует ли пароль хешу."""
        return self.pwd_context.verify(plain_password, hashed_password)
