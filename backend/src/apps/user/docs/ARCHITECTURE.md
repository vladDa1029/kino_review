# User Service Architecture

## Purpose

`user` owns user-facing operational data: local user projection, profile description, availability windows, user-owned resources, resource images, final reservation facts, and broker-delivered enrichment data used by generated shift reports.

`user` does not own project workflow state. It must not decide whether a participant or resource request is already approved inside `project`. It only validates availability, issues confirmation links, performs the final reserve, and emits the resulting facts.

## Runtime Model

The service runs as a single FastAPI process created in [main.py](../main.py).

At startup it:

- loads settings from [app/config.py](../app/config.py);
- verifies storage connectivity and ensures the configured bucket or local directory exists;
- creates a RabbitMQ broker and declares inbound exchanges and queues;
- builds the Dishka container through [app/ioc.py](../app/ioc.py);
- starts ORM mappings from [app/infrastructure/adapters/orm.py](../app/infrastructure/adapters/orm.py);
- mounts HTTP routes from [app/presentation/api.py](../app/presentation/api.py);
- mounts broker subscribers from [app/presentation/broker.py](../app/presentation/broker.py).

Runtime dependencies:

- PostgreSQL for user-owned state;
- RabbitMQ for inbound and outbound events;
- file storage backend for requisite images;
- broker request/reply to `project` for approval-state recheck during email confirmation.

## Composition Root

Primary entrypoints:

- [main.py](../main.py)
- [app/config.py](../app/config.py)
- [app/ioc.py](../app/ioc.py)
- [app/presentation/api.py](../app/presentation/api.py)
- [app/presentation/broker.py](../app/presentation/broker.py)

Key adapters:

- [app/infrastructure/adapters/repository.py](../app/infrastructure/adapters/repository.py)
- [app/infrastructure/adapters/broker.py](../app/infrastructure/adapters/broker.py)
- [app/infrastructure/adapters/storage.py](../app/infrastructure/adapters/storage.py)
- [app/infrastructure/security/confirmation_token.py](../app/infrastructure/security/confirmation_token.py)
- [app/presentation/http/project_service.py](../app/presentation/http/project_service.py)

## Owned Data

| Area | Source of truth | Notes |
| --- | --- | --- |
| User projection | `users` table | Created from `auth` event `user.registered` |
| User description | `descriptions` table | One description per user |
| User availability | `free_users_timing` table | Free and reserved user windows |
| Owned equipment | equipment tables | Microfons, cameras, tripods, lights, sounds, requisites |
| Resource availability | `*_free_times` tables | Free and reserved resource windows |
| Requisite images | `images` table plus storage backend | DB stores metadata, storage keeps bytes |
| Reservation facts | availability tables after reserve | Final source of truth for reserved time in `user` |
| Confirmation links | no dedicated table | Stateless JWT token plus sync recheck in `project` |

## Inbound Interfaces

### HTTP Surface

| Interface group | Paths | Authentication | Purpose |
| --- | --- | --- | --- |
| Health | `/health` | public | Process health check for Docker readiness |
| User existence | `/users/{user_id}` | `X-User-Id` must match path | Legacy public read-side existence endpoint; V1 interservice validation now uses AMQP |
| Profile | `/users/{user_id}/description` | `X-User-Id` | Create, update, and read description |
| User availability | `/users/{user_id}/spare-times` | `X-User-Id` | Manage user free windows |
| Equipment CRUD | `/users/{user_id}/{resource-kind}` | `X-User-Id` | Manage owned resources |
| Equipment availability | `/users/{user_id}/{resource-kind}/{resource_id}/free-times` | `X-User-Id` | Manage or list resource windows |
| Requisite images | `/users/{user_id}/requisites/{requisite_id}/images` | `X-User-Id` | Upload, list, read, and delete image metadata |
| Legacy direct reserve | `/users/{user_id}/availability/reserve` | `X-User-Id` | Compatibility endpoint for direct reserve contract |
| Public confirmation | `/confirmations/{token}` | public | One-click reservation approval flow from email |
| Project invitation confirmation | `/project-invitations/{token}` | `X-User-Id` | Accept project invitation links; caller must match the invited user |

### Inbound Events

