from __future__ import annotations

import asyncio
import logging

import httpx
import typer
from rich.console import Console
from rich.logging import RichHandler

from reporelay_core.settings import get_settings
from reporelay_ingest.github import GitHubClient

app = typer.Typer(help="RepoRelay data ingestion CLI")
console = Console()


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


@app.command()
def fetch_repo(
    owner: str = typer.Argument(..., help="Repo owner"),
    name: str = typer.Argument(..., help="Repo name"),
) -> None:
    """Fetch a single repo's metadata and print it."""
    _configure_logging()

    async def run() -> None:
        async with GitHubClient() as client:
            try:
                repo = await client.get_repo(owner, name)
            except httpx.HTTPError as exc:
                console.print(f"[red]failed:[/red] {exc}")
                raise typer.Exit(code=1) from exc
            console.print(
                f"[green]{repo['full_name']}[/green] - "
                f"{repo['stargazers_count']} stars - "
                f"{repo.get('language', '?')} - "
                f"{repo.get('description') or '(no description)'}"
            )

    asyncio.run(run())


@app.command()
def whoami() -> None:
    """Check the GitHub auth state and remaining rate limit."""
    _configure_logging()

    async def run() -> None:
        async with GitHubClient() as client:
            response = await client._client.get("/rate_limit")
            data = response.json()
            core = data.get("resources", {}).get("core", {})
            console.print(
                f"[bold]limit:[/bold] {core.get('limit')} - "
                f"[bold]used:[/bold] {core.get('used')} - "
                f"[bold]remaining:[/bold] {core.get('remaining')}"
            )

    asyncio.run(run())


if __name__ == "__main__":
    app()
