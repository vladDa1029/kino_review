from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, File, Form, Header, UploadFile

from app.application.commands import (
    ApproveResourceRequestCommand,
    ApproveResourceRequestHandler,
    ApproveShiftCommand,
    ApproveShiftHandler,
    ChangeProjectMemberRoleCommand,
    ChangeProjectMemberRoleHandler,
    ConfirmShiftParticipantCommand,
    ConfirmShiftParticipantHandler,
    CreateProjectCommand,
    CreateProjectHandler,
    CreateResourceRequestCommand,
    CreateResourceRequestHandler,
    CreateShiftCommand,
    CreateShiftHandler,
    DeclineShiftParticipantCommand,
    DeclineShiftParticipantHandler,
    InviteProjectMemberCommand,
    InviteProjectMemberHandler,
    InviteShiftParticipantCommand,
    InviteShiftParticipantHandler,
    RejectResourceRequestCommand,
    RejectResourceRequestHandler,
    UploadShiftDocumentCommand,
    UploadShiftDocumentHandler,
)
from app.application.queries import (
    GetDocumentDownloadUrlHandler,
    GetDocumentDownloadUrlQuery,
    HealthHandler,
    HealthQuery,
)
from app.presentation.schemas import (
    ChangeProjectMemberRoleRequest,
    CreateResourceRequestBody,
    CreateShiftRequest,
    DocumentTypeInput,
    DocumentDownloadUrlResponse,
    DocumentUploadResponse,
    InviteProjectMemberRequest,
    InviteShiftParticipantRequest,
    ProjectCreateRequest,
    ProjectMemberResponse,
    ProjectResponse,
    RejectResourceRequestBody,
    ShiftParticipantResponse,
    ShiftResourceRequestResponse,
    ShiftResponse,
)

router = APIRouter(tags=["project"], route_class=DishkaRoute)


@router.get("/health", summary="Health check")
async def healthcheck(handler: FromDishka[HealthHandler]) -> dict:
    return await handler(HealthQuery())


