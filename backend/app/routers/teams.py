
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Team, TeamMember, User
from app.routers.auth import get_current_user


router = APIRouter(prefix="/teams", tags=["Teams"])


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Team name cannot be empty")

        return value


class TeamResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TeamMemberCreate(BaseModel):
    user_id: int = Field(gt=0)
    role: Literal["admin", "member"] = "member"


class TeamMemberResponse(BaseModel):
    user_id: int
    name: str
    email: str
    role: str


def get_team_membership(
    db: Session,
    team_id: int,
    user_id: int,
) -> TeamMember | None:
    return (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        )
        .first()
    )


def require_team_admin(
    db: Session,
    team_id: int,
    user_id: int,
) -> TeamMember:
    membership = get_team_membership(db, team_id, user_id)

    if membership is None or membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team admins can perform this action",
        )

    return membership


@router.post(
    "/",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = data.name

    existing = db.query(Team).filter(Team.name == name).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A team with this name already exists",
        )

    try:
        team = Team(name=name)
        db.add(team)
        db.flush()

        # The creator becomes the first team admin.
        db.add(
            TeamMember(
                team_id=team.id,
                user_id=current_user.id,
                role="admin",
            )
        )

        db.commit()
        db.refresh(team)

        return team

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A team with this name already exists",
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create team",
        )


@router.get("/", response_model=list[TeamResponse])
def list_my_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Team)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .filter(TeamMember.user_id == current_user.id)
        .order_by(Team.id)
        .all()
    )


@router.post(
    "/{team_id}/members",
    status_code=status.HTTP_201_CREATED,
)
def add_team_member(
    team_id: int,
    data: TeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = db.query(Team).filter(Team.id == team_id).first()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    require_team_admin(db, team_id, current_user.id)

    user = db.query(User).filter(User.id == data.user_id).first()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active user not found",
        )

    existing = get_team_membership(db, team_id, data.user_id)

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a team member",
        )

    membership = TeamMember(
        team_id=team_id,
        user_id=user.id,
        role=data.role,
    )

    try:
        db.add(membership)
        db.commit()

        return {"message": "Team member added successfully"}

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a team member",
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add team member",
        )


@router.get(
    "/{team_id}/members",
    response_model=list[TeamMemberResponse],
)
def list_team_members(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = db.query(Team).filter(Team.id == team_id).first()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    membership = get_team_membership(db, team_id, current_user.id)

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )

    rows = (
        db.query(TeamMember, User)
        .join(User, User.id == TeamMember.user_id)
        .filter(TeamMember.team_id == team_id)
        .order_by(User.id)
        .all()
    )

    return [
        {
            "user_id": member.user_id,
            "name": user.name,
            "email": user.email,
            "role": member.role,
        }
        for member, user in rows
    ]
