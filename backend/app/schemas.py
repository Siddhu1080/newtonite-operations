
from datetime import datetime
from typing import Literal
from pydantic import field_validator
from pydantic import BaseModel, ConfigDict, EmailStr, Field


WorkItemStatus = Literal[
    "Open",
    "In Progress",
    "Completed",
    "Cancelled",
]

WorkItemPriority = Literal[
    "Low",
    "Medium",
    "High",
    "Urgent",
]


class WorkItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    team_id: int
    assignee_id: int | None = None
    priority: WorkItemPriority = "Medium"



class WorkItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: WorkItemStatus | None = None
    priority: WorkItemPriority | None = None
    assignee_id: int | None = None
    version: int = Field(ge=1)

    @field_validator("title", "status", "priority", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value



class WorkItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: str
    priority: str
    team_id: int
    created_by: int
    assignee_id: int | None
    version: int
    created_at: datetime
    updated_at: datetime



from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value



class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
