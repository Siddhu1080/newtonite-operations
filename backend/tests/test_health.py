
from fastapi.testclient import TestClient

from app.main import app
from app.models import ActivityLog, Team, TeamMember, User, WorkItem
from app.routers.auth import create_access_token, password_hasher
from datetime import datetime, timedelta, timezone

import jwt

from app.routers.auth import SECRET_KEY, ALGORITHM


def get_auth_headers(user_id: int) -> dict:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def create_test_user(db_session, email: str):
    user = User(
        name="Test User",
        email=email,
        password_hash=password_hasher.hash("TestPassword123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_test_team(db_session, owner: User):
    team = Team(name=f"Team {owner.email}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    membership = TeamMember(
        team_id=team.id,
        user_id=owner.id,
        role="admin",
    )
    db_session.add(membership)
    db_session.commit()

    return team


def create_test_work_item(
    client,
    user: User,
    team: Team,
    title: str,
    idempotency_key: str,
):
    return client.post(
        "/work-items/",
        json={
            "title": title,
            "description": "Created by automated test",
            "status": "Open",
            "priority": "Medium",
            "team_id": team.id,
        },
        headers={
            **get_auth_headers(user.id),
            "Idempotency-Key": idempotency_key,
        },
    )


def test_api_docs_available(client):
    response = client.get("/docs")
    assert response.status_code == 200


def test_protected_endpoint_rejects_unauthenticated_request(client):
    response = client.get("/auth/me")
    assert response.status_code in (401, 403)


def test_login_rejects_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "WrongPassword123",
        },
    )
    assert response.status_code == 401


