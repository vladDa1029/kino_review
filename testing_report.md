# 4.3 Тестирование программного средства

## 4.3.1 Общие сведения

В рамках разработки микросервисной веб-платформы «Синхрокадр» проводилось тестирование четырёх сервисов в зоне ответственности автора: **user** (управление профилями, оборудованием и доступностью пользователей), **project** (управление проектами, сменами, участниками и ресурсными заявками), **notificate** (отправка уведомлений по электронной почте) и **apigateway** (шлюз, проксирующий запросы между клиентом и микросервисами).

Тестирование проводилось в два уровня:
- **модульное тестирование** — проверка отдельных команд, политик, спецификаций и доменных сервисов в изоляции с применением фейковых (in-memory) реализаций репозиториев и транспорта;
- **функциональное тестирование** — проверка HTTP-эндпоинтов через `TestClient` FastAPI с инъекцией зависимостей посредством Dishka-контейнера.

Тестовый фреймворк: **pytest 8.4.2**. Тесты запускались командой:
```
just test <service>
```
с переменными окружения, соответствующими `.env.example` каждого сервиса.

Сквозные (e2e) тесты запускались отдельно при поднятом Docker Compose-стеке:
```
KINO_E2E=1 uv run --directory backend/src/apps/apigateway pytest tests/test_reservation_email_e2e.py -v
```

---

## 4.3.2 Результаты запуска тестов

### Автономный прогон (без Docker)

| Сервис       | Всего тестов | Пройдено | Пропущено (e2e) | Упало |
|--------------|:---:|:---:|:---:|:---:|
| user         | 148 | 148 | 0   | 0   |
| project      | 96  | 96  | 0   | 0   |
| notificate   | 6   | 6   | 0   | 0   |
| apigateway   | 21  | 17  | 4   | 0   |
| **Итого**    | **271** | **267** | **4** | **0** |

### E2E-прогон (с запущенным Docker Compose-стеком)

| Идентификатор | Название теста | Статус |
|---|---|:---:|
| E2E-01 | `test_member_invite_validates_user_existence_via_broker_request_reply` | ✅ Пройден |
| E2E-02 | `test_participant_reservation_confirmation_flow_end_to_end` | ✅ Исправлен |
| E2E-03 | `test_resource_request_confirmation_flow_end_to_end` | ✅ Исправлен |
| E2E-04 | `test_generated_shift_report_flow_end_to_end` | ✅ Пройден |

### Сводная итоговая статистика (с E2E)

| Сервис       | Авт. пройдено | E2E пройдено | E2E упало | Всего |
|--------------|:---:|:---:|:---:|:---:|
| user         | 148 | —  | —  | 148 |
| project      | 96  | —  | —  | 96  |
| notificate   | 6   | —  | —  | 6   |
| apigateway   | 17  | 4  | 0  | 21  |
| **Итого**    | **267** | **4** | **0** | **271** |

---

## 4.3.3 Анализ результатов E2E-тестирования

Сквозные тесты запускались при полностью поднятом Docker Compose-стеке, включающем: `apigateway`, `auth`, `user`, `project`, `notificate`, `notificate-worker`, `project-worker`, `broker` (RabbitMQ), `pg` (PostgreSQL), `minio`, `mailhog`. Шлюз доступен по адресу `http://127.0.0.1:8000`, MailHog API — по `http://127.0.0.1:8025/api/v2/messages`.

### E2E-01 — Валидация существования пользователя через брокер при приглашении в проект ✅

**Сценарий:** директор регистрируется, создаёт проект, приглашает существующего участника по `user_id` — получает `200`; приглашает по несуществующему UUID — получает `404`.

**Результат:** пройден. Подтверждает корректность request-reply коммуникации между `project` и `user` через RabbitMQ: сервис project запрашивает существование пользователя у сервиса user до сохранения приглашения.

---

### E2E-02 — Полный цикл бронирования участника смены ✅ (исправлен)

**Ожидаемый сценарий:**
1. Директор и участник регистрируются.
2. Участник добавляет свободное окно доступности.
3. Директор создаёт проект и **приглашает участника в проект** (через email-ссылку; статус → ACTIVE).
4. Директор создаёт смену и приглашает участника в смену → `200`.
5. Участник подтверждает участие → запускается резервирование.
6. На email участника приходит письмо со ссылкой подтверждения.
7. Переход по ссылке подтверждает бронь → окно доступности переходит в `reserved`.
8. Повторный переход по той же ссылке возвращает `Already processed`.

**Исправление:** в тест добавлен вспомогательный метод `_invite_and_activate_project_member`, реализующий полный цикл приглашения в проект — от `POST /project/projects/{id}/members` до получения email-ссылки и ожидания перехода статуса участника в `ACTIVE`.

---

### E2E-03 — Полный цикл бронирования ресурса (камеры) ✅ (исправлен)

**Ожидаемый сценарий:**
1. Директор и владелец камеры регистрируются.
2. Владелец создаёт камеру и добавляет окно её доступности.
3. Директор создаёт проект и **добавляет владельца как участника** (через email-ссылку; статус → ACTIVE).
4. Директор создаёт смену и заявку на камеру → `200`.
5. Владелец одобряет заявку → запускается резервирование.
6. На email владельца приходит письмо со ссылкой подтверждения.
7. Переход по ссылке бронирует камеру → окно переходит в `reserved`.

**Исправление:** аналогично E2E-02 — добавлен вызов `_invite_and_activate_project_member` для владельца ресурса. Бизнес-логика проверяет (`app/application/commands/resources.py`) членство владельца в проекте до создания ресурсной заявки.

---

### E2E-04 — Генерация XLSX-отчёта смены ✅

**Сценарий:**
1. Директор создаёт проект, смену.
2. Смена утверждается директором.
3. Запускается генерация отчёта → статус `PENDING`.
4. Опрос (`_poll_until`) до перехода в статус `READY`.
5. Проверяется: `version == 1`, имя файла оканчивается на `.xlsx`, `actuality_status_name == "ACTUAL"`.
6. Список отчётов смены содержит ровно один отчёт.
7. Получен URL для скачивания, содержащий `.xlsx`.

