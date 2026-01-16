"""Pydantic schemas for GitHub repository operations."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RepoVisibility(str, Enum):
    """Repository visibility options."""

    PUBLIC = "public"
    PRIVATE = "private"


class RepoTemplate(str, Enum):
    """Available repository starter templates."""

    EMPTY = "empty"
    NEXTJS = "nextjs"
    FASTAPI = "fastapi"
    REACT_VITE = "react-vite"
    PYTHON_PACKAGE = "python-package"


class GitHubOwner(BaseModel):
    """Schema representing a GitHub user or organization that can own repositories."""

    login: str
    id: int
    type: Literal["User", "Organization"]
    avatar_url: Optional[str] = None


class CreateRepositoryRequest(BaseModel):
    """Schema for creating a new GitHub repository."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=350)
    visibility: RepoVisibility = RepoVisibility.PRIVATE
    owner: str
    template: RepoTemplate = RepoTemplate.EMPTY
    auto_scaffold: bool = True
    feature_description: Optional[str] = None


class CreateRepositoryResponse(BaseModel):
    """Schema for the response after creating a repository."""

    id: int
    name: str
    full_name: str
    html_url: str
    clone_url: str
    default_branch: str
    project_id: str


class AvailabilityCheckRequest(BaseModel):
    """Schema for checking repository name availability."""

    owner: str
    name: str = Field(..., min_length=1, max_length=100)


class AvailabilityCheckResponse(BaseModel):
    """Schema for availability check response."""

    available: bool
    suggestion: Optional[str] = None


class OwnersListResponse(BaseModel):
    """Schema for list of owners response."""

    owners: list[GitHubOwner]
