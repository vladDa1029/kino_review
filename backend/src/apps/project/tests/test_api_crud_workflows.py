import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from dishka import AsyncContainer, Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.commands.participants import (
    ConfirmShiftParticipantHandler,
    DeclineShiftParticipantHandler,
    InviteShiftParticipantHandler,
)
from app.application.commands.reports import (
    ArchiveShiftReportHandler,
    GenerateShiftReportHandler,
)
from app.application.commands.documents import UploadShiftDocumentHandler
from app.application.commands.projects import (
    ChangeProjectMemberRoleHandler,
    CreateProjectHandler,
    DeleteProjectHandler,
    InviteProjectMemberHandler,
    RemoveProjectMemberHandler,
    UpdateProjectHandler,
)
from app.application.commands.resources import (
    ApproveResourceRequestHandler,
    CreateResourceRequestHandler,
    RejectResourceRequestHandler,
)
from app.application.commands.shifts import ApproveShiftHandler, CreateShiftHandler
from app.application.ports.domain import (
    ProjectMemberRepository,
    ProjectRepository,
    ReservationOutboxRepository,
    ResourceRequestRepository,
    ShiftParticipantRepository,
    ShiftReportRepository,
    ShiftRepository,
    UserResourceItem,
)
from app.application.ports.transaction import TransactionManager
from app.application.queries.projects import (
    GetProjectHandler,
    ListActorProjectsHandler,
)
from app.application.queries.reports import GetReportDownloadUrlHandler, GetReportHandler, ListShiftReportsHandler
from app.application.queries.resources import (
    GetProjectMemberHandler,
    ListProjectMembersHandler,
)
from app.application.support import SystemClock
from app.domain.enums import (
    ProjectMemberStatus,
    ProjectRole,
    ResourceRequestStatus,
    ShiftParticipantStatus,
    ShiftStatus,
)
from app.domain.entities import ProjectMember
from app.domain.errors.base import ApplicationError
from app.domain.policy import ActiveMemberPolicy, DirectorMemberPolicy
from app.domain.services import (
    DocumentService,
    ProjectMembershipService,
    ResourceRequestService,
    ShiftParticipantService,
    ShiftService,
)
from app.presentation import handlers
from app.presentation.api import (
    PROJECT_API_DESCRIPTION,
    PROJECT_OPENAPI_TAGS,
    router as project_router,
)
from tests.test_project_management_service import (
    FakeIdGenerator,
    FakePublisher,
    FakeShiftReportTaskDispatcher,
    FakeStorage,
    FakeTx,
    InMemoryDocumentRepo,
    FakeUserService,
    InMemoryProjectMemberRepo,
    InMemoryProjectRepo,
    InMemoryReservationOutboxRepo,
    InMemoryResourceRequestRepo,
    InMemoryShiftRepo,
    InMemoryShiftReportRepo,
    InMemoryParticipantRepo,
)


def now_utc() -> datetime:
    return datetime.now(tz=UTC).replace(microsecond=0)


@dataclass(slots=True)
class ProjectApiCrudContext:
    app: FastAPI
    container: AsyncContainer
    tx: FakeTx
    publisher: FakePublisher
    user_service: FakeUserService
    projects: InMemoryProjectRepo
    members: InMemoryProjectMemberRepo
    shifts: InMemoryShiftRepo
    participants: InMemoryParticipantRepo
    documents: InMemoryDocumentRepo
    reports: InMemoryShiftReportRepo
    requests: InMemoryResourceRequestRepo
    reservation_outbox: InMemoryReservationOutboxRepo
    report_tasks: FakeShiftReportTaskDispatcher


def _provide_instance(provider: Provider, instance, provides) -> None:
    def _source():
        return instance

    provider.provide(
        source=_source,
        provides=provides,
        scope=Scope.REQUEST,
    )