def test_user_registration(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Registration Test",
            "email": "pytest-register@example.com",
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "pytest-register@example.com"


def test_team_member_can_create_work_item(client, db_session):
    user = create_test_user(db_session, "pytest-member@example.com")
    team = create_test_team(db_session, user)

    response = create_test_work_item(
        client,
        user,
        team,
        "Member Work Item",
        "pytest-create-member-001",
    )

    assert response.status_code in (200, 201)
    assert response.json()["title"] == "Member Work Item"


def test_non_member_cannot_create_work_item(client, db_session):
    owner = create_test_user(db_session, "pytest-owner@example.com")
    non_member = create_test_user(db_session, "pytest-nonmember@example.com")
    team = create_test_team(db_session, owner)

    response = create_test_work_item(
        client,
        non_member,
        team,
        "Unauthorized Work Item",
        "pytest-create-nonmember-001",
    )

    assert response.status_code in (403, 404)


def test_duplicate_idempotency_key_does_not_create_duplicate_work_item(
    client,
    db_session,
):
    user = create_test_user(db_session, "pytest-idempotency@example.com")
    team = create_test_team(db_session, user)

    payload = {
        "title": "Idempotency Test",
        "description": "Testing duplicate requests",
        "status": "Open",
        "priority": "Medium",
        "team_id": team.id,
    }
    headers = {
        **get_auth_headers(user.id),
        "Idempotency-Key": "pytest-idempotency-001",
    }

    first = client.post("/work-items/", json=payload, headers=headers)
    second = client.post("/work-items/", json=payload, headers=headers)

    assert first.status_code in (200, 201)
    assert second.status_code in (200, 201)
    assert first.json()["id"] == second.json()["id"]


def test_idempotency_key_rejects_different_payload(client, db_session):
    user = create_test_user(db_session, "pytest-conflict@example.com")
    team = create_test_team(db_session, user)

    headers = {
        **get_auth_headers(user.id),
        "Idempotency-Key": "pytest-conflict-001",
    }

    first = client.post(
        "/work-items/",
        json={
            "title": "Original Title",
            "description": "Original description",
            "status": "Open",
            "priority": "Medium",
            "team_id": team.id,
        },
        headers=headers,
    )

    second = client.post(
        "/work-items/",
        json={
            "title": "Different Title",
            "description": "Different description",
            "status": "Open",
            "priority": "Medium",
            "team_id": team.id,
        },
        headers=headers,
    )

    assert first.status_code in (200, 201)
    assert second.status_code == 409


def test_work_item_creation_creates_activity_log(client, db_session):
    user = create_test_user(db_session, "pytest-activity-create@example.com")
    team = create_test_team(db_session, user)

    response = create_test_work_item(
        client,
        user,
        team,
        "Activity Log Creation Test",
        "pytest-activity-create-001",
    )

    assert response.status_code in (200, 201)

    work_item_id = response.json()["id"]

    activity = (
        db_session.query(ActivityLog)
        .filter(
            ActivityLog.work_item_id == work_item_id,
            ActivityLog.action == "work_item.created",
        )
        .first()
    )

    assert activity is not None
    assert activity.actor_id == user.id


def test_work_item_update_creates_activity_log(client, db_session):
    user = create_test_user(db_session, "pytest-activity-update@example.com")
    team = create_test_team(db_session, user)

    create_response = create_test_work_item(
        client,
        user,
        team,
        "Original Update Test Title",
        "pytest-activity-update-create-001",
    )

    assert create_response.status_code in (200, 201)

    work_item_id = create_response.json()["id"]
    current_version = create_response.json()["version"]

    update_response = client.put(
        f"/work-items/{work_item_id}",
        json={
            "title": "Updated Test Title",
            "version": current_version,
        },
        headers=get_auth_headers(user.id),
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Test Title"

    activity = (
        db_session.query(ActivityLog)
        .filter(
            ActivityLog.work_item_id == work_item_id,
            ActivityLog.action == "work_item.updated",
        )
        .first()
    )

    assert activity is not None
    assert activity.actor_id == user.id
    assert activity.old_value is not None
    assert activity.new_value is not None


def test_work_item_status_can_be_updated(client, db_session):
    user = create_test_user(
        db_session,
        "pytest-status-update@example.com",
    )
    team = create_test_team(db_session, user)

    create_response = create_test_work_item(
        client,
        user,
        team,
        "Status Update Test",
        "pytest-status-update-create-001",
    )

    assert create_response.status_code == 201

    work_item_id = create_response.json()["id"]
    version = create_response.json()["version"]

    response = client.put(
        f"/work-items/{work_item_id}",
        json={
            "status": "In Progress",
            "version": version,
        },
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"


def test_invalid_work_item_status_is_rejected(client, db_session):
    user = create_test_user(
        db_session,
        "pytest-invalid-status@example.com",
    )
    team = create_test_team(db_session, user)

    create_response = create_test_work_item(
        client,
        user,
        team,
        "Invalid Status Test",
        "pytest-invalid-status-create-001",
    )

    assert create_response.status_code == 201

    work_item_id = create_response.json()["id"]
    version = create_response.json()["version"]

    response = client.put(
        f"/work-items/{work_item_id}",
        json={
            "status": "Something Invalid",
            "version": version,
        },
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 422



def test_stale_version_update_returns_conflict(client, db_session):
    user = create_test_user(
        db_session,
        "pytest-stale-version@example.com",
    )
    team = create_test_team(db_session, user)

    create_response = create_test_work_item(
        client,
        user,
        team,
        "Concurrency Test",
        "pytest-concurrency-create-001",
    )

    assert create_response.status_code == 201

    work_item_id = create_response.json()["id"]
    original_version = create_response.json()["version"]

    # First update uses the current version and should succeed.
    first_update = client.put(
        f"/work-items/{work_item_id}",
        json={
            "title": "First Update",
            "version": original_version,
        },
        headers=get_auth_headers(user.id),
    )

    assert first_update.status_code == 200
    assert first_update.json()["title"] == "First Update"

    # Second update reuses the now-stale version.
    second_update = client.put(
        f"/work-items/{work_item_id}",
        json={
            "title": "Stale Update",
            "version": original_version,
        },
        headers=get_auth_headers(user.id),
    )

    assert second_update.status_code == 409

    # Confirm that the stale update did not overwrite the first update.
    get_response = client.get(
        f"/work-items/{work_item_id}",
        headers=get_auth_headers(user.id),
    )

    assert get_response.status_code == 200
    assert get_response.json()["title"] == "First Update"
    assert get_response.json()["version"] == original_version + 1



def test_team_creation_makes_creator_admin(client, db_session):
    response = client.post(
        "/auth/register",
        json={
            "name": "Team Creator",
            "email": "pytest-team-creator@example.com",
            "password": "TestPassword123",
        },
    )
    assert response.status_code == 201

    user = (
        db_session.query(User)
        .filter(User.email == "pytest-team-creator@example.com")
        .first()
    )
    assert user is not None

    response = client.post(
        "/teams/",
        json={"name": "Creator Test Team"},
        headers=get_auth_headers(user.id),
    )
    assert response.status_code == 201

    team_id = response.json()["id"]

    membership = (
        db_session.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id,
        )
        .first()
    )
    assert membership is not None
    assert membership.role == "admin"


def test_user_can_list_only_their_teams(client, db_session):
    user = create_test_user(db_session, "pytest-list-teams@example.com")
    other_user = create_test_user(
        db_session,
        "pytest-other-teams@example.com",
    )

    create_test_team(db_session, user)
    create_test_team(db_session, other_user)

    response = client.get(
        "/teams/",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == f"Team {user.email}"


def test_admin_can_add_team_member(client, db_session):
    admin = create_test_user(db_session, "pytest-team-admin@example.com")
    new_member = create_test_user(
        db_session,
        "pytest-new-member@example.com",
    )
    team = create_test_team(db_session, admin)

    response = client.post(
        f"/teams/{team.id}/members",
        json={
            "user_id": new_member.id,
            "role": "member",
        },
        headers=get_auth_headers(admin.id),
    )

    assert response.status_code == 201

    membership = (
        db_session.query(TeamMember)
        .filter(
            TeamMember.team_id == team.id,
            TeamMember.user_id == new_member.id,
        )
        .first()
    )
    assert membership is not None
    assert membership.role == "member"


def test_regular_member_cannot_add_team_member(client, db_session):
    admin = create_test_user(db_session, "pytest-member-admin@example.com")
    regular_member = create_test_user(
        db_session,
        "pytest-regular-member@example.com",
    )
    target_user = create_test_user(
        db_session,
        "pytest-target-member@example.com",
    )
    team = create_test_team(db_session, admin)

    db_session.add(
        TeamMember(
            team_id=team.id,
            user_id=regular_member.id,
            role="member",
        )
    )
    db_session.commit()

    response = client.post(
        f"/teams/{team.id}/members",
        json={
            "user_id": target_user.id,
            "role": "member",
        },
        headers=get_auth_headers(regular_member.id),
    )

    assert response.status_code == 403


def test_duplicate_team_membership_is_rejected(client, db_session):
    admin = create_test_user(
        db_session,
        "pytest-duplicate-admin@example.com",
    )
    existing_member = create_test_user(
        db_session,
        "pytest-duplicate-member@example.com",
    )
    team = create_test_team(db_session, admin)

    db_session.add(
        TeamMember(
            team_id=team.id,
            user_id=existing_member.id,
            role="member",
        )
    )
    db_session.commit()

    response = client.post(
        f"/teams/{team.id}/members",
        json={
            "user_id": existing_member.id,
            "role": "member",
        },
        headers=get_auth_headers(admin.id),
    )

    assert response.status_code == 409


def test_team_member_can_create_comment(client, db_session):
    user = create_test_user(db_session, "pytest-comment-create@example.com")
    team = create_test_team(db_session, user)

    work_item_response = create_test_work_item(
        client,
        user,
        team,
        "Comment Creation Test",
        "pytest-comment-create-workitem-001",
    )
    assert work_item_response.status_code == 201

    item_id = work_item_response.json()["id"]

    response = client.post(
        f"/work-items/{item_id}/comments/",
        json={"body": "This is a test comment"},
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 201
    assert response.json()["body"] == "This is a test comment"
    assert response.json()["user_id"] == user.id
    assert response.json()["work_item_id"] == item_id


def test_team_member_can_list_comments(client, db_session):
    user = create_test_user(db_session, "pytest-comment-list@example.com")
    team = create_test_team(db_session, user)

    work_item_response = create_test_work_item(
        client,
        user,
        team,
        "Comment Listing Test",
        "pytest-comment-list-workitem-001",
    )
    item_id = work_item_response.json()["id"]

    client.post(
        f"/work-items/{item_id}/comments/",
        json={"body": "First comment"},
        headers=get_auth_headers(user.id),
    )
    client.post(
        f"/work-items/{item_id}/comments/",
        json={"body": "Second comment"},
        headers=get_auth_headers(user.id),
    )

    response = client.get(
        f"/work-items/{item_id}/comments/",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["body"] == "First comment"
    assert response.json()[1]["body"] == "Second comment"


def test_non_member_cannot_access_comments(client, db_session):
    owner = create_test_user(db_session, "pytest-comment-owner@example.com")
    outsider = create_test_user(
        db_session,
        "pytest-comment-outsider@example.com",
    )
    team = create_test_team(db_session, owner)

    work_item_response = create_test_work_item(
        client,
        owner,
        team,
        "Private Comment Test",
        "pytest-comment-private-workitem-001",
    )
    item_id = work_item_response.json()["id"]

    headers = get_auth_headers(outsider.id)

    create_response = client.post(
        f"/work-items/{item_id}/comments/",
        json={"body": "Unauthorized comment"},
        headers=headers,
    )
    list_response = client.get(
        f"/work-items/{item_id}/comments/",
        headers=headers,
    )

    assert create_response.status_code == 403
    assert list_response.status_code == 403


def test_empty_comment_is_rejected(client, db_session):
    user = create_test_user(db_session, "pytest-empty-comment@example.com")
    team = create_test_team(db_session, user)

    work_item_response = create_test_work_item(
        client,
        user,
        team,
        "Empty Comment Test",
        "pytest-empty-comment-workitem-001",
    )
    item_id = work_item_response.json()["id"]

    response = client.post(
        f"/work-items/{item_id}/comments/",
        json={"body": "   "},
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 422


def test_comments_for_missing_work_item_return_404(client, db_session):
    user = create_test_user(db_session, "pytest-comment-missing@example.com")

    response = client.get(
        "/work-items/999999/comments/",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 404


def test_team_member_can_list_activities(client, db_session):
    user = create_test_user(
        db_session,
        "pytest-activities-list@example.com",
    )
    team = create_test_team(db_session, user)

    response = create_test_work_item(
        client,
        user,
        team,
        "Activity History Test",
        "pytest-activities-list-create-001",
    )
    assert response.status_code == 201

    item_id = response.json()["id"]

    activity_response = client.get(
        f"/work-items/{item_id}/activities/",
        headers=get_auth_headers(user.id),
    )

    assert activity_response.status_code == 200
    activities = activity_response.json()
    assert len(activities) >= 1
    assert activities[0]["action"] == "work_item.created"
    assert activities[0]["actor_id"] == user.id


def test_activity_history_includes_updates(client, db_session):
    user = create_test_user(
        db_session,
        "pytest-activities-update@example.com",
    )
    team = create_test_team(db_session, user)

    response = create_test_work_item(
        client,
        user,
        team,
        "Original Activity Title",
        "pytest-activities-update-create-001",
    )
    assert response.status_code == 201

    item_id = response.json()["id"]
    version = response.json()["version"]

    update_response = client.put(
        f"/work-items/{item_id}",
        json={
            "title": "Updated Activity Title",
            "version": version,
        },
        headers=get_auth_headers(user.id),
    )
    assert update_response.status_code == 200

    history_response = client.get(
        f"/work-items/{item_id}/activities/",
        headers=get_auth_headers(user.id),
    )

    assert history_response.status_code == 200
    actions = [activity["action"] for activity in history_response.json()]
    assert "work_item.created" in actions
    assert "work_item.updated" in actions


def test_non_member_cannot_list_activities(client, db_session):
    owner = create_test_user(
        db_session,
        "pytest-activities-owner@example.com",
    )
    outsider = create_test_user(
        db_session,
        "pytest-activities-outsider@example.com",
    )
    team = create_test_team(db_session, owner)

    response = create_test_work_item(
        client,
        owner,
        team,
        "Private Activity History",
        "pytest-activities-private-create-001",
    )
    assert response.status_code == 201

    item_id = response.json()["id"]

    history_response = client.get(
        f"/work-items/{item_id}/activities/",
        headers=get_auth_headers(outsider.id),
    )

    assert history_response.status_code == 403


def test_missing_work_item_activity_history_returns_404(client, db_session):
    user = create_test_user(
        db_session,
        "pytest-activities-missing@example.com",
    )

    response = client.get(
        "/work-items/999999/activities/",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 404


def test_team_member_can_get_single_work_item(client, db_session):
    user = create_test_user(db_session, "pytest-get-item@example.com")
    team = create_test_team(db_session, user)

    created = create_test_work_item(
        client,
        user,
        team,
        "Get Single Item Test",
        "pytest-get-single-item-001",
    )
    assert created.status_code == 201

    item_id = created.json()["id"]

    response = client.get(
        f"/work-items/{item_id}",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Get Single Item Test"


def test_team_member_can_list_work_items(client, db_session):
    user = create_test_user(db_session, "pytest-list-items@example.com")
    team = create_test_team(db_session, user)

    for index in range(2):
        response = create_test_work_item(
            client,
            user,
            team,
            f"List Item {index}",
            f"pytest-list-item-{index}-001",
        )
        assert response.status_code == 201

    response = client.get(
        "/work-items/",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert "List Item 0" in titles
    assert "List Item 1" in titles


def test_work_item_list_supports_status_filter(client, db_session):
    user = create_test_user(db_session, "pytest-filter-items@example.com")
    team = create_test_team(db_session, user)

    created = create_test_work_item(
        client,
        user,
        team,
        "Open Filter Test",
        "pytest-filter-open-001",
    )
    assert created.status_code == 201

    response = client.get(
        "/work-items/?status=Open",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert all(item["status"] == "Open" for item in response.json())
    assert any(
        item["title"] == "Open Filter Test"
        for item in response.json()
    )


def test_non_member_cannot_get_single_work_item(client, db_session):
    owner = create_test_user(db_session, "pytest-get-owner@example.com")
    outsider = create_test_user(db_session, "pytest-get-outsider@example.com")
    team = create_test_team(db_session, owner)

    created = create_test_work_item(
        client,
        owner,
        team,
        "Private Work Item",
        "pytest-get-private-item-001",
    )
    assert created.status_code == 201

    item_id = created.json()["id"]

    response = client.get(
        f"/work-items/{item_id}",
        headers=get_auth_headers(outsider.id),
    )

    assert response.status_code == 403


def test_work_item_pagination_respects_limit(client, db_session):
    user = create_test_user(db_session, "pytest-pagination@example.com")
    team = create_test_team(db_session, user)

    for index in range(3):
        response = create_test_work_item(
            client,
            user,
            team,
            f"Pagination Item {index}",
            f"pytest-pagination-{index}-001",
        )
        assert response.status_code == 201

    response = client.get(
        "/work-items/?skip=0&limit=2",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_work_item_priority_filter(client, db_session):
    user = create_test_user(db_session, "pytest-priority-filter@example.com")
    team = create_test_team(db_session, user)

    for index, priority in enumerate(["High", "Low"]):
        response = client.post(
            "/work-items/",
            json={
                "title": f"Priority Item {index}",
                "description": "Priority filter test",
                "team_id": team.id,
                "priority": priority,
            },
            headers={
                **get_auth_headers(user.id),
                "Idempotency-Key": f"pytest-priority-filter-{index}-001",
            },
        )
        assert response.status_code == 201

    response = client.get(
        "/work-items/?priority=High",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["priority"] == "High"


def test_work_item_cannot_be_assigned_to_non_member(client, db_session):
    user = create_test_user(db_session, "pytest-assignment-owner@example.com")
    outsider = create_test_user(
        db_session,
        "pytest-assignment-outsider@example.com",
    )
    team = create_test_team(db_session, user)

    response = client.post(
        "/work-items/",
        json={
            "title": "Invalid Assignment Test",
            "description": "Assignee must belong to the team",
            "team_id": team.id,
            "assignee_id": outsider.id,
        },
        headers={
            **get_auth_headers(user.id),
            "Idempotency-Key": "pytest-invalid-assignee-001",
        },
    )

    assert response.status_code == 422


def test_non_member_cannot_list_another_teams_work_items(
    client,
    db_session,
):
    owner = create_test_user(
        db_session,
        "pytest-list-private-owner@example.com",
    )
    outsider = create_test_user(
        db_session,
        "pytest-list-private-outsider@example.com",
    )
    team = create_test_team(db_session, owner)

    created = create_test_work_item(
        client,
        owner,
        team,
        "Private List Item",
        "pytest-list-private-item-001",
    )
    assert created.status_code == 201

    response = client.get(
        f"/work-items/?team_id={team.id}",
        headers=get_auth_headers(outsider.id),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_regular_member_cannot_promote_themselves(client, db_session):
    admin = create_test_user(
        db_session,
        "pytest-promotion-admin@example.com",
    )
    regular_member = create_test_user(
        db_session,
        "pytest-promotion-member@example.com",
    )
    team = create_test_team(db_session, admin)

    db_session.add(
        TeamMember(
            team_id=team.id,
            user_id=regular_member.id,
            role="member",
        )
    )
    db_session.commit()

    response = client.post(
        f"/teams/{team.id}/members",
        json={
            "user_id": regular_member.id,
            "role": "admin",
        },
        headers=get_auth_headers(regular_member.id),
    )

    assert response.status_code == 403

    db_session.expire_all()
    membership = (
        db_session.query(TeamMember)
        .filter(
            TeamMember.team_id == team.id,
            TeamMember.user_id == regular_member.id,
        )
        .first()
    )

    assert membership.role == "member"


def test_register_duplicate_email_returns_conflict(client):
    payload = {
        "name": "Duplicate Registration Test",
        "email": "pytest-duplicate-register@example.com",
        "password": "TestPassword123",
    }

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert (
        second_response.json()["detail"]
        == "An account with this email already exists"
    )


def test_auth_me_rejects_invalid_token(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401


def test_inactive_user_cannot_access_protected_endpoint(client, db_session):
    user = create_test_user(
        db_session,
        "pytest-inactive-user@example.com",
    )

    user.is_active = False
    db_session.commit()

    response = client.get(
        "/auth/me",
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 401


def test_auth_me_rejects_expired_token(client):
    expired_token = jwt.encode(
        {
            "sub": "1",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
   

def test_work_item_update_rejects_null_status(client, db_session):
    user = create_test_user(
        db_session,
        "pytest-null-status@example.com",
    )
    team = create_test_team(db_session, user)

    created = create_test_work_item(
        client,
        user,
        team,
        "Null Status Test",
        "pytest-null-status-create-001",
    )
    assert created.status_code == 201

    item_id = created.json()["id"]
    version = created.json()["version"]

    response = client.put(
        f"/work-items/{item_id}",
        json={
            "status": None,
            "version": version,
        },
        headers=get_auth_headers(user.id),
    )

    assert response.status_code == 422


def test_work_item_update_rejects_null_title_and_priority(
    client, db_session
):
    user = create_test_user(
        db_session,
        "pytest-null-fields@example.com",
    )
    team = create_test_team(db_session, user)

    created = create_test_work_item(
        client,
        user,
        team,
        "Null Fields Test",
        "pytest-null-fields-create-001",
    )
    assert created.status_code == 201

    item_id = created.json()["id"]
    version = created.json()["version"]
    headers = get_auth_headers(user.id)

    for field in ("title", "priority"):
        response = client.put(
            f"/work-items/{item_id}",
            json={field: None, "version": version},
            headers=headers,
        )
        assert response.status_code == 422

def test_non_member_cannot_update_another_teams_work_item(
    client, db_session
):
    owner = create_test_user(
        db_session,
        "pytest-update-owner@example.com",
    )
    outsider = create_test_user(
        db_session,
        "pytest-update-outsider@example.com",
    )
    team = create_test_team(db_session, owner)

    created = create_test_work_item(
        client,
        owner,
        team,
        "Private Update Test",
        "pytest-update-private-item-001",
    )
    assert created.status_code == 201

    item_id = created.json()["id"]
    original_title = created.json()["title"]
    original_version = created.json()["version"]

    response = client.put(
        f"/work-items/{item_id}",
        json={
            "title": "Unauthorized Change",
            "version": original_version,
        },
        headers=get_auth_headers(outsider.id),
    )

    assert response.status_code == 403

    # Confirm the original work item was not changed.
    db_session.expire_all()
    item = (
        db_session.query(WorkItem)
        .filter(WorkItem.id == item_id)
        .first()
    )

    assert item is not None
    assert item.title == original_title
    assert item.version == original_version