**Результат:** пройден. Подтверждает полный цикл асинхронной генерации XLSX-отчёта: от запроса через шлюз, создания задачи в TaskIQ, получения снимка данных у `user`-сервиса — до загрузки файла в MinIO и получения presigned URL.

---

## 4.3.4 Таблица модульных тестов

### Условные обозначения

- **Статус**: ✅ Пройден / ⏭ Пропущен (e2e)
- Файлы расположены в `backend/src/apps/<service>/test[s]/`

### Сервис user

| № | Идентификатор | Тестируемый компонент | Описание теста | Входные данные | Ожидаемый результат | Фактический результат | Статус |
|---|---|---|---|---|---|---|---|
| 1 | MT-01 | `healthcheck()` (user) | Эндпоинт `/health` возвращает `{"status": "ok"}` | — | `{"status": "ok"}` | `{"status": "ok"}` | ✅ |
| 2 | MT-02 | `router` (user) | Маршрут `/health` зарегистрирован в роутере | — | Маршрут существует | Маршрут найден | ✅ |
| 3 | MT-03 | `AddSpareTimeHandler` | Команда добавления временного окна доступности сохраняется и коммитит транзакцию | `user_id`, `start_time=2024-01-02T10:00`, `end_time=2024-01-02T12:00` | 1 запись в репозитории, 1 коммит | 1 запись, коммит = 1, откат = 0 | ✅ |
| 4 | MT-04 | `CheckAvailabilityHandler` | Проверка доступности не изменяет данные (read-only) | Пользователь активен, окно `10:00–14:00`, запрос `11:00–12:00` | `added == [], deleted == []` | Состояние репозитория не изменилось | ✅ |
| 5 | MT-05 | `CheckAvailabilityHandler` | Отсутствие свободного окна вызывает `AvailabilityNotFoundError` | Пустой репозиторий свободного времени | `AvailabilityNotFoundError` | Исключение поднято | ✅ |
| 6 | MT-06 | `CheckAvailabilityHandler` | Ресурс, принадлежащий другому пользователю, отклоняется (`OwnershipError`) | `owner_id` ≠ `user_id` камеры | `OwnershipError` | Исключение поднято | ✅ |
| 7 | MT-07 | `ReserveAvailabilityHandler` | Бронирование разбивает свободное окно на три части (до/резервация/после) и коммитит | Окно `10:00–14:00`, бронь `11:00–12:00` | 3 добавленных записи, 1 коммит | Верно | ✅ |
| 8 | MT-08 | `ReserveAvailabilityHandler` | Идемпотентность: повторный вызов с тем же `request_id` возвращает уже существующий `reservation_id` | Запись с `request_id` уже есть в репозитории | Возвращается сохранённый `reservation_id` | Верно | ✅ |
| 9 | MT-09 | `ReserveAvailabilityHandler` | Резервирование оборудования (Camera) использует репозиторий `camera_free_time` | Camera с `resource_id` принадлежит пользователю | Окно обновлено в `camera_free_time_repo`, `spare_time_repo` не изменён | Верно | ✅ |
| 10 | MT-10 | `ReserveAvailabilityHandler` | Чужой ресурс отклоняется (`OwnershipError`), транзакция не коммитится | `camera.users_id` ≠ `user_id` | `OwnershipError`, коммит = 0 | Верно | ✅ |
| 11 | MT-11 | `CreateDescriptionHandler` | Создание профиля пользователя сохраняется и коммитит | `username="user"`, `phone="89001234567"` | 1 запись в репозитории, коммит = 1 | Верно | ✅ |
| 12 | MT-12 | `UpdateDescriptionHandler` | Обновление профиля меняет поля и коммитит | `username="new"`, `phone="89001112233"` | `description.username == "new"`, коммит = 1 | Верно | ✅ |
| 13 | MT-13 | `CreateMicrofonHandler` | Создание микрофона сохраняет сущность с корректными полями | `title="mic"`, `type="shotgun"` | `microfon.oid == microfon_id`, коммит = 1 | Верно | ✅ |
| 14 | MT-14 | `CreateMicrofonHandler` | Отсутствующий пользователь вызывает `UserNotFoundError` | `user_repo.get()` возвращает `None` | `UserNotFoundError`, коммит = 0 | Верно | ✅ |
| 15 | MT-15 | `CreateMicrofonHandler` | Неактивный пользователь вызывает `UserInactiveError` и откат | `user.is_active = False` | `UserInactiveError`, откат = 1 | Верно | ✅ |
| 16 | MT-16 | `CreateEquipmentHandler` (Camera, CameraTripod, Light, LightTripod, Sound, Requisite) | Параметризованный тест: каждый тип оборудования создаётся с корректными полями и коммитит | Соответствующие данные для 6 типов | Сущность нужного класса в репозитории, коммит = 1 | Верно для всех 6 случаев | ✅ |
| 17 | MT-17 | `DeleteEquipmentHandler` (7 типов) | Параметризованный тест: оборудование удаляется из репозитория, коммит выполняется | Идентификатор существующего объекта | Сущность помечена к удалению, коммит = 1 | Верно для всех 7 типов | ✅ |
| 18 | MT-18 | `UpdateEquipmentHandler` (7 типов) | Параметризованный тест: обновление свойств оборудования | Новые `title`, `type` и т.д. | Поля изменены, коммит = 1 | Верно для всех 7 типов | ✅ |
| 19 | MT-19 | `AddImageHandler` | Загрузка изображения к реквизиту сохраняет запись и коммитит | Бинарные данные изображения, `requisite_id` | 1 запись в репозитории, коммит = 1 | Верно | ✅ |
| 20 | MT-20 | `RemoveImageHandler` | Удаление изображения фиксируется в репозитории | `image_id`, `user_id` (владелец) | Запись удалена, коммит = 1 | Верно | ✅ |
| 21 | MT-21 | `prepare_file_storage` (local) | При локальном бэкенде создаётся директория бакета | `STORAGE_BACKEND="local"`, `STORAGE_BUCKET="user"` | `result.bucket_created is True`, директория существует | Верно | ✅ |
| 22 | MT-22 | `prepare_file_storage` (S3) | При отсутствующем S3-бакете создаётся новый | `FakeS3Client(missing_bucket=True)` | `head_calls == ["user"]`, `create_calls == [{"Bucket": "user"}]` | Верно | ✅ |
| 23 | MT-23 | `JWTConfirmationTokenService` | Изменённый или просроченный токен обнаруживается | Токен с неверной подписью / истёкший токен | `TokenError` | Исключение поднято | ✅ |
| 24 | MT-24 | `HandleParticipantApprovalRequestedHandler` | При запросе на согласование участника публикуется email-событие | `participant_id`, данные смены | Событие в очереди FakePublisher | Верно | ✅ |
| 25 | MT-25 | `HandleProjectMemberInvitationRequestedHandler` | При приглашении участника проекта публикуется email-событие | `user_id`, `project_title`, `role` | Событие в очереди | Верно | ✅ |
| 26 | MT-26 | `ConfirmReservationByTokenHandler` | Подтверждение бронирования по токену резервирует доступность и публикует успех | Валидный JWT-токен, свободное окно | `reservation_id` возвращён, событие SUCCESS опубликовано | Верно | ✅ |
| 27 | MT-27 | `ConfirmReservationByTokenHandler` | Повторный вызов (состояние не RESERVING) возвращает `already_processed` | Статус участника ≠ RESERVING | Флаг `already_processed` | Верно | ✅ |
| 28 | MT-28 | `ProjectApprovalStateBrokerClient` | Запрос состояния участника публикует событие и получает ответ через inbox | Брокер возвращает `PARTICIPANT_APPROVAL_STATE_PROVIDED` | Состояние с полями `project_title`, `shift_title` | Верно | ✅ |
| 29 | MT-29 | `ProjectApprovalStateBrokerClient` | Таймаут при ожидании ответа вызывает исключение и очищает waiter | `timeout_seconds=0.01`, нет ответа | Исключение, waiter удалён | Верно | ✅ |
| 30 | MT-30 | `ProvideShiftReportSnapshotHandler` | Снимок отчёта смены возвращает данные пользователя и ресурса | `user_id`, `resource_id` с данными в репозиториях | `username`, `phone`, `email`, `title` заполнены | Верно | ✅ |
| 31 | MT-31 | `ProvideShiftReportSnapshotHandler` | При отсутствии данных поля снимка содержат `None` | Пустые репозитории | Все поля = `None` | Верно | ✅ |
| 32 | MT-32 | `ProvideShiftReportSnapshotHandler` | Ресурс, принадлежащий другому пользователю, игнорируется | `resource.users_id` ≠ `owner_user_id` | `title == None` | Верно | ✅ |
| 33 | MT-33 | `ActiveUserPolicy`, `OwnershipPolicy` и др. (доменные политики user) | Параметризованные тесты: активный/неактивный пользователь, соответствие владельца, наличие описания и т.д. | Комбинации флагов `is_active`, `is_owner` | Соответствующие ошибки или `None` | Верно для всех комбинаций | ✅ |
| 34 | MT-34 | `AvailabilityService` | Резервирование делит окно, отмена бронирования объединяет свободные окна | Различные комбинации временных окон | Корректные переходы статусов | Верно | ✅ |
| 35 | MT-35 | `EquipmentService` | Операции create/update/delete соблюдают политики (активность, владение, блокировка) | Комбинации `is_active`, `is_owner`, `locked_statuses` | Ошибки или успех в соответствии с правилами | Верно | ✅ |

