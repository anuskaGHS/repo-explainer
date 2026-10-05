"""Pydantic data models and schemas for request and response validation."""

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    """Request payload containing the GitHub repository URL to analyze."""

    repo_url: str = Field(
        ...,
        description="Public GitHub repository URL (e.g., https://github.com/user/repo)",
        examples=["https://github.com/octocat/Hello-World"],
    )


class ExplainResponse(BaseModel):
    """Response payload containing repository explanation details."""

    repo_name: str = Field(
        ...,
        description="Name of the cloned and analyzed repository",
    )
    files_found: int = Field(
        ...,
        description="Number of relevant files discovered and analyzed",
    )
    explanation: str = Field(
        ...,
        description="Structured plain-English explanation of the repository",
    )
