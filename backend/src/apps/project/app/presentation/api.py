from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, File, Form, Header, Response, UploadFile, status

from app.application.commands import (
    ApproveResourceRequestCommand,
    ApproveResourceRequestHandler,
    ApproveShiftCommand,
    ApproveShiftHandler,
    ArchiveShiftReportCommand,
    ArchiveShiftReportHandler,
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
    GenerateShiftReportCommand,
    GenerateShiftReportHandler,
    InviteProjectMemberByEmailCommand,
    InviteProjectMemberByEmailHandler,
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
    GetAdminDocumentDownloadUrlHandler,
    GetAdminDocumentDownloadUrlQuery,
    GetAdminProjectHandler,
    GetAdminProjectMemberHandler,
    GetAdminProjectMemberQuery,
    GetAdminProjectQuery,
    GetAdminReportDownloadUrlHandler,
    GetAdminReportDownloadUrlQuery,
    GetAdminReportHandler,
    GetAdminReportQuery,
    GetDocumentDownloadUrlHandler,
    GetDocumentDownloadUrlQuery,
    GetProjectHandler,
    GetProjectMemberHandler,
    GetProjectMemberQuery,
    GetProjectQuery,
    GetProjectUserResourcesHandler,
    GetProjectUserResourcesQuery,
    GetReportDownloadUrlHandler,
    GetReportDownloadUrlQuery,
    GetReportHandler,
    GetReportQuery,
    HealthHandler,
    HealthQuery,
    ListActorProjectsHandler,
    ListActorProjectsQuery,
    ListAdminProjectMembersHandler,
    ListAdminProjectMembersQuery,
    ListAdminProjectsHandler,
    ListAdminProjectsQuery,
    ListAdminShiftReportsHandler,
    ListAdminShiftReportsQuery,
    ListProjectMembersHandler,
    ListProjectMembersQuery,
    ListShiftReportsHandler,
    ListShiftReportsQuery,
)
from app.domain.errors.business import AccessDeniedError
from app.presentation.schemas import (
    ChangeProjectMemberRoleRequest,
    CreateResourceRequestBody,
    CreateShiftRequest,
    DocumentDownloadUrlResponse,
    DocumentTypeInput,
    DocumentUploadResponse,
    InviteProjectMemberByEmailRequest,
    InviteProjectMemberRequest,
    InviteShiftParticipantRequest,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectMemberShortResponse,
    ProjectResourceResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    ProjectUserResourcesResponse,
    RejectResourceRequestBody,
    ReportListResponse,
    ReportResponse,
    ResourceTimeWindowResponse,
    ShiftParticipantResponse,
    ShiftResourceRequestResponse,
    ShiftResponse,
    to_project_role_input,
)

PROJECT_API_DESCRIPTION = """
Project service owns project planning, membership, shifts, participants, resource requests,
document metadata, reports, and reservation workflow orchestration.

Notes:
- Final availability and reserve facts are owned by `user`.
- Confirmation email delivery is owned by `notificate`.
- Member resource discovery remains the legacy V2 HTTP-backed read path.
- Admin read endpoints are available under `/admin/*` and require `X-User-Is-Superuser: true`.
""".strip()

PROJECT_OPENAPI_TAGS = [
    {"name": "system", "description": "Health and service-level endpoints."},
    {
        "name": "admin",
        "description": "Administrative read-only endpoints guarded by X-User-Is-Superuser.",
    },
    {"name": "projects", "description": "Project aggregate management endpoints."},
    {
        "name": "members",
        "description": "Project membership invitation, listing, role management, and removal endpoints.",
    },
    {
        "name": "member-resources",
        "description": "Authorized member resource reads through the legacy V2 integration path.",
    },
    {"name": "shifts", "description": "Shift planning and approval endpoints."},
    {
        "name": "participants",
        "description": "Participant invitation and confirmation workflow endpoints.",
    },
    {"name": "documents", "description": "Shift document upload and download-url endpoints."},
    {
        "name": "reports",
        "description": "Generated XLSX shift reports with versioning, stale tracking, and download endpoints.",
    },
    {
        "name": "resource-requests",
        "description": "Resource request creation and owner decision endpoints.",
    },
]

router = APIRouter(route_class=DishkaRoute)