### Сервис project

| № | Идентификатор | Тестируемый компонент | Описание теста | Входные данные | Ожидаемый результат | Фактический результат | Статус |
|---|---|---|---|---|---|---|---|
| 36 | MT-36 | `TimeInterval` | Невалидный интервал (start == end) вызывает `DomainInvariantError` | `start = now, end = now` | `DomainInvariantError` | Исключение поднято | ✅ |
| 37 | MT-37 | `ProjectMembershipService.invite_member` | Приглашение участника требует роль DIRECTOR | `actor.role = ACTOR` | `AccessDeniedError` | Исключение поднято | ✅ |
| 38 | MT-38 | `ProjectMembershipService.activate_member` | Активация переводит статус INVITED → ACTIVE | `member.status = INVITED` | `member.status == ACTIVE` | Верно | ✅ |
| 39 | MT-39 | `ProjectMembershipService.activate_member` | Активация не-INVITED участника вызывает `StateTransitionError` | `member.status = ACTIVE` | `StateTransitionError` | Верно | ✅ |
| 40 | MT-40 | `ShiftParticipantService.invite` | Временной интервал участника должен лежать внутри интервала смены | `time_from` раньше начала смены | `StateTransitionError` | Верно | ✅ |
| 41 | MT-41 | `ResourceRequestService.create` | Только роли с разрешением на ресурсы могут создавать заявку | `actor.role = ACTOR` (не имеет права) | `AccessDeniedError` | Верно | ✅ |
| 42 | MT-42 | `ActiveMemberPolicy` | Неактивный участник (статус INVITED) не проходит политику | `member.status = INVITED` | `AccessDeniedError` | Верно | ✅ |
| 43 | MT-43 | `DirectorMemberPolicy` | Не-DIRECTOR не проходит политику | `member.role = ACTOR` | `AccessDeniedError` | Верно | ✅ |
| 44 | MT-44 | `EditableShiftSpecification` | Смена в статусе DRAFT — редактируемая; APPROVED — нет | `status=DRAFT`, `status=APPROVED` | `True`, `False` | Верно | ✅ |
| 45 | MT-45 | `IntervalWithinShiftSpecification` | Интервал внутри смены — соответствует; выходящий — нет | Внутренний и внешний интервалы | `True`, `False` | Верно | ✅ |
| 46 | MT-46 | `CreateProjectHandler` | Создание проекта коммитит и публикует событие | `title="Feature film"` | Проект в репозитории, событие опубликовано | Верно | ✅ |
| 47 | MT-47 | `InviteProjectMemberHandler` | Приглашение участника проверяет существование пользователя через брокер | Брокер возвращает `user_exists=True` | Участник добавлен | Верно | ✅ |
| 48 | MT-48 | `InviteProjectMemberByEmailHandler` | Поиск пользователя по email через брокер | Email → `user_id` через lookup | Участник создан с корректным `user_id` | Верно | ✅ |
| 49 | MT-49 | `DeleteProjectHandler` | Удаление проекта архивирует его и публикует событие; не-директор получает отказ | Не-директор пробует удалить | `AccessDeniedError` | Верно | ✅ |
| 50 | MT-50 | `UpdateProjectHandler` | Обновление с пустым payload вызывает ошибку; обновление с пробельным title — тоже | `title="   "` | Ошибка валидации | Верно | ✅ |
| 51 | MT-51 | `GenerateShiftReportHandler` | Генерация отчёта создаёт запись PENDING и планирует задачу; второй вызов до завершения отклоняется | Двойной вызов | Второй вызов: ошибка «уже в процессе» | Верно | ✅ |
| 52 | MT-52 | `ProcessShiftReportGenerationHandler` | Генерация XLSX-отчёта помечает его READY; ошибка снимка помечает FAILED | Снимок с данными / ошибка | Статус READY / FAILED | Верно | ✅ |
| 53 | MT-53 | `ProcessReservationOutboxHandler` | Обработчик outbox рассылает запросы на бронирование участников и ресурсов | Записи `OUTBOX_STATUS_PENDING` | Запросы опубликованы | Верно | ✅ |
| 54 | MT-54 | `HandleParticipantReservationCheckSucceededHandler` | После успешной проверки доступности публикуется запрос на подтверждение | Событие `CHECK_SUCCEEDED` | Запрос approval опубликован | Верно | ✅ |
| 55 | MT-55 | `to_project_role_input`, `_report_actuality_status` (runtime) | Целочисленные значения из ORM корректно преобразуются в enum | `int(ProjectRole.SOUND)` | `ProjectRoleInput.SOUND` | Верно | ✅ |
| 56 | MT-56 | `UserServiceHttpClient.ensure_user_exists` | Запрос существования пользователя публикует событие и ожидает reply | Брокер возвращает `user_exists=True` | Метод завершается без исключений | Верно | ✅ |
| 57 | MT-57 | `UserServiceHttpClient.ensure_user_exists` | Отсутствующий пользователь → `EntityNotFoundError`; таймаут → `ExternalServiceError` | `user_exists=False` / нет ответа | Соответствующие исключения | Верно | ✅ |
| 58 | MT-58 | `ShiftReportRenderer` | XLSX-рендерер использует русскоязычные метки столбцов | Данные участников и ресурсов | Метки на русском в ячейках | Верно | ✅ |
| 59 | MT-59 | `ensure_minio_bucket` (project) | Отсутствующий Minio-бакет создаётся; существующий — не пересоздаётся | `missing=True` / `missing=False` | Бакет создан / не создан | Верно | ✅ |
| 60 | MT-60 | `create_taskiq_broker` (project) | Брокер TaskIQ использует project-специфичные exchange/queue | Конфиг по умолчанию | `_exchange_name == "project.taskiq"` | Верно | ✅ |
| 61 | MT-61 | `test_api_lifespan_starts_and_stops_task_manager` | Lifespan приложения корректно запускает и останавливает TaskIQ task manager | Запуск FastAPI lifespan | Менеджер задач стартовал и остановился без ошибок | Верно | ✅ |