def build_project_api_crud_context() -> ProjectApiCrudContext:
    tx = FakeTx()
    publisher = FakePublisher()
    user_service = FakeUserService()
    projects = InMemoryProjectRepo()
    members = InMemoryProjectMemberRepo()
    shifts = InMemoryShiftRepo()
    participants = InMemoryParticipantRepo()
    documents = InMemoryDocumentRepo()
    reports = InMemoryShiftReportRepo()
    requests = InMemoryResourceRequestRepo()
    reservation_outbox = InMemoryReservationOutboxRepo()
    storage = FakeStorage()
    clock = SystemClock()
    id_generator = FakeIdGenerator()
    report_tasks = FakeShiftReportTaskDispatcher()

    create_project_handler = CreateProjectHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator,
        publisher=publisher,
        projects=projects,
        project_members=members,
        membership_service=ProjectMembershipService(),
    )
    list_projects_handler = ListActorProjectsHandler(projects=projects)
    get_project_handler = GetProjectHandler(
        projects=projects,
        project_members=members,
        active_member_policy=ActiveMemberPolicy(),
    )
    update_project_handler = UpdateProjectHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        projects=projects,
        project_members=members,
        director_member_policy=DirectorMemberPolicy(),
    )
    delete_project_handler = DeleteProjectHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        projects=projects,
        project_members=members,
        director_member_policy=DirectorMemberPolicy(),
    )
    invite_project_member_handler = InviteProjectMemberHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator,
        publisher=publisher,
        user_service=user_service,
        project_members=members,
        projects=projects,
        membership_service=ProjectMembershipService(),
    )
    list_members_handler = ListProjectMembersHandler(
        project_members=members,
        active_member_policy=ActiveMemberPolicy(),
    )
    get_member_handler = GetProjectMemberHandler(
        project_members=members,
        active_member_policy=ActiveMemberPolicy(),
    )
    change_role_handler = ChangeProjectMemberRoleHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        project_members=members,
        membership_service=ProjectMembershipService(),
    )
    remove_member_handler = RemoveProjectMemberHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        projects=projects,
        project_members=members,
        membership_service=ProjectMembershipService(),
    )
    create_shift_handler = CreateShiftHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator,
        publisher=publisher,
        project_members=members,
        shifts=shifts,
        shift_service=ShiftService(),
    )
    approve_shift_handler = ApproveShiftHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        project_members=members,
        shifts=shifts,
        shift_service=ShiftService(),
    )
    invite_participant_handler = InviteShiftParticipantHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator,
        publisher=publisher,
        user_service=user_service,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        shift_reports=reports,
        shift_participant_service=ShiftParticipantService(),
    )
    confirm_participant_handler = ConfirmShiftParticipantHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        reservation_outbox=reservation_outbox,
        project_members=members,
        shifts=shifts,
        shift_participants=participants,
        shift_reports=reports,
        shift_participant_service=ShiftParticipantService(),
    )
    decline_participant_handler = DeclineShiftParticipantHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        shift_participants=participants,
        shift_reports=reports,
        shifts=shifts,
        shift_participant_service=ShiftParticipantService(),
    )
    upload_document_handler = UploadShiftDocumentHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator,
        publisher=publisher,
        document_storage=storage,
        project_members=members,
        shifts=shifts,
        documents=documents,
        document_service=DocumentService(),
    )
    generate_report_handler = GenerateShiftReportHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator,
        project_members=members,
        shifts=shifts,
        shift_reports=reports,
        task_dispatcher=report_tasks,
        director_member_policy=DirectorMemberPolicy(),
    )
    archive_report_handler = ArchiveShiftReportHandler(
        transaction_manager=tx,
        clock=clock,
        project_members=members,
        shifts=shifts,
        shift_reports=reports,
        director_member_policy=DirectorMemberPolicy(),
    )
    list_shift_reports_handler = ListShiftReportsHandler(
        shift_reports=reports,
        shifts=shifts,
        project_members=members,
        director_member_policy=DirectorMemberPolicy(),
    )
    get_report_handler = GetReportHandler(
        shift_reports=reports,
        shifts=shifts,
        project_members=members,
        director_member_policy=DirectorMemberPolicy(),
    )
    get_report_download_url_handler = GetReportDownloadUrlHandler(
        shift_reports=reports,
        shifts=shifts,
        project_members=members,
        director_member_policy=DirectorMemberPolicy(),
        document_storage=storage,
    )
    create_resource_request_handler = CreateResourceRequestHandler(
        transaction_manager=tx,
        clock=clock,
        id_generator=id_generator,
        publisher=publisher,
        user_service=user_service,
        project_members=members,
        shifts=shifts,
        resource_requests=requests,
        shift_reports=reports,
        resource_request_service=ResourceRequestService(),
    )
    approve_resource_request_handler = ApproveResourceRequestHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        reservation_outbox=reservation_outbox,
        project_members=members,
        resource_requests=requests,
        shift_reports=reports,
        resource_request_service=ResourceRequestService(),
    )
    reject_resource_request_handler = RejectResourceRequestHandler(
        transaction_manager=tx,
        clock=clock,
        publisher=publisher,
        project_members=members,
        resource_requests=requests,
        shift_reports=reports,
        resource_request_service=ResourceRequestService(),
    )

    provider = Provider(scope=Scope.REQUEST)
    for instance, provides in (
        (create_project_handler, CreateProjectHandler),
        (list_projects_handler, ListActorProjectsHandler),
        (get_project_handler, GetProjectHandler),
        (update_project_handler, UpdateProjectHandler),
        (delete_project_handler, DeleteProjectHandler),
        (invite_project_member_handler, InviteProjectMemberHandler),
        (list_members_handler, ListProjectMembersHandler),
        (get_member_handler, GetProjectMemberHandler),
        (change_role_handler, ChangeProjectMemberRoleHandler),
        (remove_member_handler, RemoveProjectMemberHandler),
        (create_shift_handler, CreateShiftHandler),
        (approve_shift_handler, ApproveShiftHandler),
        (invite_participant_handler, InviteShiftParticipantHandler),
        (confirm_participant_handler, ConfirmShiftParticipantHandler),
        (decline_participant_handler, DeclineShiftParticipantHandler),
        (upload_document_handler, UploadShiftDocumentHandler),
        (generate_report_handler, GenerateShiftReportHandler),
        (archive_report_handler, ArchiveShiftReportHandler),
        (list_shift_reports_handler, ListShiftReportsHandler),
        (get_report_handler, GetReportHandler),
        (get_report_download_url_handler, GetReportDownloadUrlHandler),
        (create_resource_request_handler, CreateResourceRequestHandler),
        (approve_resource_request_handler, ApproveResourceRequestHandler),
        (reject_resource_request_handler, RejectResourceRequestHandler),
        (tx, TransactionManager),
        (projects, ProjectRepository),
        (members, ProjectMemberRepository),
        (shifts, ShiftRepository),
        (participants, ShiftParticipantRepository),
        (documents, InMemoryDocumentRepo),
        (reports, ShiftReportRepository),
        (requests, ResourceRequestRepository),
        (reservation_outbox, ReservationOutboxRepository),
    ):
        _provide_instance(provider, instance, provides)

    container = make_async_container(provider)
    app = FastAPI(
        title="Project service",
        version="0.1.0",
        description=PROJECT_API_DESCRIPTION,
        openapi_tags=PROJECT_OPENAPI_TAGS,
    )
    setup_dishka(container=container, app=app)
    app.add_exception_handler(ApplicationError, handlers.application_error_handler)
    app.include_router(project_router)
    return ProjectApiCrudContext(
        app=app,
        container=container,
        tx=tx,
        publisher=publisher,
        user_service=user_service,
        projects=projects,
        members=members,
        shifts=shifts,
        participants=participants,
        documents=documents,
        reports=reports,
        requests=requests,
        reservation_outbox=reservation_outbox,
        report_tasks=report_tasks,
    )


def test_project_http_crud_lifecycle() -> None:
    ctx = build_project_api_crud_context()
    owner_id = uuid4()

    try:
        with TestClient(ctx.app) as client:
            create_response = client.post(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Project lifecycle", "description": "initial"},
            )
            assert create_response.status_code == 200
            project = create_response.json()
            project_id = project["oid"]

            list_response = client.get(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
            )
            assert list_response.status_code == 200
            assert [item["oid"] for item in list_response.json()["items"]] == [project_id]

            get_response = client.get(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(owner_id)},
            )
            assert get_response.status_code == 200
            assert get_response.json()["title"] == "Project lifecycle"

            patch_response = client.patch(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(owner_id)},
                json={"title": "Project lifecycle updated", "description": "updated"},
            )
            assert patch_response.status_code == 200
            assert patch_response.json()["title"] == "Project lifecycle updated"

            archive_response = client.delete(
                f"/projects/{project_id}",
                headers={"X-User-Id": str(owner_id)},
            )
            assert archive_response.status_code == 204

            default_list_after_archive = client.get(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
            )
            archived_list = client.get(
                "/projects",
                headers={"X-User-Id": str(owner_id)},
                params={"include_archived": "true"},
            )
    finally:
        asyncio.run(ctx.container.close())

    assert default_list_after_archive.status_code == 200
    assert default_list_after_archive.json()["items"] == []
    assert archived_list.status_code == 200
    assert archived_list.json()["items"][0]["oid"] == project_id


