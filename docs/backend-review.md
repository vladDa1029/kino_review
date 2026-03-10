# Backend Code Review

Дата ревью: 2026-03-07

## Контекст

- Ниже ревью backend-части репозитория `kino`.
- С учетом уточнения: текущий `docker-compose` рассматривается как dev-окружение.
- Для production предполагается, что наружу будет опубликован только `api-getaway`, а прямой доступ к `auth`, `user`, `project`, `postgres`, `rabbitmq`, `minio` будет закрыт.

Это снижает часть инфраструктурных рисков в текущем compose, но не отменяет архитектурные и контрактные слабые места backend.

## Критично

### 1. `project-service` небезопасен при прямом доступе

`project-service` доверяет заголовку `X-User-Id` как источнику идентичности и не валидирует JWT сам.

Почему это проблема:
- если сервис случайно окажется доступен напрямую не только через `api-getaway`, любой клиент сможет подставить чужой `X-User-Id`;
- защита завязана не на сам сервис, а на корректную сетевую топологию;
- это создает хрупкую security-модель: ошибка в ingress/reverse proxy сразу превращается в компрометацию авторизации.

Подтверждение в коде:
- `project` читает `X-User-Id` напрямую: `backend/src/apps/project/app/presentation/api.py`
- `project` явно принимает этот заголовок в CORS: `backend/src/apps/project/main.py`
- в dev compose сервис опубликован наружу: `docker-compose.yaml`

Важно: с вашим уточнением это не означает, что текущий dev compose "неправильный". Это означает, что `project-service` пока не является self-protected сервисом и зависит от правильной изоляции сети.

## Высокий

### 2. Контракт между `project` и `user` сейчас расходится

`project-service` пытается резервировать время через:
- `/reservations/user-time`
- `/reservations/resource-time`

Но в `user-service` опубликован endpoint:
- `/users/{user_id}/availability/reserve`

Почему это проблема:
- подтверждение участника смены и approve resource request будут падать в рантайме;
- ошибка находится не на уровне валидации схемы, а проявится только в интеграции;
- это прямой признак несогласованного API-контракта между сервисами.

Подтверждение в коде:
- `backend/src/apps/project/app/presentation/http/user_service.py`
- `backend/src/apps/user/app/presentation/api.py`

### 3. Резервирование между сервисами было неконсистентным, но теперь закрыто через saga/outbox/idempotency

Что изменено:
- в `project-service` reserve больше не живет внутри одного локального use-case с внешним вызовом до финального `commit`;
- локальная сущность сначала переводится в `RESERVING` и вместе с этим в БД пишется запись reservation-outbox;
- затем saga-шаг reserve обрабатывается отдельно: сразу после commit и повторно фоновым poller'ом, если первый проход не завершился;
- вызов в `user-service` теперь идемпотентен по `request_id`, поэтому повтор после частичного сбоя возвращает тот же `reservation_id`, а не создает второй резерв.

Что это дает:
- если внешний reserve в `user-service` уже прошел, а локальный commit финализации в `project-service` упал, outbox-сообщение останется `pending`;
- следующий retry повторит тот же reserve с тем же `request_id` и дотянет локальную сущность до `RESERVED`, не создавая дубль;
- расхождение состояний между сервисами больше не зависит от "успел ли пройти последний commit" в том же request path.

Подтверждение в коде:
- saga/outbox processor: `backend/src/apps/project/app/application/commands/reservation_outbox.py`
- enqueue шага reserve: `backend/src/apps/project/app/application/commands/participants.py`
- enqueue шага reserve: `backend/src/apps/project/app/application/commands/resources.py`
- outbox persistence: `backend/src/apps/project/app/infrastructure/adapters/orm.py`
- idempotent reserve contract: `backend/src/apps/project/app/presentation/http/user_service.py`
- idempotency store в `user`: `backend/src/apps/user/app/application/commands/reserve_availability.py`

### 4. Refresh token lifecycle не завершен

Сейчас:
- refresh-токену генерируется `jti`;
- сервер не хранит и не проверяет этот `jti`;
- `logout()` не реализован;
- refresh-токен нельзя нормально отозвать до истечения TTL.