@router.post("/projects", response_model=ProjectResponse, summary="Create project")
async def create_project(
    payload: ProjectCreateRequest,
    handler: FromDishka[CreateProjectHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ProjectResponse:
    project = await handler(
        CreateProjectCommand(
            owner_id=x_user_id,
            title=payload.title,
            description=payload.description,
        )
    )
    return ProjectResponse.from_entity(project)


@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    summary="Invite member to project",
)
async def invite_project_member(
    project_id: UUID,
    payload: InviteProjectMemberRequest,
    handler: FromDishka[InviteProjectMemberHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ProjectMemberResponse:
    member = await handler(
        InviteProjectMemberCommand(
            project_id=project_id,
            actor_user_id=x_user_id,
            invited_user_id=payload.user_id,
            role=payload.role.to_domain(),
        )
    )
    return ProjectMemberResponse.from_entity(member)


@router.patch(
    "/projects/{project_id}/members/{target_user_id}/role",
    response_model=ProjectMemberResponse,
    summary="Change project member role",
)
async def change_project_member_role(
    project_id: UUID,
    target_user_id: UUID,
    payload: ChangeProjectMemberRoleRequest,
    handler: FromDishka[ChangeProjectMemberRoleHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ProjectMemberResponse:
    member = await handler(
        ChangeProjectMemberRoleCommand(
            project_id=project_id,
            actor_user_id=x_user_id,
            target_user_id=target_user_id,
            role=payload.role.to_domain(),
        )
    )
    return ProjectMemberResponse.from_entity(member)


@router.post(
    "/projects/{project_id}/shifts",
    response_model=ShiftResponse,
    summary="Create shift",
)
async def create_shift(
    project_id: UUID,
    payload: CreateShiftRequest,
    handler: FromDishka[CreateShiftHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ShiftResponse:
    shift = await handler(
        CreateShiftCommand(
            project_id=project_id,
            actor_user_id=x_user_id,
            title=payload.title,
            description=payload.description,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
    )
    return ShiftResponse.from_entity(shift)


@router.post("/shifts/{shift_id}/approve", response_model=ShiftResponse, summary="Approve shift")
async def approve_shift(
    shift_id: UUID,
    handler: FromDishka[ApproveShiftHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ShiftResponse:
    shift = await handler(
        ApproveShiftCommand(
            shift_id=shift_id,
            actor_user_id=x_user_id,
        )
    )
    return ShiftResponse.from_entity(shift)


@router.post(
    "/shifts/{shift_id}/participants",
    response_model=ShiftParticipantResponse,
    summary="Invite shift participant",
)
async def invite_shift_participant(
    shift_id: UUID,
    payload: InviteShiftParticipantRequest,
    handler: FromDishka[InviteShiftParticipantHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ShiftParticipantResponse:
    participant = await handler(
        InviteShiftParticipantCommand(
            shift_id=shift_id,
            actor_user_id=x_user_id,
            participant_user_id=payload.user_id,
            role=payload.role.to_domain(),
            time_from=payload.time_from,
            time_to=payload.time_to,
        )
    )
    return ShiftParticipantResponse.from_entity(participant)


@router.post(
    "/participants/{participant_id}/confirm",
    response_model=ShiftParticipantResponse,
    summary="Confirm shift participation",
)
async def confirm_shift_participant(
    participant_id: UUID,
    handler: FromDishka[ConfirmShiftParticipantHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ShiftParticipantResponse:
    participant = await handler(
        ConfirmShiftParticipantCommand(
            participant_id=participant_id,
            actor_user_id=x_user_id,
        )
    )
    return ShiftParticipantResponse.from_entity(participant)


@router.post(
    "/participants/{participant_id}/decline",
    response_model=ShiftParticipantResponse,
    summary="Decline shift participation",
)
async def decline_shift_participant(
    participant_id: UUID,
    handler: FromDishka[DeclineShiftParticipantHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ShiftParticipantResponse:
    participant = await handler(
        DeclineShiftParticipantCommand(
            participant_id=participant_id,
            actor_user_id=x_user_id,
        )
    )
    return ShiftParticipantResponse.from_entity(participant)


@router.post(
    "/shifts/{shift_id}/documents",
    response_model=DocumentUploadResponse,
    summary="Upload shift document",
)
async def upload_document(
    shift_id: UUID,
    handler: FromDishka[UploadShiftDocumentHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
    file: UploadFile = File(...),
    doc_type: DocumentTypeInput = Form(
        ...,
        description="Document type. Allowed values: PLAN, SCENARIO.",
    ),
    title: str = Form(...),
    description: str | None = Form(default=None),
) -> DocumentUploadResponse:
    content = await file.read()
    document = await handler(
        UploadShiftDocumentCommand(
            shift_id=shift_id,
            actor_user_id=x_user_id,
            doc_type=doc_type.to_domain(),
            title=title,
            filename=file.filename or "document.bin",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            description=description,
        )
    )
    return DocumentUploadResponse.from_entity(document)


@router.get(
    "/documents/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
    summary="Get document download url",
)
async def get_document_download_url(
    document_id: UUID,
    handler: FromDishka[GetDocumentDownloadUrlHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> DocumentDownloadUrlResponse:
    url = await handler(
        GetDocumentDownloadUrlQuery(
            document_id=document_id,
            actor_user_id=x_user_id,
        )
    )
    return DocumentDownloadUrlResponse(download_url=url)


@router.post(
    "/shifts/{shift_id}/resource-requests",
    response_model=ShiftResourceRequestResponse,
    summary="Create shift resource request",
)
async def create_resource_request(
    shift_id: UUID,
    payload: CreateResourceRequestBody,
    handler: FromDishka[CreateResourceRequestHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ShiftResourceRequestResponse:
    request = await handler(
        CreateResourceRequestCommand(
            shift_id=shift_id,
            actor_user_id=x_user_id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            resource_owner_user_id=payload.resource_owner_user_id,
            time_from=payload.time_from,
            time_to=payload.time_to,
        )
    )
    return ShiftResourceRequestResponse.from_entity(request)


@router.post(
    "/resource-requests/{request_id}/approve",
    response_model=ShiftResourceRequestResponse,
    summary="Approve resource request",
)
async def approve_resource_request(
    request_id: UUID,
    handler: FromDishka[ApproveResourceRequestHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ShiftResourceRequestResponse:
    request = await handler(
        ApproveResourceRequestCommand(
            request_id=request_id,
            actor_user_id=x_user_id,
        )
    )
    return ShiftResourceRequestResponse.from_entity(request)


@router.post(
    "/resource-requests/{request_id}/reject",
    response_model=ShiftResourceRequestResponse,
    summary="Reject resource request",
)
async def reject_resource_request(
    request_id: UUID,
    payload: RejectResourceRequestBody,
    handler: FromDishka[RejectResourceRequestHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ShiftResourceRequestResponse:
    request = await handler(
        RejectResourceRequestCommand(
            request_id=request_id,
            actor_user_id=x_user_id,
            reason=payload.reason,
        )
    )
    return ShiftResourceRequestResponse.from_entity(request)
