"""Public CLI adapted from DH_THESIS command boundaries."""

import asyncio
import json
import os
from importlib.resources import files
from pathlib import Path
import click
from mailo_cli import __version__
from mailo_cli.pipeline import export_findings, read_json, validate_findings
from mailo_cli.services import execute_packaged_query
from mailo_cli.validate_cmd import run_validate

RESOURCE_DIR = Path(str(files("mailo_cli").joinpath("resources")))
QUERIES = ("cjeu_chain", "frameworks", "fto_patent", "obligations_samd", "tensions")


def guarded(function, *args):
    try:
        return function(*args)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc


@click.group()
@click.version_option(__version__)
def main():
    """Python research pipeline, knowledge engineering and SHACL validation."""


@main.command()
@click.option("--output", type=click.Path(path_type=Path), default="artifacts/demo")
def demo(output):
    """Run the bundled synthetic example offline, without API keys."""
    stats = guarded(export_findings, read_json(RESOURCE_DIR / "findings.json"), output)
    report = guarded(
        run_validate,
        RESOURCE_DIR / "system.json",
        RESOURCE_DIR / "demo-shapes.ttl",
        output,
    )
    click.echo(
        json.dumps({**stats, "conforms": report["conforms"], "output": str(output)})
    )
    if not report["conforms"]:
        raise click.exceptions.Exit(1)


@main.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--output", required=True, type=click.Path(path_type=Path))
def graph(input_path, output):
    """Export supplied findings to JSON-LD and Turtle."""
    findings = guarded(read_json, input_path)
    click.echo(json.dumps(guarded(export_findings, findings, output)))


@main.command()
@click.option(
    "--instance",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--shapes",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--output", default="artifacts/validation", type=click.Path(path_type=Path)
)
def validate(instance, shapes, output):
    """Validate a system JSON against explicit local SHACL shapes."""
    report = guarded(run_validate, instance, shapes, output)
    click.echo(json.dumps(report))
    if not report["conforms"]:
        raise click.exceptions.Exit(1)


@main.command()
@click.option(
    "--ontology",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--built-in", type=click.Choice(QUERIES), required=True)
def sparql(ontology, built_in):
    """Run a reviewed SELECT query; emits full RDF term strings as JSON."""

    def execute():
        return execute_packaged_query(
            ontology.read_text(encoding="utf-8"),
            RESOURCE_DIR / "queries" / (built_in + ".sparql"),
        )

    click.echo(json.dumps(guarded(execute), ensure_ascii=False, indent=2))


@main.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--model", envvar="MAILO_MODEL", required=True)
@click.option("--output", required=True, type=click.Path(path_type=Path))
def research(input_path, model, output):
    """LIVE: send supplied findings/text to Anthropic; may incur API charges."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise click.ClickException("Set ANTHROPIC_API_KEY for live research")
    try:
        from mailo_cli.agents.base_agent import BaseAgent
    except ImportError as exc:
        raise click.ClickException(
            "Install the research extra: pip install '.[research]'"
        ) from exc
    sources = guarded(read_json, input_path)
    guarded(validate_findings, sources)
    agent = BaseAgent(api_key=key, output_dir=output, model=model)
    agent.allowed_sources = {item["source_url"] for item in sources}
    try:
        asyncio.run(agent.run_agent(json.dumps(sources, ensure_ascii=False)))
        guarded(validate_findings, agent.collected_data)
        agent.save_collected_data()
        stats = guarded(export_findings, agent.collected_data, output)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(
            f"Research did not complete ({type(exc).__name__}); no successful run claimed"
        ) from exc
    click.echo(json.dumps(stats))


if __name__ == "__main__":
    main()
