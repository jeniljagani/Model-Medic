"""
modelmedic CLI entry point.

Usage
-----
    modelmedic --help
    modelmedic version
    modelmedic ping
    modelmedic diagnose <task_id>
    modelmedic diagnose <task_id> --output json
"""
from __future__ import annotations

import json
import sys

import click


@click.group()
@click.version_option(package_name="modelmedic", prog_name="modelmedic")
def main():
    """
    ModelMedic — Intelligent ML diagnosis built on ClearML.

    Analyzes your ClearML experiments and tells you:
    what's wrong, why, and what to do next.
    """
    pass


@main.command()
def ping():
    """Test connection to the ClearML server."""
    from modelmedic.integration import ClearMLClient
    client = ClearMLClient()
    click.echo("Pinging ClearML server...", nl=False)
    if client.ping():
        click.echo(click.style("  OK", fg="green", bold=True))
    else:
        click.echo(click.style("  FAILED", fg="red", bold=True))
        click.echo("Check your ClearML credentials in ~/clearml.conf")
        sys.exit(1)


@main.command()
@click.argument("task_id")
@click.option(
    "--output",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format (default: text)",
)
def diagnose(task_id: str, output: str):
    """
    Diagnose a ClearML experiment.

    TASK_ID is the ClearML task/experiment ID to diagnose.
    Find it in the ClearML Web UI URL or via Task.id.

    Example:

        modelmedic diagnose fd8762fbf666486dae12d43d9488de5a
    """
    from modelmedic.integration import ExperimentFetcher
    from modelmedic.diagnosis import DiagnosisEngine

    click.echo(f"Fetching experiment {task_id}...", nl=False)
    try:
        fetcher = ExperimentFetcher()
        experiment = fetcher.fetch(task_id)
        click.echo(click.style("  OK", fg="green"))
    except Exception as exc:
        click.echo(click.style(f"  FAILED: {exc}", fg="red"))
        sys.exit(1)

    click.echo(f"Running diagnosis for '{experiment.task_name}'...", nl=False)
    try:
        engine = DiagnosisEngine()
        report = engine.run(experiment)
        click.echo(click.style("  DONE", fg="green"))
    except Exception as exc:
        click.echo(click.style(f"  FAILED: {exc}", fg="red"))
        sys.exit(1)

    # Output
    if output == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        # Color-code the health status
        health_color = {
            "healthy": "green",
            "warning": "yellow",
            "critical": "red",
        }.get(report.overall_health, "white")

        click.echo()
        for line in report.summary().splitlines():
            if "CRITICAL" in line or "[SEVERE]" in line:
                click.echo(click.style(line, fg="red", bold=True))
            elif "WARNING" in line or "[MODERATE]" in line:
                click.echo(click.style(line, fg="yellow"))
            elif "[MILD]" in line:
                click.echo(click.style(line, fg="cyan"))
            elif "Health" in line:
                click.echo(
                    click.style(line, fg=health_color, bold=True)
                )
            else:
                click.echo(line)


@main.command(name="analyze-dataset")
@click.argument("dataset_source")
@click.option(
    "--output",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format (default: text)",
)
@click.option(
    "--target",
    type=str,
    default=None,
    help="Target column name for classification/regression analysis",
)
def analyze_dataset(dataset_source: str, output: str, target: str):
    """
    Analyze a dataset for quality issues.

    DATASET_SOURCE can be a ClearML dataset ID or a local file path (e.g. data.csv).
    """
    from modelmedic.integration import DatasetFetcher
    from modelmedic.dataset_intelligence import DatasetAnalyzer, load_dataset
    from pathlib import Path

    local_file = None
    
    if Path(dataset_source).is_file():
        # Treat as local file
        click.echo(f"Using local dataset file: {dataset_source}")
        local_file = Path(dataset_source)
    else:
        # Treat as ClearML ID
        click.echo(f"Fetching ClearML dataset {dataset_source}...", nl=False)
        try:
            fetcher = DatasetFetcher()
            local_file = fetcher.resolve_dataset_file(dataset_id=dataset_source)
            click.echo(click.style("  OK", fg="green"))
        except Exception as exc:
            click.echo(click.style(f"  FAILED: {exc}", fg="red"))
            sys.exit(1)

    click.echo(f"Loading dataset into memory...", nl=False)
    try:
        df = load_dataset(local_file)
        click.echo(click.style("  OK", fg="green"))
    except Exception as exc:
        click.echo(click.style(f"  FAILED: {exc}", fg="red"))
        sys.exit(1)

    click.echo(f"Running advanced dataset analysis...", nl=False)
    try:
        analyzer = DatasetAnalyzer()
        report = analyzer.analyze(df, target_column=target)
        click.echo(click.style("  DONE", fg="green"))
    except Exception as exc:
        click.echo(click.style(f"  FAILED: {exc}", fg="red"))
        sys.exit(1)

    if output == "json":
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        health = report.health_score.score
        health_color = "green" if health >= 80 else ("yellow" if health >= 50 else "red")
        
        click.echo()
        for line in report.get_report_summary().splitlines():
            if "CRITICAL" in line or "!" in line:
                click.echo(click.style(line, fg="red", bold=True))
            elif "WARNING" in line or "-" in line:
                click.echo(click.style(line, fg="yellow"))
            elif "Health Score" in line:
                click.echo(click.style(line, fg=health_color, bold=True))
            else:
                click.echo(line)


@main.command(name="version")
def show_version():
    """Show ModelMedic version."""
    from modelmedic import __version__
    click.echo(f"ModelMedic v{__version__}")


if __name__ == "__main__":
    main()