Почему это проблема:
- при утечке refresh-токена злоумышленник сохраняет долгоживущий доступ;
- невозможна нормальная серверная инвалидизация сессий;
- rotate токена формально есть, но полноценной session security нет.

Подтверждение в коде:
- `backend/src/apps/auth/app/infrastructure/security/jwt.py`
- `backend/src/apps/auth/app/application/use_case/authenticate_uc.py`

## Средний

### 5. Ошибки декодирования refresh JWT покрыты не полностью

`decode_token()` ловит только:
- `ExpiredSignatureError`
- `InvalidSignatureError`

Но битый JWT может выбросить, например, `DecodeError`.

Почему это проблема:
- часть невалидных токенов может уйти в `500`, а не в ожидаемый `401`;
- это делает auth flow менее устойчивым и хуже для observability.

Подтверждение в коде:
- `backend/src/apps/auth/app/infrastructure/security/jwt.py`
- `backend/src/apps/auth/app/presentations/handlers.py`

### 6. Получение ресурсов пользователя в `project` плохо масштабируется

Сейчас `project-service`:
- ходит в `user-service` по страницам;
- потом для каждого ресурса отдельно тянет его окна доступности;
- при этом на каждый вызов создает новый `httpx.AsyncClient`.

Почему это проблема:
- много сетевых round-trip;
- высокий latency на списках ресурсов;
- под нагрузкой это даст каскадное замедление и лишние соединения.

Подтверждение в коде:
- `backend/src/apps/project/app/application/queries/resources.py`
- `backend/src/apps/project/app/presentation/http/user_service.py`

### 7. Конфигурация сервисов все еще dev-first

Сейчас в коде видно:
- `debug=True` у всех сервисов;
- `--reload` у `api-getaway` в compose;
- `echo=True` в SQLAlchemy-конфигах `auth` и `user`;
- cookie refresh-токена выставляется с `secure=False`.

Почему это проблема:
- слишком много dev-поведения зашито в рантайм;
- повышается риск утечки деталей реализации и чувствительных данных в логах;
- прод-конфигурация пока не выглядит как отдельный, жестко зафиксированный режим.

Подтверждение в коде:
- `backend/src/apps/auth/main.py`
- `backend/src/apps/user/main.py`
- `backend/src/apps/project/main.py`
- `backend/src/apps/apigetaway/main.py`
- `backend/src/apps/auth/app/config.py`
- `backend/src/apps/user/app/config.py`
- `backend/src/apps/auth/app/presentations/api.py`
- `docker-compose.yaml`

## Низкий

### 8. Тестовый контур слабо покрывает реальную security-схему

Интеграционные тесты `project` работают через прямую подстановку `X-User-Id`, а не через реальный сценарий `frontend -> api-getaway -> auth middleware -> project`.

Почему это проблема:
- тесты подтверждают business flow, но не подтверждают безопасность маршрута;
- интеграционный дефект на уровне gateway/headers/JWT может пройти незамеченным.

Подтверждение в коде:
- `backend/src/apps/project/tests/test_integration_api_http.py`

## Общая оценка слабых сторон

Главные слабости backend сейчас не в доменной модели, а в стыках:
- доверие между сервисами слишком сильное;
- межсервисные контракты не до конца стабилизированы;
- нет завершенной модели консистентности для reserve/release;
- prod-режим не отделен жестко от dev-режима.

Иными словами: локальная бизнес-логика уже выглядит осмысленно, но эксплуатационная надежность и безопасность распределенной системы еще не доведены.

## Что чинить первым

1. Согласовать и зафиксировать единый API-контракт reserve/release между `project` и `user`.
2. Сделать release/unreserve как полноценный публичный сценарий с компенсацией.
3. Зафиксировать production topology: наружу только `api-getaway`, внутренние сервисы только во внутренней сети.
4. Убрать доверие к "голому" `X-User-Id` как единственной линии защиты.
5. Довести refresh-session model: storage, revocation, logout, rotation policy.
6. Разделить dev/prod конфигурацию явно и жестко.