| Routing key | Exchange | Queue | Producer | Purpose |
| --- | --- | --- | --- | --- |
| `user.registered` | `user.registered` | `user.registered.user` | `auth` | Build or refresh local user projection |
| `user.existence_requested` | `project.events` | `user.existence_requested.user` | `project` | V1 broker request/reply for invited user existence validation |
| `user.email_lookup_requested` | `project.events` | `user.email_lookup_requested.user` | `project` | Resolve registered user id from invite email |
| `project.member_invitation_requested` | `project.events` | `project.member_invitation_requested.user` | `project` | Build project invitation email request |
| `shift.participant_reservation_check_requested` | `project.events` | `shift.participant_reservation_check_requested.user` | `project` | Check participant availability without final reserve |
| `shift.resource_request_reservation_check_requested` | `project.events` | `shift.resource_request_reservation_check_requested.user` | `project` | Check resource availability without final reserve |
| `shift.report_snapshot_requested` | `project.events` | `shift.report_snapshot_requested.user` | `project` | Provide user-owned enrichment for generated shift reports |
| `shift.participant_approval_requested` | `project.events` | `shift.participant_approval_requested.user` | `project` | Build participant confirmation email request |
| `shift.resource_request_approval_requested` | `project.events` | `shift.resource_request_approval_requested.user` | `project` | Build resource-owner confirmation email request |
| `shift.participant_reservation_requested` | `project.events` | `shift.participant_reservation_requested.user` | compatibility path | Perform direct participant reserve |
| `shift.resource_request_reservation_requested` | `project.events` | `shift.resource_request_reservation_requested.user` | compatibility path | Perform direct resource reserve |

## Outbound Interfaces

### Outbound Events

| Routing key | Exchange | Consumer | Trigger |
| --- | --- | --- | --- |
| `user.existence_provided` / `user.existence_failed` | `user.events` via `project.reply.<instance_id>` | `project` | V1 reply to invited-user existence lookup |
| `user.email_lookup_provided` / `user.email_lookup_failed` | `user.events` via `project.reply.<instance_id>` | `project` | Reply to project email-invite lookup |
| `shift.report_snapshot_provided` / `shift.report_snapshot_failed` | `user.events` via `project.reply.<instance_id>` | `project` | Reply with report enrichment snapshot |
| `shift.participant_reservation_check_succeeded` | `user.events` | `project` | Participant interval is currently reservable |
| `shift.participant_reservation_check_failed` | `user.events` | `project` | Participant interval cannot be reserved |
| `shift.resource_request_reservation_check_succeeded` | `user.events` | `project` | Resource interval is currently reservable |
| `shift.resource_request_reservation_check_failed` | `user.events` | `project` | Resource interval cannot be reserved |
| `notification.email_requested` | `user.events` | `notificate` | Confirmation email must be delivered |
| `project.member.approved` | `user.events` | `project` | Authenticated invitee accepted project invitation link |
| `shift.participant_approval_state_requested` | `user.events` | `project` | V3 approval-state request before final participant reserve |
| `shift.resource_request_approval_state_requested` | `user.events` | `project` | V3 approval-state request before final resource reserve |
| `shift.participant_reserved.user` | `user.events` | `project` | Final participant reserve succeeded |
| `shift.participant_reserve_failed` | `user.events` | `project` | Final participant reserve failed |
| `shift.resource_request_reserved.user` | `user.events` | `project` | Final resource reserve succeeded |
| `shift.resource_request_reserve_failed` | `user.events` | `project` | Final resource reserve failed |

### Broker Request/Reply Dependencies

| Target service | Client | Purpose | Mechanism |
| --- | --- | --- | --- |
| `project` | [app/presentation/http/project_service.py](../app/presentation/http/project_service.py) | Recheck approval-state before final reserve | Correlated AMQP request/reply over per-instance reply topic |

### Confirmation Token Claims

| Claim | Participant approval | Resource approval | Project invitation | Notes |
| --- | --- | --- | --- | --- |
| `type` | `participant_approval` | `resource_request_approval` | `project_member_invitation` | Distinguishes token payload shape |
| `request_id` | required | required | required | Correlates token to project-side request |
| `project_id` | required | required | required | Project ownership check |
| `shift_id` | required | required | - | Shift ownership check |
| `participant_id` | required | - | - | Present only for participant approval |
| `user_id` | required | - | required | Participant or invited user id |
| `member_id` | - | - | required | Project membership row id |
| `role` | - | - | required | Invited project role |
| `resource_request_id` | - | required | - | Present only for resource approval |
| `owner_user_id` | - | required | - | Resource owner user id |
| `resource_id` | - | required | - | Reserved resource id |
| `time_from` | required | required | - | Expected start time |
| `time_to` | required | required | - | Expected end time |
| `iat` | required | required | required | Issued-at timestamp |
| `exp` | required | required | required | Expiration timestamp |

## Key Flows

### User projection from `auth`

