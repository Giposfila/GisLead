"""`leadgis` command-line entry point (typer)."""

from __future__ import annotations

import asyncio

import typer

from leadgis.config import CONFIG_PATH, DB_PATH, ensure_config_file

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def start() -> None:
    """Run migrations and start the LeadGis server, opening the UI in a browser."""
    ensure_config_file()
    typer.echo(f"Config: {CONFIG_PATH}")
    typer.echo(f"Database: {DB_PATH}")

    from leadgis.main import run

    run()


@app.command()
def export(
    campaign_id: int = typer.Argument(..., help="Campaign id to export"),
    fmt: str = typer.Option("csv", "--format", help="csv or xlsx"),
    output: str = typer.Option(None, "--output", help="Output file path"),
) -> None:
    """Export a campaign's leads to CSV/XLSX without starting the server."""
    from leadgis.services.export import CampaignNotFoundError, export_campaign

    try:
        path = asyncio.run(export_campaign(campaign_id, fmt, output))
    except CampaignNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Exported to {path}")


@app.command()
def reset(yes: bool = typer.Option(False, "--yes", help="Skip confirmation")) -> None:
    """Delete the local database (config is kept)."""
    if not yes:
        typer.confirm(f"Delete {DB_PATH}?", abort=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    typer.echo("Database deleted.")


if __name__ == "__main__":
    app()
