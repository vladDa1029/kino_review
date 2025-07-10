## Генерация ключей для работы токенов.

Генерация приватного ключа.
~~~sh
openssl genrsa -out src\auth\private_key.pem 2048
~~~
Генерация публичного ключа по приватному.
``` sh
openssl rsa -in src\auth\private_key.pem -pubout -out src\auth\public_key.pem
```
## Генерация ключей для работы сброса пароля.
```sh
openssl rand -hex 32 > src/auth/reset_secret.key
```

``` sh
openssl rand -hex 32 > src/auth/forgot_secret.key
```