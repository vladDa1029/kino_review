from dataclasses import dataclass

from app.application.commands.reserve_availability import (
    ReserveAvailabilityCommand,
    ReserveAvailabilityHandler,
)
from app.application.ports.approvals import (
    ConfirmationTokenPort,
    ParticipantConfirmationTokenData,
    ProjectApprovalStatePort,
    ResourceConfirmationTokenData,
)
from app.application.ports.broker import EventPublisher
from app.domain.entity.base import BaseId
from app.domain.errors.confirmation import (
    ConfirmationTokenExpiredError,
    ConfirmationTokenInvalidError,
)


@dataclass(frozen=True, slots=True)
class ReservationConfirmationResult:
    page: str
    title: str
    message: str


class ConfirmReservationByTokenHandler:
    def __init__(
        self,
        *,
        confirmation_tokens: ConfirmationTokenPort,
        project_approval_states: ProjectApprovalStatePort,
        reserve_availability: ReserveAvailabilityHandler,
        publisher: EventPublisher,
    ) -> None:
        self._confirmation_tokens = confirmation_tokens
        self._project_approval_states = project_approval_states
        self._reserve_availability = reserve_availability
        self._publisher = publisher

    async def __call__(self, token: str) -> ReservationConfirmationResult:
        try:
            payload = self._confirmation_tokens.decode_confirmation_token(token)
        except ConfirmationTokenExpiredError:
            return ReservationConfirmationResult(
                page="expired",
                title="Link expired",
                message="This confirmation link has expired.",
            )
        except ConfirmationTokenInvalidError:
            return ReservationConfirmationResult(
                page="invalid",
                title="Invalid link",
                message="This confirmation link is invalid.",
            )

        if isinstance(payload, ParticipantConfirmationTokenData):
            return await self._confirm_participant(payload)
        if isinstance(payload, ResourceConfirmationTokenData):
            return await self._confirm_resource(payload)
        return ReservationConfirmationResult(
            page="invalid",
            title="Invalid link",
            message="This confirmation link is invalid.",
        )

    async def _confirm_participant(
        self,
        payload: ParticipantConfirmationTokenData,
    ) -> ReservationConfirmationResult:
        try:
            state = await self._project_approval_states.get_participant_approval_state(
                participant_id=payload.participant_id,
            )
        except Exception:
            return ReservationConfirmationResult(
                page="error",
                title="Confirmation error",
                message="Could not verify reservation state right now.",
            )

        if not _matches_participant_state(payload, state):
            return ReservationConfirmationResult(
                page="invalid",
                title="Invalid link",
                message="This confirmation link does not match the current reservation state.",
            )
        if state.status_name != "RESERVING":
            return _already_processed_result(state.status_name)

        try:
            reservation_id = await self._reserve_availability(
                ReserveAvailabilityCommand(
                    request_id=BaseId(payload.request_id),
                    user_id=BaseId(payload.user_id),
                    owner_id=BaseId(payload.user_id),
                    obj_id=BaseId(payload.user_id),
                    start_time=payload.time_from,
                    end_time=payload.time_to,
                )
            )
        except Exception as exc:
            await self._publisher.publish(
                "shift.participant_reserve_failed",
                {
                    "request_id": str(payload.request_id),
                    "project_id": str(payload.project_id),
                    "shift_id": str(payload.shift_id),
                    "participant_id": str(payload.participant_id),
                    "user_id": str(payload.user_id),
                    "reason": str(exc),
                },
            )
            return ReservationConfirmationResult(
                page="error",
                title="Reservation failed",
                message="The reservation could not be confirmed.",
            )

        await self._publisher.publish(
            "shift.participant_reserved.user",
            {
                "request_id": str(payload.request_id),
                "project_id": str(payload.project_id),
                "shift_id": str(payload.shift_id),
                "participant_id": str(payload.participant_id),
                "user_id": str(payload.user_id),
                "reservation_id": str(reservation_id),
            },
        )
        return ReservationConfirmationResult(
            page="success",
            title="Reservation confirmed",
            message="The reservation was confirmed successfully.",
        )

    async def _confirm_resource(
        self,
        payload: ResourceConfirmationTokenData,
    ) -> ReservationConfirmationResult:
        try:
            state = await self._project_approval_states.get_resource_approval_state(
                resource_request_id=payload.resource_request_id,
            )
        except Exception:
            return ReservationConfirmationResult(
                page="error",
                title="Confirmation error",
                message="Could not verify reservation state right now.",
            )

        if not _matches_resource_state(payload, state):
            return ReservationConfirmationResult(
                page="invalid",
                title="Invalid link",
                message="This confirmation link does not match the current reservation state.",
            )
        if state.status_name != "RESERVING":
            return _already_processed_result(state.status_name)

        try:
            reservation_id = await self._reserve_availability(
                ReserveAvailabilityCommand(
                    request_id=BaseId(payload.request_id),
                    user_id=BaseId(payload.owner_user_id),
                    owner_id=BaseId(payload.owner_user_id),
                    obj_id=BaseId(payload.resource_id),
                    start_time=payload.time_from,
                    end_time=payload.time_to,
                )
            )
        except Exception as exc:
            await self._publisher.publish(
                "shift.resource_request_reserve_failed",
                {
                    "request_id": str(payload.request_id),
                    "project_id": str(payload.project_id),
                    "shift_id": str(payload.shift_id),
                    "resource_request_id": str(payload.resource_request_id),
                    "owner_user_id": str(payload.owner_user_id),
                    "resource_id": str(payload.resource_id),
                    "reason": str(exc),
                },
            )
            return ReservationConfirmationResult(
                page="error",
                title="Reservation failed",
                message="The reservation could not be confirmed.",
            )

        await self._publisher.publish(
            "shift.resource_request_reserved.user",
            {
                "request_id": str(payload.request_id),
                "project_id": str(payload.project_id),
                "shift_id": str(payload.shift_id),
                "resource_request_id": str(payload.resource_request_id),
                "owner_user_id": str(payload.owner_user_id),
                "resource_id": str(payload.resource_id),
                "reservation_id": str(reservation_id),
            },
        )
        return ReservationConfirmationResult(
            page="success",
            title="Reservation confirmed",
            message="The reservation was confirmed successfully.",
        )


def _matches_participant_state(
    payload: ParticipantConfirmationTokenData,
    state,
) -> bool:
    return (
        state.request_id == payload.request_id
        and state.project_id == payload.project_id
        and state.shift_id == payload.shift_id
        and state.participant_id == payload.participant_id
        and state.user_id == payload.user_id
        and state.time_from == payload.time_from
        and state.time_to == payload.time_to
    )


def _matches_resource_state(
    payload: ResourceConfirmationTokenData,
    state,
) -> bool:
    return (
        state.request_id == payload.request_id
        and state.project_id == payload.project_id
        and state.shift_id == payload.shift_id
        and state.resource_request_id == payload.resource_request_id
        and state.owner_user_id == payload.owner_user_id
        and state.resource_id == payload.resource_id
        and state.time_from == payload.time_from
        and state.time_to == payload.time_to
    )


def _already_processed_result(status_name: str) -> ReservationConfirmationResult:
    return ReservationConfirmationResult(
        page="already-processed",
        title="Already processed",
        message=f"Reservation is already in state {status_name}.",
    )
