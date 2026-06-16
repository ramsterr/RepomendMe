from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

SlotName = Literal[
    "alternatives",
    "addons",
    "companions",
    "starters",
    "trending",
    "maintainer_wanted",
]


class Repo(BaseModel):
    id: int
    full_name: str
    description: str | None = None
    stars: int
    language: str | None = None
    topics: list[str] = Field(default_factory=list)


class Slot(BaseModel):
    name: SlotName
    repos: list[Repo]


class RecommendResponse(BaseModel):
    source_repo: str
    slots: list[Slot]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str = "0.0.0"


app = FastAPI(
    title="RepoRelay",
    version="0.0.0",
    description="GitHub repository recommendation engine",
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/recommend", response_model=RecommendResponse)
async def recommend(
    repo: str = Query(..., description="Source repo as owner/name"),
    limit: int = Query(10, ge=1, le=50),
) -> RecommendResponse:
    if "/" not in repo:
        raise HTTPException(
            status_code=400,
            detail="repo must be in 'owner/name' format",
        )
    return _stub_recommend(repo, limit)


def _stub_recommend(source: str, limit: int) -> RecommendResponse:
    return RecommendResponse(
        source_repo=source,
        slots=[
            Slot(
                name="alternatives",
                repos=[],
            ),
            Slot(name="addons", repos=[]),
            Slot(name="companions", repos=[]),
            Slot(name="starters", repos=[]),
            Slot(name="trending", repos=[]),
            Slot(name="maintainer_wanted", repos=[]),
        ],
    )
