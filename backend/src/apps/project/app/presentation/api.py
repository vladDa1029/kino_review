from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, File, Form, Header, Response, UploadFile, status

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
    DeleteProjectCommand,
    DeleteProjectHandler,
    InviteProjectMemberCommand,
    InviteProjectMemberHandler,
    InviteShiftParticipantCommand,
    InviteShiftParticipantHandler,
    RejectResourceRequestCommand,
    RejectResourceRequestHandler,
    RemoveProjectMemberCommand,
    RemoveProjectMemberHandler,
    UpdateProjectCommand,
    UpdateProjectHandler,
    UploadShiftDocumentCommand,
    UploadShiftDocumentHandler,
)
from app.application.queries import (
    GetDocumentDownloadUrlHandler,
    GetDocumentDownloadUrlQuery,
    GetProjectHandler,
    GetProjectMemberHandler,
    GetProjectMemberQuery,
    GetProjectQuery,
    GetProjectUserResourcesHandler,
    GetProjectUserResourcesQuery,
    HealthHandler,
    HealthQuery,
    ListActorProjectsHandler,
    ListActorProjectsQuery,
    ListProjectMembersHandler,
    ListProjectMembersQuery,
)
from app.presentation.schemas import (
    ChangeProjectMemberRoleRequest,
    CreateResourceRequestBody,
    CreateShiftRequest,
    DocumentDownloadUrlResponse,
    DocumentTypeInput,
    DocumentUploadResponse,
    InviteProjectMemberRequest,
    InviteShiftParticipantRequest,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectMemberShortResponse,
    ProjectResourceResponse,
    ProjectResponse,
    ProjectRoleInput,
    ProjectUpdateRequest,
    ProjectUserResourcesResponse,
    RejectResourceRequestBody,
    ResourceTimeWindowResponse,
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


@router.get("/projects", response_model=ProjectListResponse, summary="List my projects")
async def list_projects(
    handler: FromDishka[ListActorProjectsHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
    include_archived: bool = False,
) -> ProjectListResponse:
    projects = await handler(
        ListActorProjectsQuery(
            actor_user_id=x_user_id,
            include_archived=include_archived,
        )
    )
    return ProjectListResponse(items=[ProjectResponse.from_entity(project) for project in projects])


@router.get("/projects/{project_id}", response_model=ProjectResponse, summary="Get project")
async def get_project(
    project_id: UUID,
    handler: FromDishka[GetProjectHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ProjectResponse:
    project = await handler(
        GetProjectQuery(
            project_id=project_id,
            actor_user_id=x_user_id,
        )
    )
    return ProjectResponse.from_entity(project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse, summary="Update project")
async def update_project(
    project_id: UUID,
    payload: ProjectUpdateRequest,
    handler: FromDishka[UpdateProjectHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ProjectResponse:
    project = await handler(
        UpdateProjectCommand(
            project_id=project_id,
            actor_user_id=x_user_id,
            title=payload.title,
            description=payload.description,
        )
    )
    return ProjectResponse.from_entity(project)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive project",
)
async def delete_project(
    project_id: UUID,
    handler: FromDishka[DeleteProjectHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> Response:
    await handler(
        DeleteProjectCommand(
            project_id=project_id,
            actor_user_id=x_user_id,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.get(
    "/projects/{project_id}/members",
    response_model=ProjectMemberListResponse,
    summary="List project members",
)
async def list_project_members(
    project_id: UUID,
    handler: FromDishka[ListProjectMembersHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
    user_id: UUID | None = None,
    include_inactive: bool = False,
) -> ProjectMemberListResponse:
    members = await handler(
        ListProjectMembersQuery(
            project_id=project_id,
            actor_user_id=x_user_id,
            user_id=user_id,
            include_inactive=include_inactive,
        )
    )
    return ProjectMemberListResponse(
        items=[
            ProjectMemberShortResponse(
                oid=member.oid,
                user_id=member.user_id,
                role=ProjectRoleInput[member.role.name],
                status=member.status,
                invited_by=member.invited_by,
                created_at=member.created_at,
                updated_at=member.updated_at,
            )
            for member in members
        ]
    )


@router.get(
    "/projects/{project_id}/members/{target_user_id}",
    response_model=ProjectMemberResponse,
    summary="Get project member",
)
async def get_project_member(
    project_id: UUID,
    target_user_id: UUID,
    handler: FromDishka[GetProjectMemberHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
    include_inactive: bool = False,
) -> ProjectMemberResponse:
    member = await handler(
        GetProjectMemberQuery(
            project_id=project_id,
            actor_user_id=x_user_id,
            target_user_id=target_user_id,
            include_inactive=include_inactive,
        )
    )
    return ProjectMemberResponse(
        oid=member.oid,
        project_id=project_id,
        user_id=member.user_id,
        role=ProjectRoleInput[member.role.name],
        status=member.status,
        invited_by=member.invited_by,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


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


@router.delete(
    "/projects/{project_id}/members/{target_user_id}",
    response_model=ProjectMemberResponse,
    summary="Remove project member",
)
async def remove_project_member(
    project_id: UUID,
    target_user_id: UUID,
    handler: FromDishka[RemoveProjectMemberHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ProjectMemberResponse:
    member = await handler(
        RemoveProjectMemberCommand(
            project_id=project_id,
            actor_user_id=x_user_id,
            target_user_id=target_user_id,
        )
    )
    return ProjectMemberResponse.from_entity(member)


@router.get(
    "/projects/{project_id}/members/{target_user_id}/resources",
    response_model=ProjectUserResourcesResponse,
    summary="Get project member resources by access role",
)
async def get_project_user_resources(
    project_id: UUID,
    target_user_id: UUID,
    handler: FromDishka[GetProjectUserResourcesHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ProjectUserResourcesResponse:
    result = await handler(
        GetProjectUserResourcesQuery(
            project_id=project_id,
            actor_user_id=x_user_id,
            target_user_id=target_user_id,
        )
    )
    return ProjectUserResourcesResponse(
        user_id=result.user_id,
        role=ProjectRoleInput[result.role.name],
        resources=[
            ProjectResourceResponse(
                resource_kind=item.resource_kind,
                resource_id=item.resource_id,
                title=item.title,
                description=item.description,
                resource_type=item.resource_type,
                size=item.size,
                created_at=item.created_at,
                windows=[
                    ResourceTimeWindowResponse(
                        window_id=window.window_id,
                        start_time=window.start_time,
                        end_time=window.end_time,
                        status=window.status,
                    )
                    for window in item.windows
                ],
            )
            for item in result.resources
        ],
    )


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