### Сервис notificate

| № | Идентификатор | Тестируемый компонент | Описание теста | Входные данные | Ожидаемый результат | Фактический результат | Статус |
|---|---|---|---|---|---|---|---|
| 62 | MT-62 | `ScheduleNotificationEmailHandler` | Команда планирования email передаётся в диспетчер | `notification_id`, `recipient_email`, шаблон `reservation_confirmation` | `dispatcher.commands == [command]` | Верно | ✅ |
| 63 | MT-63 | `SendNotificationEmailHandler` | Письмо подтверждения бронирования содержит нужные поля | Шаблон `reservation_confirmation`, данные смены | `body` содержит `"Feature film"`, URL подтверждения, роль | Верно | ✅ |
| 64 | MT-64 | `SendNotificationEmailHandler` | При наличии `resource_type` в теле письма отображается тип ресурса | `resource_type="camera"` | `"Resource type: camera"` в теле | Верно | ✅ |
| 65 | MT-65 | `SendNotificationEmailHandler` | Письмо-приглашение в проект содержит нужные поля | Шаблон `project_member_invitation`, `role="CAMERA"` | `body` содержит `"Feature film"`, `"Role: CAMERA"`, URL | Верно | ✅ |
| 66 | MT-66 | `TaskiqNotificationTaskDispatcher` | Диспетчер вызывает зарегистрированную taskiq-задачу с корректными параметрами | `notification_id="notif-2"`, шаблон | `task.calls == [{...правильные поля...}]` | Верно | ✅ |
| 67 | MT-67 | `create_taskiq_broker` (notificate) | Брокер использует notificate-специфичные exchange/queue/DLQ | Конфиг по умолчанию | `_exchange_name == "notificate.taskiq"` | Верно | ✅ |

### Сервис apigateway