def test_project_openapi_contains_domain_tags_and_service_metadata() -> None:
    ctx = build_project_api_crud_context()

    try:
        with TestClient(ctx.app) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            payload = response.json()
    finally:
        asyncio.run(ctx.container.close())

    assert payload["info"]["title"] == "Project service"
    assert payload["info"]["version"] == "0.1.0"
    assert "reservation workflow orchestration" in payload["info"]["description"]

    tag_names = {item["name"] for item in payload["tags"]}
    assert {
        "system",
        "projects",
        "members",
        "member-resources",
        "shifts",
        "participants",
        "documents",
        "reports",
        "resource-requests",
    }.issubset(tag_names)

    assert payload["paths"]["/health"]["get"]["tags"] == ["system"]
    assert payload["paths"]["/projects"]["post"]["tags"] == ["projects"]
    assert payload["paths"]["/projects/{project_id}/members"]["post"]["tags"] == ["members"]
    assert payload["paths"]["/projects/{project_id}/members/{target_user_id}/resources"]["get"]["tags"] == [
        "member-resources"
    ]
    assert payload["paths"]["/participants/{participant_id}/confirm"]["post"]["tags"] == ["participants"]
    assert payload["paths"]["/shifts/{shift_id}/reports/generate"]["post"]["tags"] == ["reports"]
    assert payload["paths"]["/reports/{report_id}"]["get"]["tags"] == ["reports"]
    assert payload["paths"]["/resource-requests/{request_id}/approve"]["post"]["tags"] == [
        "resource-requests"
    ]
    assert (
        payload["paths"]["/projects/{project_id}/members/{target_user_id}/resources"]["get"]["description"]
        .startswith("Returns resources owned by the target user")
    )