def _require_superuser_access(x_user_is_superuser: bool | None) -> None:
    if x_user_is_superuser is not True:
        raise AccessDeniedError("Admin access required.")


def require_superuser_access(
    x_user_is_superuser: Annotated[bool | None, Header(alias="X-User-Is-Superuser")] = None,
) -> None:
    _require_superuser_access(x_user_is_superuser)


admin_router = APIRouter(
    prefix="/admin",
    route_class=DishkaRoute,
    dependencies=[Depends(require_superuser_access)],
)


@router.get(
    "/health",
    tags=["system"],
    summary="Health check",
    description="Returns a lightweight health payload for liveness and readiness probes.",
)
async def healthcheck(handler: FromDishka[HealthHandler]) -> dict:
    return await handler(HealthQuery())


@admin_router.get(
    "/projects",
    response_model=ProjectListResponse,
    tags=["admin"],
    summary="List all projects for admins",
    description="Returns all projects visible to service administrators. Access requires X-User-Is-Superuser=true.",
)
async def admin_list_projects(
    handler: FromDishka[ListAdminProjectsHandler],
    include_archived: bool = False,
) -> ProjectListResponse:
    projects = await handler(ListAdminProjectsQuery(include_archived=include_archived))
    return ProjectListResponse(items=[ProjectResponse.from_entity(project) for project in projects])


@admin_router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    tags=["admin"],
    summary="Get project for admins",
    description="Returns a project by id for service administrators. Access requires X-User-Is-Superuser=true.",
)
async def admin_get_project(
    project_id: UUID,
    handler: FromDishka[GetAdminProjectHandler],
) -> ProjectResponse:
    project = await handler(GetAdminProjectQuery(project_id=project_id))
    return ProjectResponse.from_entity(project)


@admin_router.get(
    "/projects/{project_id}/members",
    response_model=ProjectMemberListResponse,
    tags=["admin"],
    summary="List project members for admins",
    description="Returns project members without project-level RBAC checks. Access requires X-User-Is-Superuser=true.",
)
async def admin_list_project_members(
    project_id: UUID,
    handler: FromDishka[ListAdminProjectMembersHandler],
    user_id: UUID | None = None,
    include_inactive: bool = False,
) -> ProjectMemberListResponse:
    members = await handler(
        ListAdminProjectMembersQuery(
            project_id=project_id,
            user_id=user_id,
            include_inactive=include_inactive,
        )
    )
    return ProjectMemberListResponse(
        items=[
            ProjectMemberShortResponse(
                oid=member.oid,
                user_id=member.user_id,
                role=to_project_role_input(member.role),
                status=member.status,
                invited_by=member.invited_by,
                created_at=member.created_at,
                updated_at=member.updated_at,
            )
            for member in members
        ]
    )


@admin_router.get(
    "/projects/{project_id}/members/{target_user_id}",
    response_model=ProjectMemberResponse,
    tags=["admin"],
    summary="Get project member for admins",
    description="Returns a project member by user id without project-level RBAC checks. Access requires X-User-Is-Superuser=true.",
)
async def admin_get_project_member(
    project_id: UUID,
    target_user_id: UUID,
    handler: FromDishka[GetAdminProjectMemberHandler],
    include_inactive: bool = False,
) -> ProjectMemberResponse:
    member = await handler(
        GetAdminProjectMemberQuery(
            project_id=project_id,
            target_user_id=target_user_id,
            include_inactive=include_inactive,
        )
    )
    return ProjectMemberResponse(
        oid=member.oid,
        project_id=project_id,
        user_id=member.user_id,
        role=to_project_role_input(member.role),
        status=member.status,
        invited_by=member.invited_by,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


@admin_router.get(
    "/shifts/{shift_id}/reports",
    response_model=ReportListResponse,
    tags=["admin"],
    summary="List shift reports for admins",
    description="Returns report versions for a shift without project-level RBAC checks. Access requires X-User-Is-Superuser=true.",
)
async def admin_list_shift_reports(
    shift_id: UUID,
    handler: FromDishka[ListAdminShiftReportsHandler],
) -> ReportListResponse:
    reports = await handler(ListAdminShiftReportsQuery(shift_id=shift_id))
    return ReportListResponse(items=[ReportResponse.from_entity(report) for report in reports])


@admin_router.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    tags=["admin"],
    summary="Get report metadata for admins",
    description="Returns report metadata without project-level RBAC checks. Access requires X-User-Is-Superuser=true.",
)
async def admin_get_report(
    report_id: UUID,
    handler: FromDishka[GetAdminReportHandler],
) -> ReportResponse:
    report = await handler(GetAdminReportQuery(report_id=report_id))
    return ReportResponse.from_entity(report)