| № | Идентификатор | Тестируемый компонент | Описание теста | Входные данные | Ожидаемый результат | Фактический результат | Статус |
|---|---|---|---|---|---|---|---|
| 68 | MT-68 | `healthcheck()` (apigateway) | Эндпоинт `/health` возвращает `{"status": "ok"}` | — | `{"status": "ok"}` | Верно | ✅ |
| 69 | MT-69 | `router` (apigateway) | Маршрут `/health` зарегистрирован в роутере | — | Маршрут существует | Верно | ✅ |
| 70 | MT-70 | `ensure_admin_payload` | Суперпользователь пропускается без ошибок | `{"is_superuser": True}` | `None` (нет исключения) | Верно | ✅ |
| 71 | MT-71 | `ensure_admin_payload` | Не-суперпользователь вызывает `AccessDeniedError` | `{"is_superuser": False}` | `AccessDeniedError("Admin access required.")` | Верно | ✅ |
| 72 | MT-72 | `access_denied_error_handler` | Обработчик ошибок возвращает HTTP 403 с телом JSON | `AccessDeniedError("Admin access required.")` | `status_code=403`, `body='{"detail":"Admin access required."}'` | Верно | ✅ |
| 73 | MT-73 | Страница документации (`/`) | Хаб документации содержит ссылку на `/admin/user/docs` | GET `/` | `href="/admin/user/docs"` в HTML | Верно | ✅ |
| 74 | MT-74 | `_apply_admin_headers` | Поддельный заголовок `x-user-is-superuser` удаляется из запроса | Запрос с `x-user-is-superuser: spoofed` | Заголовок удалён, установлен `x-user-id` из сессии | Верно | ✅ |
| 75 | MT-75 | `proxy_admin_users` | Не-суперпользователь получает `AccessDeniedError` до вызова бэкенда | `is_superuser=False` | `AccessDeniedError`, backend не вызван | Верно | ✅ |
| 76 | MT-76 | `build_user_headers` | При `is_superuser=True` заголовок `x-user-is-superuser: "true"` включается | `is_superuser=True` | Словарь с тремя ключами, включая `"true"` | Верно | ✅ |
| 77 | MT-77 | `ProtectedPathsSettings` | Пути `/project/reports/*` и `/user/project-invitations/*` считаются защищёнными | Паттерны по умолчанию | `fnmatch` возвращает `True` | Верно | ✅ |
| 78 | MT-78 | `ProtectedPathsSettings` | Путь `/user/project-invitations/*` защищён даже при переопределении `PROTECTED_PATH_PATTERNS` | Переопределение `{"user": ["/user/users/*"]}` | Путь `/user/project-invitations/token` всё равно защищён | Верно | ✅ |
| 79 | MT-79 | `strip_header_parameter` | Внутренние заголовки `X-User-Token-Type`, `X-User-Is-Superuser` удаляются из OpenAPI-спецификации | Spec с 3 параметрами, 2 из которых — внутренние | Остаётся только `"page"` | Верно | ✅ |
| 80 | MT-80 | `mark_protected_endpoints_with_security` | Защищённые эндпоинты получают пометку Bearer в OpenAPI | Операция без `security` | Поле `security` добавлено | Верно | ✅ |
| 81 | MT-81 | `AuthGatewayMiddleware` | Запрос к публичному пути `/user/confirmations/*` проходит без аутентификации | GET `/user/confirmations/test-token` без заголовка | HTTP 200 | Верно | ✅ |
| 82 | MT-82 | `AuthGatewayMiddleware` | Запрос к защищённому пути `/user/project-invitations/*` без токена → HTTP 401 | GET `/user/project-invitations/test-token` без токена | HTTP 401, `{"detail": "Not authenticated"}` | Верно | ✅ |
| 83 | MT-83 | `AuthGatewayMiddleware` | При аутентифицированном запросе заголовки `x-user-id`, `x-user-token-type` устанавливаются корректно | GET с `Authorization: Bearer <token>` | `request.state.user_headers` содержит `x-user-id: "user-123"` | Верно | ✅ |
| 84 | MT-84 (e2e) | Сквозной сценарий: резервирование через email-подтверждение | Полный цикл: участник → email → подтверждение → бронь | Все сервисы запущены | Резервация записана | ⏭ Пропущен (требует Docker) |
| 85 | MT-85 (e2e) | Сквозной сценарий: ресурсная заявка через email-подтверждение | Полный цикл | Все сервисы запущены | Ресурс забронирован | ⏭ Пропущен (требует Docker) |
| 86 | MT-86 (e2e) | Сквозной сценарий: приглашение участника проекта | Полный цикл | Все сервисы запущены | Участник добавлен | ⏭ Пропущен (требует Docker) |
| 87 | MT-87 (e2e) | Сквозной сценарий: генерация отчёта смены | Полный цикл | Все сервисы запущены | XLSX-файл создан | ⏭ Пропущен (требует Docker) |

### Негативные сценарии — сервис user (добавлены)

| № | Идентификатор | Тестируемый компонент | Описание теста | Входные данные | Ожидаемый результат | Фактический результат | Статус |
|---|---|---|---|---|---|---|---|
| 88 | MT-88 | `AddSpareTimeHandler` / `FreeTimeService` | Добавление пересекающегося окна доступности вызывает `CrossingTimingError`, транзакция откатывается | Существующее окно `10:00–14:00`, новое `12:00–16:00` (пересечение) | `CrossingTimingError`, откат = 1, коммит = 0 | Исключение поднято, откат выполнен | ✅ |
| 89 | MT-89 | `AddSpareTimeHandler` / `FreeTimeService` | Окно, полностью входящее в существующее, тоже вызывает `CrossingTimingError` | Существующее `08:00–18:00`, новое `10:00–12:00` | `CrossingTimingError`, откат = 1 | Исключение поднято | ✅ |
| 90 | MT-90 | `DeleteCameraHandler` / `EquipmentService` | Удаление камеры с забронированным окном доступности вызывает `ResourceLockedError` | Камера с окном в статусе `reserved` | `ResourceLockedError`, оборудование не удалено, откат = 1 | Исключение поднято, удаление не выполнено | ✅ |
| 91 | MT-91 | `UpdateCameraHandler` / `EquipmentService` | Обновление камеры с забронированным окном вызывает `ResourceLockedError` | Камера с окном в статусе `reserved` | `ResourceLockedError`, обновление не зафиксировано, откат = 1 | Исключение поднято | ✅ |
| 92 | MT-92 | `CreateDescriptionHandler` / `DescriptionService` | Повторное создание профиля для того же пользователя вызывает `DescriptionAlreadyExistsError` | Пользователь с уже существующим профилем | `DescriptionAlreadyExistsError`, новая запись не добавлена, откат = 1 | Исключение поднято, данные не изменены | ✅ |

