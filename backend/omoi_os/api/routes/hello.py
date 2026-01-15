"""Hello World API route.

A simple endpoint to verify the API is working correctly.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class HelloResponse(BaseModel):
    """Response model for the hello endpoint."""

    message: str
    timestamp: str
    version: str


class HelloNameResponse(BaseModel):
    """Response model for personalized hello."""

    message: str
    name: str
    timestamp: str


@router.get("", response_model=HelloResponse)
async def hello():
    """Return a hello world message.

    Returns a simple greeting with timestamp and API version.
    """
    return HelloResponse(
        message="Hello, World!",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
    )


@router.get("/{name}", response_model=HelloNameResponse)
async def hello_name(name: str):
    """Return a personalized hello message.

    Args:
        name: The name to greet.

    Returns:
        A personalized greeting with timestamp.
    """
    return HelloNameResponse(
        message=f"Hello, {name}!",
        name=name,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