1. `auth` emits `user.registered`.
2. `user` consumes the event and upserts the local user projection.
3. All later profile, resource, and availability commands work against that local projection.

### Reservation check from `project`

1. `project` emits a reservation-check event.
2. `user` validates the interval against current free windows.
3. For resource reservations, `user` first verifies that the requested resource exists and belongs to the supplied owner user id.
4. `user` emits either `*_reservation_check_succeeded` or `*_reservation_check_failed`.
5. No final reserve is written in this stage.

### Approval email flow

1. `project` emits `shift.participant_approval_requested` or `shift.resource_request_approval_requested`.
2. `user` loads the recipient, issues a signed confirmation token, and builds the frontend link `${FRONTEND_BASE_URL}/confirm/{token}`.
3. `user` emits `notification.email_requested`.
4. `notificate` sends the email.
5. The user opens the frontend `/confirm/{token}` page, which `POST`s `/user/confirmations/{token}` (public path) through the gateway.

### Project invitation email flow

1. `project` resolves the invite email through `user.email_lookup_requested`; only registered users can be invited by email.
2. `project` writes the project member as `INVITED` and emits `project.member_invitation_requested`.
3. `user` loads the invitee, issues a signed `project_member_invitation` token, builds the frontend link `${FRONTEND_BASE_URL}/invitations/{token}`, and emits `notification.email_requested`.
4. `notificate` sends the email.
5. The invitee opens the frontend `/invitations/{token}` page (signing in if needed), which `POST`s `/user/project-invitations/{token}` through the gateway while authenticated.
6. `user` verifies the token user id matches `X-User-Id` and emits `project.member.approved`.
7. `project` activates the invited member if the invitation is still in `INVITED`.

### Report enrichment for generated shift reports

1. `project` emits `shift.report_snapshot_requested` with project-owned participant and resource context.
2. `user` enriches that context with user-owned fields:
   - `username`, `phone`, `email`
   - resource `title`, `type`, `description`, `size`
3. `user` replies on the caller-specific `project.reply.<instance_id>` topic.
4. `project` remains the report owner and performs rendering, storage, and metadata persistence itself.

### Final reserve after click

1. `user` decodes the token and validates signature and TTL.
2. `user` publishes an approval-state request with a transport `correlation_id` and waits on its process-local reply queue.
3. If the project-side context still matches and remains `RESERVING`, `user` performs the final reserve.
4. For resource reservations, the final reserve rechecks that `resource_id` still belongs to `owner_user_id` before slicing availability windows.
5. `user` emits the final success or failure event back to `project`.

## Change Playbooks

- If you change confirmation-token claims, update [app/infrastructure/security/confirmation_token.py](../app/infrastructure/security/confirmation_token.py), the confirmation endpoint, tests, and the architecture table above in one change.
- If you change any reservation event payload, update producer, consumer, Pydantic schema, and interservice tests together. Do not treat broker payloads as informal.
- If you change the approval email flow, keep the broker-based recheck in `project`. Do not replace it with local assumptions inside `user`.
- If you change the project invitation email flow, update `project` invite producer, `user` token/link handling, `notificate` template schema, gateway public/protected assumptions, docs, and tests together.
- If you change report snapshot enrichment, update the broker consumer, payload schemas, project-side reply handling, docs, and tests together.
- If you change image storage behavior, update storage adapter, config docs, and tests for both metadata and binary backend behavior.
- If you add a new public route, verify whether it must stay public through the gateway or still require `X-User-Id`.

## Known Traps

- Do not move project workflow state into `user`. `user` owns reservation facts, not project orchestration statuses.
- Do not skip the broker-based project recheck before final reserve. A valid token is not enough by itself.
- Do not treat `notification.email_requested` as a domain decision. It is a delivery request only.
- Do not render or store generated shift reports in `user`. `user` only enriches report data.
- Do not introduce a new pending-confirmation table casually. The current design is intentionally stateless for approval links.
- Do not trust arbitrary `X-User-Id` values outside the gateway path contract.

## Validation / Testing Focus

- Run service tests covering confirmation token handling, reserve flow, and broker handlers in [test](../test).
- Recheck contract tests when event payloads or routing keys change.
- Recheck confirmation endpoint behavior for valid, expired, tampered, and repeated-link scenarios.
- Recheck storage-backed image behavior when storage configuration or image schema changes.

## Current Limitations

- No dedicated audit trail for link clicks or resend management.
- No explicit revoke flow for issued confirmation links.
- Notification delivery guarantees stop at event emission; SMTP delivery state is owned elsewhere.
- Some compatibility reserve events still exist and should be treated as legacy paths, not the preferred approval flow.