### Негативные HTTP-сценарии — сервис project (добавлены)

| № | Идентификатор | Тестируемый компонент | Описание теста | Входные данные | Ожидаемый результат | Фактический результат | Статус |
|---|---|---|---|---|---|---|---|
| 93 | MT-93 | `GET /projects/{id}` | Запрос несуществующего проекта → 404 | UUID без соответствующего проекта | HTTP 404 | HTTP 404 | ✅ |
| 94 | MT-94 | `GET /projects/{id}` | Доступ к проекту от пользователя, не являющегося участником → 403 | `X-User-Id` постороннего пользователя | HTTP 403 | HTTP 403 | ✅ |
| 95 | MT-95 | `GET /projects/{id}/members/{uid}` | Запрос несуществующего участника → 404 | `user_id` без соответствующей записи участника | HTTP 404 | HTTP 404 | ✅ |
| 96 | MT-96 | `DELETE /projects/{id}` | Не-директор пытается удалить проект → 403 | Участник с ролью CAMERA (активный) | HTTP 403 | HTTP 403 | ✅ |
| 97 | MT-97 | `POST /projects/{id}/members` | Не-директор пытается пригласить нового участника → 403 | Участник с ролью CAMERA пытается пригласить другого | HTTP 403 | HTTP 403 | ✅ |
| 98 | MT-98 | `PATCH /projects/{id}/members/{uid}/role` | Не-директор пытается изменить роль участника → 403 | Участник с ролью CAMERA | HTTP 403 | HTTP 403 | ✅ |
| 99 | MT-99 | `POST /shifts/{id}/reports/generate` | Не-директор запрашивает генерацию отчёта → 403 | Участник с ролью CAMERA; смена в статусе APPROVED | HTTP 403 | HTTP 403 | ✅ |
| 100 | MT-100 | `POST /shifts/{id}/participants` | Временной интервал участника выходит за пределы смены → 409 | `time_from` за 1 час до начала смены | HTTP 409 (`StateTransitionError`) | HTTP 409 | ✅ |
| 101 | MT-101 | `POST /shifts/{id}/approve` | Повторное утверждение уже одобренной смены → 409 | Смена уже в статусе APPROVED | HTTP 409 | HTTP 409 | ✅ |
| 102 | MT-102 | `POST /projects` | Отсутствие обязательного поля `title` → 422 | `{"description": "no title"}` | HTTP 422 (ошибка Pydantic) | HTTP 422 | ✅ |
| 103 | MT-103 | `PATCH /projects/{id}` | Пустое тело PATCH-запроса → 409 (доменная валидация) | `{}` | HTTP 409 (`StateTransitionError`) | HTTP 409 | ✅ |
| 104 | MT-104 | `POST /projects/{id}/members` | Приглашение с несуществующей ролью → 422 | `{"role": "NONEXISTENT_ROLE"}` | HTTP 422 | HTTP 422 | ✅ |
| 105 | MT-105 | `POST /projects/{id}/shifts` | Создание смены с `end_time` раньше `start_time` → 400 или 422 | Перевёрнутый интервал | HTTP 400 или 422 | HTTP 400 | ✅ |

---

## 4.3.5 Таблица функциональных тест-кейсов

Функциональные тест-кейсы описывают проверку HTTP-эндпоинтов сервисов на соответствие требованиям технического задания (п. А.3.1). Тесты выполняются через `FastAPI TestClient` с in-memory репозиториями (файл `test_api_crud_workflows.py`, `test_integration_api_http.py`).

### Сервис user — HTTP-эндпоинты

