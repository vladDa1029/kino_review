## Генерация ключей для работы токенов.

Генерация приватного ключа.
~~~sh
openssl genrsa -out src\apps\auth\app\key\private_key.pem 2048
~~~
Генерация публичного ключа по приватному.
``` sh
openssl rsa -in src\apps\auth\app\key\private_key.pem -pubout -out src\apps\auth\app\key\public_key.pem
```