@admin_router.get(
    "/reports/{report_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
    tags=["admin"],
    summary="Get report download url for admins",
    description="Returns a temporary download URL for a READY report without project-level RBAC checks. Access requires X-User-Is-Superuser=true.",
)
async def admin_get_report_download_url(
    report_id: UUID,
    handler: FromDishka[GetAdminReportDownloadUrlHandler],
) -> DocumentDownloadUrlResponse:
    url = await handler(GetAdminReportDownloadUrlQuery(report_id=report_id))
    return DocumentDownloadUrlResponse(download_url=url)


@admin_router.get(
    "/documents/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
    tags=["admin"],
    summary="Get document download url for admins",
    description="Returns a temporary download URL for a shift document without project-level RBAC checks. Access requires X-User-Is-Superuser=true.",
)
async def admin_get_document_download_url(
    document_id: UUID,
    handler: FromDishka[GetAdminDocumentDownloadUrlHandler],
) -> DocumentDownloadUrlResponse:
    url = await handler(GetAdminDocumentDownloadUrlQuery(document_id=document_id))
    return DocumentDownloadUrlResponse(download_url=url)


@router.post(
    "/projects",
    response_model=ProjectResponse,
    tags=["projects"],
    summary="Create project",
    description="Creates a new active project and adds the caller as the owning director.",
)
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


@router.get(
    "/projects",
    response_model=ProjectListResponse,
    tags=["projects"],
    summary="List actor projects",
    description="Returns projects visible to the caller. Archived projects are excluded unless explicitly requested.",
)
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


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    tags=["projects"],
    summary="Get project",
    description="Returns a single project visible to the caller.",
)
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


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    tags=["projects"],
    summary="Update project",
    description="Updates editable project fields such as title and description.",
)
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
    tags=["projects"],
    summary="Archive project",
    description="Archives the project instead of removing project-owned data from persistence.",
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
    tags=["members"],
    summary="Invite member to project by user id",
    description="Invites a registered user into the project by user id. The invitee receives an email link and must accept it while authenticated.",
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