| № | Идентификатор | URL | Метод | Тело запроса / параметры | Ожидаемый статус | Описание проверки | Требование ТЗ |
|---|---|---|---|---|---|---|---|
| 1 | FT-01 | `/health` | GET | — | 200 | Сервис жив и отвечает | — |
| 2 | FT-02 | `/users/{user_id}/description` | POST | `{"username": "Ivan", "phone": "89001234567"}` | 201 | Создание профиля пользователя | Р-03 |
| 3 | FT-03 | `/users/{user_id}/description` | GET | — | 200 | Получение профиля пользователя | Р-03 |
| 4 | FT-04 | `/users/{user_id}/description/{desc_id}` | PUT | `{"username": "New Name"}` | 200 | Обновление профиля | Р-03 |
| 5 | FT-05 | `/users/{user_id}/spare-times` | POST | `{"start_time": "...", "end_time": "..."}` | 201 | Добавление временного окна доступности | Р-05 |
| 6 | FT-06 | `/users/{user_id}/spare-times` | GET | — | 200 | Список временных окон | Р-05 |
| 7 | FT-07 | `/users/{user_id}/spare-times/{id}` | GET | — | 200 | Получение конкретного временного окна | Р-05 |
| 8 | FT-08 | `/users/{user_id}/spare-times/{id}` | PUT | `{"start_time": "...", "end_time": "..."}` | 200 | Обновление временного окна | Р-05 |
| 9 | FT-09 | `/users/{user_id}/spare-times/{id}` | DELETE | — | 204 | Удаление временного окна | Р-05 |
| 10 | FT-10 | `/users/{user_id}/availability/reserve` | POST | `{"request_id": "...", "obj_id": "...", "start_time": "...", "end_time": "..."}` | 200 | Бронирование окна доступности | Р-06 |
| 11 | FT-11 | `/confirmations/{token}` | GET | — | 200 | Подтверждение бронирования по токену из письма (возвращает HTML) | Р-06 |
| 12 | FT-12 | `/project-invitations/{token}` | GET | `X-User-Id: <uuid>` | 200 | Принятие приглашения в проект по токену | Р-04 |
| 13 | FT-13 | `/users/{user_id}/microfons` | POST | `{"title": "Rode", "type": "shotgun", "description": "..."}` | 201 | Добавление микрофона | Р-07 |
| 14 | FT-14 | `/users/{user_id}/microfons` | GET | `?page=1&page_size=10` | 200 | Список микрофонов с пагинацией | Р-07 |
| 15 | FT-15 | `/users/{user_id}/microfons/{id}` | PUT | `{"title": "Updated"}` | 200 | Обновление микрофона | Р-07 |
| 16 | FT-16 | `/users/{user_id}/microfons/{id}` | DELETE | — | 204 | Удаление микрофона | Р-07 |
| 17 | FT-17 | `/users/{user_id}/cameras` | POST | `{"title": "Sony A7", "type": "mirrorless", "description": "..."}` | 201 | Добавление камеры | Р-07 |
| 18 | FT-18 | `/users/{user_id}/lights` | POST | `{"title": "Aputure", "type": "led", "description": "..."}` | 201 | Добавление осветительного оборудования | Р-07 |
| 19 | FT-19 | `/users/{user_id}/sounds` | POST | `{"title": "Zoom H6", "type": "field", "description": "..."}` | 201 | Добавление звукового оборудования | Р-07 |
| 20 | FT-20 | `/users/{user_id}/requisites` | POST | `{"title": "Шляпа", "type": "costume", "size": "m", "description": "..."}` | 201 | Добавление реквизита | Р-07 |
| 21 | FT-21 | `/users/{user_id}/requisites/{req_id}/images` | POST | `multipart/form-data: file, title, description` | 201 | Загрузка изображения для реквизита | Р-07 |
| 22 | FT-22 | `/users/{user_id}/requisites/{req_id}/images` | GET | — | 200 | Список изображений реквизита | Р-07 |
| 23 | FT-23 | `/users/{user_id}/requisites/{req_id}/images/{img_id}` | DELETE | — | 204 | Удаление изображения реквизита | Р-07 |
| 24 | FT-24 | `/users/{user_id}` | GET | — | 200 / 404 | Проверка существования пользователя (используется сервисом project) | — |

### Сервис project — HTTP-эндпоинты

| № | Идентификатор | URL | Метод | Тело запроса / параметры | Ожидаемый статус | Описание проверки | Требование ТЗ |
|---|---|---|---|---|---|---|---|
| 25 | FT-25 | `/health` | GET | — | 200 | Сервис жив | — |
| 26 | FT-26 | `/projects` | POST | `{"title": "Feature film", "description": "..."}` | 201 | Создание проекта | Р-01 |
| 27 | FT-27 | `/projects` | GET | `X-User-Id: <uuid>` | 200 | Список проектов текущего пользователя | Р-01 |
| 28 | FT-28 | `/projects/{id}` | GET | `X-User-Id: <member_id>` | 200 | Получение проекта (только для участника) | Р-01 |
| 29 | FT-29 | `/projects/{id}` | PATCH | `{"title": "New title"}` | 200 | Обновление проекта | Р-01 |
| 30 | FT-30 | `/projects/{id}` | PATCH | `{}` (пустой payload) | 409 | Пустой PATCH отклоняется (`StateTransitionError` — доменная валидация) | Р-01 |
| 31 | FT-31 | `/projects/{id}` | DELETE | `X-User-Id: <director_id>` | 204 | Архивирование проекта (только директор) | Р-01 |
| 32 | FT-32 | `/projects/{id}/members` | POST | `{"user_id": "...", "role": "CAMERA"}` | 201 | Приглашение участника по UUID | Р-02 |
| 33 | FT-33 | `/projects/{id}/members/by-email` | POST | `{"email": "user@example.com", "role": "SOUND"}` | 201 | Приглашение участника по email | Р-02 |
| 34 | FT-34 | `/projects/{id}/members` | GET | — | 200 | Список участников проекта | Р-02 |
| 35 | FT-35 | `/projects/{id}/members/{user_id}` | GET | — | 200 | Данные конкретного участника | Р-02 |
| 36 | FT-36 | `/projects/{id}/members/{user_id}/role` | PATCH | `{"role": "LIGHT"}` | 200 | Изменение роли участника | Р-02 |
| 37 | FT-37 | `/projects/{id}/members/{user_id}` | DELETE | `X-User-Id: <director_id>` | 204 | Удаление участника из проекта | Р-02 |
| 38 | FT-38 | `/projects/{id}/shifts` | POST | `{"title": "Ночная съёмка", "start_time": "...", "end_time": "..."}` | 201 | Создание смены | Р-08 |
| 39 | FT-39 | `/shifts/{id}/approve` | POST | `X-User-Id: <director_id>` | 200 | Утверждение смены директором | Р-08 |
| 40 | FT-40 | `/shifts/{id}/participants` | POST | `{"user_id": "...", "role": "ACTOR", "time_from": "...", "time_to": "..."}` | 201 | Добавление участника в смену | Р-09 |
| 41 | FT-41 | `/participants/{id}/confirm` | POST | `X-User-Id: <participant_user_id>` | 200 | Подтверждение участия в смене | Р-09 |
| 42 | FT-42 | `/participants/{id}/decline` | POST | `X-User-Id: <participant_user_id>` | 200 | Отказ от участия в смене | Р-09 |
| 43 | FT-43 | `/shifts/{id}/documents` | POST | `multipart/form-data: file, document_type` | 201 | Загрузка документа (сценарий/план) к смене | Р-10 |
| 44 | FT-44 | `/documents/{id}/download-url` | GET | — | 200 | Получение URL для скачивания документа | Р-10 |
| 45 | FT-45 | `/shifts/{id}/resource-requests` | POST | `{"resource_type": "camera", "resource_id": "...", ...}` | 201 | Создание заявки на оборудование | Р-11 |
| 46 | FT-46 | `/resource-requests/{id}/approve` | POST | `X-User-Id: <owner_id>` | 200 | Подтверждение заявки владельцем ресурса | Р-11 |
| 47 | FT-47 | `/resource-requests/{id}/reject` | POST | `{"reason": "Недоступно"}` | 200 | Отклонение заявки с указанием причины | Р-11 |
| 48 | FT-48 | `/shifts/{id}/reports/generate` | POST | `X-User-Id: <director_id>` | 201 | Генерация XLSX-отчёта о смене | Р-12 |
| 49 | FT-49 | `/shifts/{id}/reports` | GET | — | 200 | Список отчётов смены | Р-12 |
| 50 | FT-50 | `/reports/{id}` | GET | — | 200 | Метаданные отчёта | Р-12 |
| 51 | FT-51 | `/reports/{id}/download-url` | GET | — | 200 | Получение URL для скачивания отчёта | Р-12 |
| 52 | FT-52 | `/reports/{id}` | DELETE | `X-User-Id: <director_id>` | 204 | Архивирование отчёта | Р-12 |
| 53 | FT-53 | `/admin/projects` | GET | `X-User-Is-Superuser: true` | 200 | Административный список всех проектов | Р-13 |
| 54 | FT-54 | `/admin/projects/{id}` | GET | `X-User-Is-Superuser: true` | 200 | Административное получение проекта | Р-13 |
| 55 | FT-55 | `/admin/projects/{id}/members` | GET | `X-User-Is-Superuser: true` | 200 | Административный список участников | Р-13 |

