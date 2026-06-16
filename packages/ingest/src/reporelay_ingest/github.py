from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from reporelay_core.settings import get_settings

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubRateLimitError(Exception):
    pass


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        settings = get_settings()
        self._token = token or settings.github_token
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers=self._auth_headers(),
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    def _auth_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoRelay/0.1",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(GitHubRateLimitError),
        wait=wait_exponential(multiplier=2, min=30, max=600),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        response = await self._client.get(path, params=params)
        if response.status_code == 403 and self._is_rate_limited(response):
            reset = response.headers.get("X-RateLimit-Reset", "0")
            logger.warning("Rate limited; reset at %s", reset)
            raise GitHubRateLimitError(f"rate limit hit, reset={reset}")
        response.raise_for_status()
        return cast("dict[str, Any]", response.json())

    @staticmethod
    def _is_rate_limited(response: httpx.Response) -> bool:
        remaining: str | None = response.headers.get("X-RateLimit-Remaining")
        return remaining == "0"

    async def get_repo(self, owner: str, name: str) -> dict[str, Any]:
        return await self.get(f"/repos/{owner}/{name}")

    async def get_readme(self, owner: str, name: str) -> str:
        data = await self.get(f"/repos/{owner}/{name}/readme")
        import base64

        content = data.get("content", "")
        if not content:
            return ""
        padding = "=" * (-len(content) % 4)
        return base64.b64decode(content + padding).decode("utf-8", errors="replace")


def _demo() -> None:
    from rich.console import Console

    console = Console()

    async def run() -> None:
        async with GitHubClient() as client:
            try:
                repo = await client.get_repo("anthropics", "anthropic-sdk-python")
            except httpx.HTTPError as exc:
                console.print(f"[red]request failed:[/red] {exc}")
                return
            console.print(
                f"[green]{repo['full_name']}[/green] - {repo['stargazers_count']} stars - {repo['description']}"
            )

    asyncio.run(run())


if __name__ == "__main__":
    _demo()