@router.post(
    "/projects/{project_id}/members/by-email",
    response_model=ProjectMemberResponse,
    tags=["members"],
    summary="Invite member to project by email",
    description="Invites a registered user into the project by email. The invitee receives an email link and must accept it while authenticated.",
)
async def invite_project_member_by_email(
    project_id: UUID,
    payload: InviteProjectMemberByEmailRequest,
    handler: FromDishka[InviteProjectMemberByEmailHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ProjectMemberResponse:
    member = await handler(
        InviteProjectMemberByEmailCommand(
            project_id=project_id,
            actor_user_id=x_user_id,
            email=payload.email,
            role=payload.role.to_domain(),
        )
    )
    return ProjectMemberResponse.from_entity(member)


@router.get(
    "/projects/{project_id}/members",
    response_model=ProjectMemberListResponse,
    tags=["members"],
    summary="List project members",
    description="Lists project members visible to the caller. Inactive invitations can be included when requested.",
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
                role=to_project_role_input(member.role),
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
    tags=["members"],
    summary="Get project member",
    description="Returns a single project member by target user id.",
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
        role=to_project_role_input(member.role),
        status=member.status,
        invited_by=member.invited_by,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


@router.patch(
    "/projects/{project_id}/members/{target_user_id}/role",
    response_model=ProjectMemberResponse,
    tags=["members"],
    summary="Change project member role",
    description="Changes the role of an existing project member.",
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
    tags=["members"],
    summary="Remove project member",
    description="Removes a member from the project while preserving workflow history.",
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
    tags=["member-resources"],
    summary="Get project member resources by access role",
    description="Returns resources owned by the target user after project-side authorization. This endpoint still uses the legacy V2 HTTP-backed integration path to `user`.",
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
        role=to_project_role_input(result.role),
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
    tags=["shifts"],
    summary="Create shift",
    description="Creates a draft shift inside the specified project.",
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


@router.post(
    "/shifts/{shift_id}/approve",
    response_model=ShiftResponse,
    tags=["shifts"],
    summary="Approve shift",
    description="Approves a draft shift and applies the project workflow rules for approved shifts.",
)
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
    tags=["participants"],
    summary="Invite shift participant",
    description="Invites a participant to the shift for the specified time window.",
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
    tags=["participants"],
    summary="Confirm shift participation",
    description="Confirms participant acceptance and starts asynchronous reservation orchestration.",
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
    tags=["participants"],
    summary="Decline shift participation",
    description="Declines an invited shift participation request.",
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
    tags=["documents"],
    summary="Upload shift document",
    description="Uploads a project document for the shift and stores the binary in object storage.",
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


@router.post(
    "/shifts/{shift_id}/reports/generate",
    response_model=ReportResponse,
    tags=["reports"],
    summary="Generate shift report",
    description="Creates a generated XLSX report in background for an APPROVED shift and returns report metadata immediately.",
)
async def generate_report(
    shift_id: UUID,
    handler: FromDishka[GenerateShiftReportHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ReportResponse:
    report = await handler(
        GenerateShiftReportCommand(
            shift_id=shift_id,
            actor_user_id=x_user_id,
        )
    )
    return ReportResponse.from_entity(report)


@router.get(
    "/shifts/{shift_id}/reports",
    response_model=ReportListResponse,
    tags=["reports"],
    summary="List shift reports",
    description="Lists all report versions attached to the shift.",
)
async def list_shift_reports(
    shift_id: UUID,
    handler: FromDishka[ListShiftReportsHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ReportListResponse:
    reports = await handler(
        ListShiftReportsQuery(
            shift_id=shift_id,
            actor_user_id=x_user_id,
        )
    )
    return ReportListResponse(items=[ReportResponse.from_entity(report) for report in reports])


@router.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    tags=["reports"],
    summary="Get report metadata",
    description="Returns report metadata for a single generated shift report.",
)
async def get_report(
    report_id: UUID,
    handler: FromDishka[GetReportHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ReportResponse:
    report = await handler(
        GetReportQuery(
            report_id=report_id,
            actor_user_id=x_user_id,
        )
    )
    return ReportResponse.from_entity(report)


@router.get(
    "/reports/{report_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
    tags=["reports"],
    summary="Get report download url",
    description="Returns a temporary download URL for a READY generated report.",
)
async def get_report_download_url(
    report_id: UUID,
    handler: FromDishka[GetReportDownloadUrlHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> DocumentDownloadUrlResponse:
    url = await handler(
        GetReportDownloadUrlQuery(
            report_id=report_id,
            actor_user_id=x_user_id,
        )
    )
    return DocumentDownloadUrlResponse(download_url=url)


@router.delete(
    "/reports/{report_id}",
    response_model=ReportResponse,
    tags=["reports"],
    summary="Archive report",
    description="Soft-archives a generated report version. In-progress reports cannot be archived.",
)
async def archive_report(
    report_id: UUID,
    handler: FromDishka[ArchiveShiftReportHandler],
    x_user_id: Annotated[UUID, Header(alias="X-User-Id")],
) -> ReportResponse:
    report = await handler(
        ArchiveShiftReportCommand(
            report_id=report_id,
            actor_user_id=x_user_id,
        )
    )
    return ReportResponse.from_entity(report)


@router.get(
    "/documents/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
    tags=["documents"],
    summary="Get document download url",
    description="Returns a temporary download URL for a previously uploaded shift document.",
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
    tags=["resource-requests"],
    summary="Create shift resource request",
    description="Creates a resource request for a user-owned resource in the specified shift time window.",
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
    tags=["resource-requests"],
    summary="Approve resource request",
    description="Approves a resource request as the resource owner and starts asynchronous reservation orchestration.",
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
    tags=["resource-requests"],
    summary="Reject resource request",
    description="Rejects a resource request as the resource owner and stores the rejection reason.",
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


router.include_router(admin_router)