### Сервис notificate — HTTP-эндпоинты

| № | Идентификатор | URL | Метод | Тело запроса / параметры | Ожидаемый статус | Описание проверки | Требование ТЗ |
|---|---|---|---|---|---|---|---|
| 56 | FT-56 | `/health` | GET | — | 200 | Сервис жив и отвечает | — |

### Сервис apigateway — HTTP-эндпоинты и middleware

| № | Идентификатор | URL | Метод | Тело запроса / параметры | Ожидаемый статус | Описание проверки | Требование ТЗ |
|---|---|---|---|---|---|---|---|
| 57 | FT-57 | `/health` | GET | — | 200 | Шлюз жив | — |
| 58 | FT-58 | `/user/confirmations/{token}` | GET | Без заголовка авторизации | 200 | Публичный путь подтверждения не требует токен | Р-06 |
| 59 | FT-59 | `/user/project-invitations/{token}` | GET | Без заголовка авторизации | 401 | Защищённый путь приглашения требует токен | Р-04 |
| 60 | FT-60 | `/user/project-invitations/{token}` | GET | `Authorization: Bearer <valid_token>` | 200 | Аутентифицированный запрос проходит с заголовками пользователя | Р-04 |
| 61 | FT-61 | `/admin/user/{path}` | ANY | Без `is_superuser: true` | 403 | Не-суперпользователь отклоняется до проксирования | Р-13 |
| 62 | FT-62 | `/` (docs hub) | GET | — | 200 | Страница документации содержит ссылки на Swagger | — |

---

## 4.3.6 Итоговая статистика

| Категория | Количество |
|---|---|
| Модульных тестов (MT) | 105 описано; 271 запущено (с параметризованными) |
| Функциональных тест-кейсов (FT) | 62 |
| E2E-тест-кейсов | 4 |
| **Итого тестовых сценариев** | **171** |
| Пройдено тестов pytest (автономно) | **267** |
| Пройдено E2E (с Docker) | **4** |
| Провалено E2E (с Docker) | **0** |
| Упало автономных тестов | **0** |

---

## 4.3.7 Анализ неохваченных сценариев

В ходе работы над покрытием был написан дополнительный набор тестов (MT-88–MT-105), закрывший ранее выявленные пробелы: негативные 4xx HTTP-сценарии для сервиса `project`, RBAC-проверки (роли не-директора) и доменные отказы сервиса `user` (пересечения временных окон, заблокированный ресурс, дублирование профиля). E2E-тесты E2E-02 и E2E-03 были исправлены: добавлены шаги приглашения и активации участника проекта через email-ссылку.

Оставшиеся области без тестового покрытия:

### 4.3.7.1 Негативные сценарии (частично закрыты)

| Сценарий | Эндпоинт | Ожидаемый статус | Состояние |
|---|---|---|---|
| Невалидный UUID в параметре пути | `GET /users/{user_id}/description` | 422 | Не покрыт |
| `PATCH /projects/{id}` с `title: "   "` (только пробелы) | PATCH | 400 | Покрыт только в юнит-тесте сервисного слоя |
| Пересечение временных окон у user (HTTP-уровень) | `POST /users/{id}/spare-times` | 409 | Покрыт юнитом MT-88, не покрыт на HTTP-уровне |

### 4.3.7.2 Граничные случаи

| Сценарий | Компонент |
|---|---|
| Бронирование окна ровно на границе свободного интервала (start == free.start) | `ReserveAvailabilityHandler` |
| Загрузка файла, превышающего `IMAGE_MAX_SIZE_BYTES` | `AddImageHandler` |
| Загрузка файла с недопустимым MIME-типом | `AddImageHandler` |
| Генерация отчёта для смены без участников | `GenerateShiftReportHandler` |
| Приглашение пользователя, уже являющегося участником проекта | `InviteProjectMemberHandler` |

### 4.3.7.3 Брокерные сценарии

| Сценарий |
|---|
| Поведение outbox при недоступности брокера RabbitMQ |
| Retry-логика TaskIQ при ошибке отправки email |
