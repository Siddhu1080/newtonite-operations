
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Comment, TeamMember, User, WorkItem
from app.routers.auth import get_current_user


router = APIRouter(
    prefix="/work-items/{item_id}/comments",
    tags=["Comments"],
)


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: int
    work_item_id: int
    user_id: int
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


def get_accessible_work_item(
    item_id: int,
    db: Session,
    current_user: User,
) -> WorkItem:
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

    return work_item


@router.post(
    "/",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    item_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    work_item = get_accessible_work_item(
        item_id,
        db,
        current_user,
    )

    body = data.body.strip()

    if not body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment cannot be empty",
        )

    comment = Comment(
        work_item_id=work_item.id,
        user_id=current_user.id,
        body=body,
    )

    db.add(comment)

    try:
        db.commit()
        db.refresh(comment)
        return comment
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create comment",
        )


@router.get(
    "/",
    response_model=list[CommentResponse],
)
def list_comments(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    work_item = get_accessible_work_item(
        item_id,
        db,
        current_user,
    )

    return (
        db.query(Comment)
        .filter(Comment.work_item_id == work_item.id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )
