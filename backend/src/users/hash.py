# TODO: Проверить кодировка оптимальна и достаточно

from fastapi_users.password import PasswordHelper
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

password_hash = PasswordHash((
    Argon2Hasher(),
))
password_helper = PasswordHelper(password_hash)