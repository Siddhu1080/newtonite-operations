
import hashlib
import json
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import text, update as sql_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActivityLog, TeamMember, User, WorkItem
from app.routers.auth import get_current_user
from app.schemas import WorkItemCreate, WorkItemResponse, WorkItemUpdate


router = APIRouter(prefix="/work-items", tags=["Work Items"])


def verify_team_membership(
    db: Session,
    team_id: int,
    user_id: int,
) -> None:
    membership = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )


def validate_assignee(
    db: Session,
    team_id: int,
    assignee_id: int | None,
) -> None:
    if assignee_id is None:
        return

    assignee = (
        db.query(User)
        .join(TeamMember, TeamMember.user_id == User.id)
        .filter(
            User.id == assignee_id,
            User.is_active.is_(True),
            TeamMember.team_id == team_id,
        )
        .first()
    )

    if assignee is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assignee must be an active member of the team",
        )


def add_activity_log(
    db: Session,
    work_item_id: int,
    actor_id: int,
    action: str,
    old_value: dict | None,
    new_value: dict,
) -> None:
    activity = ActivityLog(
        work_item_id=work_item_id,
        actor_id=actor_id,
        action=action,
        old_value=json.dumps(old_value) if old_value is not None else None,
        new_value=json.dumps(new_value),
    )
    db.add(activity)


@router.post(
    "/",
    response_model=WorkItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_work_item(
    item: WorkItemCreate,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check team access before processing the request.
    verify_team_membership(db, item.team_id, current_user.id)

    # Create a stable hash of the validated request body.
    request_data = item.model_dump(mode="json")
    request_hash = hashlib.sha256(
        json.dumps(
            request_data,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    try:
        # Reserve the key. The database UNIQUE constraint
        # prevents the same user from reserving it twice.
        db.execute(
            text("""
                INSERT INTO idempotency_keys
                    (user_id, idempotency_key, request_hash)
                VALUES
                    (:user_id, :key, :request_hash)
            """),
            {
                "user_id": current_user.id,
                "key": idempotency_key,
                "request_hash": request_hash,
            },
        )

    except IntegrityError:
        db.rollback()

        # Look up a previously committed request.
        existing = (
            db.execute(
                text("""
                    SELECT request_hash, work_item_id
                    FROM idempotency_keys
                    WHERE user_id = :user_id
                      AND idempotency_key = :key
                """),
                {
                    "user_id": current_user.id,
                    "key": idempotency_key,
                },
            )
            .mappings()
            .first()
        )

        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not reserve the idempotency key",
            )

        if existing["request_hash"] != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This idempotency key was already used "
                    "with a different request body"
                ),
            )

        if existing["work_item_id"] is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The original request is not yet complete. Retry shortly.",
            )

        original_item = (
            db.query(WorkItem)
            .filter(WorkItem.id == existing["work_item_id"])
            .first()
        )

        if original_item is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The original work item could not be found",
            )

        return original_item

    try:
        validate_assignee(
            db,
            item.team_id,
            item.assignee_id,
        )

        work_item = WorkItem(
            title=item.title,
            description=item.description,
            team_id=item.team_id,
            assignee_id=item.assignee_id,
            priority=item.priority,
            status="Open",
            created_by=current_user.id,
        )

        db.add(work_item)
        db.flush()

        # Record the creation activity in the same transaction.
        add_activity_log(
            db=db,
            work_item_id=work_item.id,
            actor_id=current_user.id,
            action="work_item.created",
            old_value=None,
            new_value={
                "title": work_item.title,
                "description": work_item.description,
                "status": work_item.status,
                "priority": work_item.priority,
                "team_id": work_item.team_id,
                "assignee_id": work_item.assignee_id,
            },
        )

        # Link the idempotency key to the created work item.
        db.execute(
            text("""
                UPDATE idempotency_keys
                SET work_item_id = :work_item_id
                WHERE user_id = :user_id
                  AND idempotency_key = :key
            """),
            {
                "work_item_id": work_item.id,
                "user_id": current_user.id,
                "key": idempotency_key,
            },
        )

        # Commit the key, work item, and activity log together.
        db.commit()
        db.refresh(work_item)

        return work_item

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create work item",
        )


@router.get("/", response_model=list[WorkItemResponse])
def list_work_items(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    team_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(WorkItem)
        .join(TeamMember, TeamMember.team_id == WorkItem.team_id)
        .filter(TeamMember.user_id == current_user.id)
    )

    if status_filter:
        query = query.filter(WorkItem.status == status_filter)

    if priority:
        query = query.filter(WorkItem.priority == priority)

    if team_id is not None:
        query = query.filter(WorkItem.team_id == team_id)

    return (
        query.order_by(WorkItem.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{item_id}", response_model=WorkItemResponse)
def get_work_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    work_item = (
        db.query(WorkItem)
        .filter(WorkItem.id == item_id)
        .first()
    )

    if work_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found",
        )

    verify_team_membership(db, work_item.team_id, current_user.id)

    return work_item


@router.put("/{item_id}", response_model=WorkItemResponse)
def update_work_item(
    item_id: int,
    item: WorkItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    work_item = (
        db.query(WorkItem)
        .filter(WorkItem.id == item_id)
        .first()
    )

    if work_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work item not found",
        )

    verify_team_membership(db, work_item.team_id, current_user.id)

    changes = item.model_dump(exclude_unset=True)
    expected_version = changes.pop("version", None)

    if expected_version is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The current version is required",
        )

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update",
        )

    allowed_fields = {
        "title",
        "description",
        "status",
        "priority",
        "assignee_id",
    }
    invalid_fields = set(changes) - allowed_fields

    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported fields: {', '.join(sorted(invalid_fields))}",
        )

    if "assignee_id" in changes:
        validate_assignee(
            db,
            work_item.team_id,
            changes["assignee_id"],
        )

    old_values = {
        field: getattr(work_item, field)
        for field in changes
    }

    try:
        # Only update if the version still matches.
        result = db.execute(
            sql_update(WorkItem)
            .where(
                WorkItem.id == item_id,
                WorkItem.team_id == work_item.team_id,
                WorkItem.version == expected_version,
            )
            .values(
                **changes,
                version=WorkItem.version + 1,
                updated_at=datetime.utcnow(),
            )
        )

        if result.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This work item has changed. "
                    "Fetch the latest version and try again."
                ),
            )

        add_activity_log(
            db=db,
            work_item_id=item_id,
            actor_id=current_user.id,
            action="work_item.updated",
            old_value=old_values,
            new_value=changes,
        )

        db.commit()
        db.expire_all()

        return (
            db.query(WorkItem)
            .filter(WorkItem.id == item_id)
            .one()
        )

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update work item",
        )