def test_shift_reports_http_flow() -> None:
    ctx = build_project_api_crud_context()
    director_id = uuid4()
    start_time = now_utc() + timedelta(hours=2)
    end_time = start_time + timedelta(hours=2)

    try:
        with TestClient(ctx.app) as client:
            project_response = client.post(
                "/projects",
                headers={"X-User-Id": str(director_id)},
                json={"title": "Reports flow", "description": "report api"},
            )
            assert project_response.status_code == 200
            project_id = project_response.json()["oid"]

            shift_response = client.post(
                f"/projects/{project_id}/shifts",
                headers={"X-User-Id": str(director_id)},
                json={
                    "title": "Report shift",
                    "description": "with report",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            )
            assert shift_response.status_code == 200
            shift_id = shift_response.json()["oid"]

            approve_shift_response = client.post(
                f"/shifts/{shift_id}/approve",
                headers={"X-User-Id": str(director_id)},
            )
            assert approve_shift_response.status_code == 200

            create_report_response = client.post(
                f"/shifts/{shift_id}/reports/generate",
                headers={"X-User-Id": str(director_id)},
            )
            assert create_report_response.status_code == 200, create_report_response.text
            report = create_report_response.json()
            report_id = report["oid"]
            assert report["version"] == 1
            assert report["generation_status_name"] == "PENDING"
            assert ctx.report_tasks.commands[0].report_id == UUID(report_id)

            list_reports_response = client.get(
                f"/shifts/{shift_id}/reports",
                headers={"X-User-Id": str(director_id)},
            )
            assert list_reports_response.status_code == 200
            assert [item["oid"] for item in list_reports_response.json()["items"]] == [report_id]

            stored_report = ctx.reports.data[UUID(report_id)]
            stored_report.generation_status = 40
            stored_report.file_name = "shift-report.xlsx"
            stored_report.bucket = "bucket"
            stored_report.storage_key = "reports/test/shift-report.xlsx"
            stored_report.mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            stored_report.generated_at = start_time
            stored_report.updated_at = start_time
            ctx.reports.data[UUID(report_id)] = stored_report

            get_report_response = client.get(
                f"/reports/{report_id}",
                headers={"X-User-Id": str(director_id)},
            )
            assert get_report_response.status_code == 200
            assert get_report_response.json()["file_name"] == "shift-report.xlsx"

            download_url_response = client.get(
                f"/reports/{report_id}/download-url",
                headers={"X-User-Id": str(director_id)},
            )
            assert download_url_response.status_code == 200
            assert download_url_response.json()["download_url"].endswith(
                "reports/test/shift-report.xlsx"
            )

            archive_response = client.delete(
                f"/reports/{report_id}",
                headers={"X-User-Id": str(director_id)},
            )
            assert archive_response.status_code == 200
            assert archive_response.json()["generation_status_name"] == "ARCHIVED"
    finally:
        asyncio.run(ctx.container.close())


def test_project_http_management_flow_for_members_shifts_participants_and_requests() -> None:
    ctx = build_project_api_crud_context()
    director_id = uuid4()
    invited_member_id = uuid4()
    participant_id = uuid4()
    declining_participant_id = uuid4()
    owner_user_id = uuid4()
    rejected_owner_user_id = uuid4()
    resource_id = uuid4()
    rejected_resource_id = uuid4()
    start_time = now_utc() + timedelta(hours=2)
    end_time = start_time + timedelta(hours=2)

    try:
        with TestClient(ctx.app) as client:
            project_response = client.post(
                "/projects",
                headers={"X-User-Id": str(director_id)},
                json={"title": "Management flow", "description": "project management"},
            )
            assert project_response.status_code == 200
            project_id = project_response.json()["oid"]

            invite_member_response = client.post(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(director_id)},
                json={"user_id": str(invited_member_id), "role": "CAMERA"},
            )
            assert invite_member_response.status_code == 200
            assert invite_member_response.json()["status"] == int(ProjectMemberStatus.INVITED)

            list_members_response = client.get(
                f"/projects/{project_id}/members",
                headers={"X-User-Id": str(director_id)},
                params={"include_inactive": "true"},
            )
            assert list_members_response.status_code == 200
            listed_user_ids = {item["user_id"] for item in list_members_response.json()["items"]}
            assert listed_user_ids == {str(director_id), str(invited_member_id)}

            get_member_response = client.get(
                f"/projects/{project_id}/members/{invited_member_id}",
                headers={"X-User-Id": str(director_id)},
                params={"include_inactive": "true"},
            )
            assert get_member_response.status_code == 200
            assert get_member_response.json()["role"] == "CAMERA"

            change_role_response = client.patch(
                f"/projects/{project_id}/members/{invited_member_id}/role",
                headers={"X-User-Id": str(director_id)},
                json={"role": "SOUND"},
            )
            assert change_role_response.status_code == 200
            assert change_role_response.json()["role"] == "SOUND"

            remove_member_response = client.delete(
                f"/projects/{project_id}/members/{invited_member_id}",
                headers={"X-User-Id": str(director_id)},
            )
            assert remove_member_response.status_code == 200
            assert remove_member_response.json()["status"] == int(ProjectMemberStatus.REMOVED)

            for member_id, role in (
                (participant_id, "ACTOR"),
                (declining_participant_id, "LIGHT"),
                (owner_user_id, "CAMERA"),
                (rejected_owner_user_id, "LIGHT"),
            ):
                ctx.members.data[(UUID(project_id), member_id)] = ProjectMember(
                    oid=uuid4(),
                    project_id=UUID(project_id),
                    user_id=member_id,
                    role=ProjectRole[role],
                    status=ProjectMemberStatus.ACTIVE,
                    invited_by=director_id,
                    created_at=start_time,
                    updated_at=start_time,
                )
            ctx.user_service.resources[(owner_user_id, "cameras")] = [
                UserResourceItem(
                    resource_kind="cameras",
                    resource_id=resource_id,
                    title="Camera",
                    description="Main camera",
                    resource_type="mirrorless",
                    size=None,
                    created_at=start_time,
                    windows=(),
                )
            ]
            ctx.user_service.resources[(rejected_owner_user_id, "lights")] = [
                UserResourceItem(
                    resource_kind="lights",
                    resource_id=rejected_resource_id,
                    title="Light",
                    description="Fill light",
                    resource_type="led",
                    size=None,
                    created_at=start_time,
                    windows=(),
                )
            ]

            shift_response = client.post(
                f"/projects/{project_id}/shifts",
                headers={"X-User-Id": str(director_id)},
                json={
                    "title": "Main shift",
                    "description": "workflow shift",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            )
            assert shift_response.status_code == 200
            shift_id = shift_response.json()["oid"]
            assert shift_response.json()["status"] == int(ShiftStatus.DRAFT)

            invite_participant_response = client.post(
                f"/shifts/{shift_id}/participants",
                headers={"X-User-Id": str(director_id)},
                json={
                    "user_id": str(participant_id),
                    "role": "ACTOR",
                    "time_from": start_time.isoformat(),
                    "time_to": end_time.isoformat(),
                },
            )
            assert invite_participant_response.status_code == 200
            invited_participant_record_id = invite_participant_response.json()["oid"]
            assert invite_participant_response.json()["status"] == int(
                ShiftParticipantStatus.INVITED
            )

            confirm_participant_response = client.post(
                f"/participants/{invited_participant_record_id}/confirm",
                headers={"X-User-Id": str(participant_id)},
            )
            assert confirm_participant_response.status_code == 200
            assert confirm_participant_response.json()["status"] == int(
                ShiftParticipantStatus.RESERVING
            )

            declining_invite_response = client.post(
                f"/shifts/{shift_id}/participants",
                headers={"X-User-Id": str(director_id)},
                json={
                    "user_id": str(declining_participant_id),
                    "role": "LIGHT",
                    "time_from": start_time.isoformat(),
                    "time_to": end_time.isoformat(),
                },
            )
            assert declining_invite_response.status_code == 200
            declining_record_id = declining_invite_response.json()["oid"]

            decline_response = client.post(
                f"/participants/{declining_record_id}/decline",
                headers={"X-User-Id": str(declining_participant_id)},
            )
            assert decline_response.status_code == 200
            assert decline_response.json()["status"] == int(ShiftParticipantStatus.DECLINED)

            create_request_response = client.post(
                f"/shifts/{shift_id}/resource-requests",
                headers={"X-User-Id": str(director_id)},
                json={
                    "resource_type": "camera",
                    "resource_id": str(resource_id),
                    "resource_owner_user_id": str(owner_user_id),
                    "time_from": start_time.isoformat(),
                    "time_to": end_time.isoformat(),
                },
            )
            assert create_request_response.status_code == 200
            request_id = create_request_response.json()["oid"]
            assert create_request_response.json()["status"] == int(
                ResourceRequestStatus.PENDING_OWNER
            )

            approve_request_response = client.post(
                f"/resource-requests/{request_id}/approve",
                headers={"X-User-Id": str(owner_user_id)},
            )
            assert approve_request_response.status_code == 200
            assert approve_request_response.json()["status"] == int(
                ResourceRequestStatus.RESERVING
            )

            rejected_request_response = client.post(
                f"/shifts/{shift_id}/resource-requests",
                headers={"X-User-Id": str(director_id)},
                json={
                    "resource_type": "light",
                    "resource_id": str(rejected_resource_id),
                    "resource_owner_user_id": str(rejected_owner_user_id),
                    "time_from": start_time.isoformat(),
                    "time_to": end_time.isoformat(),
                },
            )
            assert rejected_request_response.status_code == 200
            rejected_request_id = rejected_request_response.json()["oid"]

            reject_request_response = client.post(
                f"/resource-requests/{rejected_request_id}/reject",
                headers={"X-User-Id": str(rejected_owner_user_id)},
                json={"reason": "Busy"},
            )
            assert reject_request_response.status_code == 200
            assert reject_request_response.json()["status"] == int(
                ResourceRequestStatus.REJECTED_OWNER
            )
            assert reject_request_response.json()["rejection_reason"] == "Busy"

            approve_shift_response = client.post(
                f"/shifts/{shift_id}/approve",
                headers={"X-User-Id": str(director_id)},
            )
            assert approve_shift_response.status_code == 200
            assert approve_shift_response.json()["status"] == int(ShiftStatus.APPROVED)
    finally:
        asyncio.run(ctx.container.close())

    assert len(ctx.reservation_outbox.data) == 2
    assert ctx.user_service.existing_users == {
        invited_member_id,
        participant_id,
        declining_participant_id,
    }
