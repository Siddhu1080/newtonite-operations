
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    team_memberships = relationship(
        "TeamMember", back_populates="user"
    )


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    members = relationship(
        "TeamMember", back_populates="team"
    )
    work_items = relationship(
        "WorkItem", back_populates="team"
    )


class TeamMember(Base):
    __tablename__ = "team_members"

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(30), nullable=False, default="member")

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


class WorkItem(Base):
    __tablename__ = "work_items"

    __table_args__ = (
        Index("ix_work_items_team_status", "team_id", "status"),
        Index("ix_work_items_assignee_status", "assignee_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(30), nullable=False, default="Open")
    priority = Column(String(30), nullable=False, default="Medium")

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    version = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    team = relationship("Team", back_populates="work_items")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assignee_id])

    comments = relationship(
        "Comment", back_populates="work_item",
        cascade="all, delete-orphan"
    )
    activities = relationship(
        "ActivityLog", back_populates="work_item",
        cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(
        Integer, ForeignKey("work_items.id"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    work_item = relationship("WorkItem", back_populates="comments")
    user = relationship("User")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    work_item_id = Column(
        Integer, ForeignKey("work_items.id"), nullable=False
    )
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    action = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    work_item = relationship("WorkItem", back_populates="activities")
    actor = relationship("User")
