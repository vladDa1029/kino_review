# TODO: написать и другие транспорты (redis, db , cookie)

from fastapi_users.authentication import BearerTransport

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")