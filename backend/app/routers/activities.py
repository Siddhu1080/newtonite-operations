
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActivityLog, TeamMember, User, WorkItem
from app.routers.auth import get_current_user


router = APIRouter(
    prefix="/work-items/{item_id}/activities",
    tags=["Activity Logs"],
)


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_item_id: int
    actor_id: int
    action: str
    old_value: str | None
    new_value: str | None
    created_at: datetime


@router.get("/", response_model=list[ActivityResponse])
def list_activities(
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

    membership = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == work_item.team_id,
            TeamMember.user_id == current_user.id,
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    return (
        db.query(ActivityLog)
        .filter(ActivityLog.work_item_id == item_id)
        .order_by(ActivityLog.created_at.asc(), ActivityLog.id.asc())
        .all()
    )
