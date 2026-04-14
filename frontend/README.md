# KinoFlow Frontend

Фронтенд на `React + Vite` для работы с пользовательским профилем, личной доступностью, оборудованием и реквизитом.

## Что было и что подключено сейчас

До доработки во фронте были заведены:

- описание пользователя: `POST/GET/PUT /user/users/me/description`
- CRUD только для `microfons`, `cameras`, `camera-tripods`, `lights`

После доработки фронт покрывает весь переданный `User service` из спеки:

- профиль пользователя
- личные `spare-times`
- CRUD для `microfons`, `cameras`, `camera-tripods`, `lights`, `light-tripods`, `sounds`, `requisites`
- добавление `free-times` для всех типов оборудования и реквизита
- `POST /user/users/me/availability/reserve`
- загрузку, список, просмотр и удаление изображений реквизита

## Экраны

### `/profile`

- редактирование описания пользователя
- список личных окон доступности
- создание, редактирование и удаление `spare-times`

### `/projects`

- CRUD по всем сущностям из user-service
- добавление свободного окна для выбранного объекта
- бронирование окна для выбранного объекта
- управление изображениями реквизита

## Карта покрытия API

### Полностью подключено

- `POST /user/users/me/description`
- `GET /user/users/me/description`
- `PUT /user/users/me/description/{description_id}`
- `POST /user/users/me/spare-times`
- `GET /user/users/me/spare-times`
- `GET /user/users/me/spare-times/{spare_time_id}`
- `PUT /user/users/me/spare-times/{spare_time_id}`
- `DELETE /user/users/me/spare-times/{spare_time_id}`
- `POST /user/users/me/microfons`
- `GET /user/users/me/microfons`
- `PUT /user/users/me/microfons/{microfon_id}`
- `DELETE /user/users/me/microfons/{microfon_id}`
- `POST /user/users/me/cameras`
- `GET /user/users/me/cameras`
- `PUT /user/users/me/cameras/{camera_id}`
- `DELETE /user/users/me/cameras/{camera_id}`
- `POST /user/users/me/camera-tripods`
- `GET /user/users/me/camera-tripods`
- `PUT /user/users/me/camera-tripods/{camera_tripod_id}`
- `DELETE /user/users/me/camera-tripods/{camera_tripod_id}`
- `POST /user/users/me/lights`
- `GET /user/users/me/lights`
- `PUT /user/users/me/lights/{light_id}`
- `DELETE /user/users/me/lights/{light_id}`
- `POST /user/users/me/light-tripods`
- `GET /user/users/me/light-tripods`
- `PUT /user/users/me/light-tripods/{light_tripod_id}`
- `DELETE /user/users/me/light-tripods/{light_tripod_id}`
- `POST /user/users/me/sounds`
- `GET /user/users/me/sounds`
- `PUT /user/users/me/sounds/{sound_id}`
- `DELETE /user/users/me/sounds/{sound_id}`
- `POST /user/users/me/requisites`
- `GET /user/users/me/requisites`
- `PUT /user/users/me/requisites/{requisite_id}`
- `DELETE /user/users/me/requisites/{requisite_id}`
- `POST /user/users/me/microfons/{microfon_id}/free-times`
- `POST /user/users/me/cameras/{camera_id}/free-times`
- `POST /user/users/me/camera-tripods/{camera_tripod_id}/free-times`
- `POST /user/users/me/lights/{light_id}/free-times`
- `POST /user/users/me/light-tripods/{light_tripod_id}/free-times`
- `POST /user/users/me/sounds/{sound_id}/free-times`
- `POST /user/users/me/requisites/{requisite_id}/free-times`
- `POST /user/users/me/availability/reserve`
- `POST /user/users/me/requisites/{requisite_id}/images`
- `GET /user/users/me/requisites/{requisite_id}/images`
- `GET /user/users/me/requisites/{requisite_id}/images/{image_id}`
- `DELETE /user/users/me/requisites/{requisite_id}/images/{image_id}`

### Важное ограничение спецификации

Во backend-спеке для `free-times` оборудования и реквизита есть только `POST`. Поэтому во фронте можно:

- добавить новое свободное окно
- отправить бронирование через `/availability/reserve`

Но нельзя честно показать историю этих окон или дать их редактировать, потому что в спеках нет `GET/PUT/DELETE` для этих ресурсов.

## API base URL

Используется переменная:

```env
VITE_API_BASE_URL=/api
```

Если переменная не задана, фронт работает через `/api`.

## Запуск

```bash
npm install
npm run dev
```

## Проверка

```bash
npm run lint
npm run build
```

Обе команды проходят успешно после этой доработки.
