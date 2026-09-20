"""Thin HTTP adapter for selected offline MAILO engine workflows."""

import json
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from mailo_cli.pipeline import export_findings
from mailo_cli.services import execute_packaged_query
from mailo_cli.validate_cmd import build_turtle, parse_violations, run_shacl


class Finding(BaseModel):
    """A source-linked research finding accepted by the graph endpoint."""

    model_config = ConfigDict(extra="forbid")
    category: Literal[
        "case_law", "legal_principle", "literature", "patent",
        "compliance_risk", "obligation", "technology",
    ]
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_url: HttpUrl
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphRequest(BaseModel):
    findings: list[Finding] = Field(min_length=1)


class GraphResponse(BaseModel):
    findings: int
    triples: int
    jsonld: dict[str, Any]
    turtle: str


class ValidateRequest(BaseModel):
    """A system description checked only against a reviewed packaged demo shape."""

    system: dict[str, Any]
    shapes: Literal["demo"] = "demo"


class ValidationResult(BaseModel):
    severity: str
    shape: str
    focus: str
    path: str
    value: str
    constraint: str
    messages: list[str]


class ValidateResponse(BaseModel):
    system: str
    conforms: bool
    results: list[ValidationResult]
    scope: str


class SparqlRequest(BaseModel):
    ontology_turtle: str = Field(min_length=1)
    built_in: Literal[
        "cjeu_chain", "frameworks", "fto_patent", "obligations_samd", "tensions"
    ]


class SparqlResponse(BaseModel):
    rows: list[dict[str, str | None]]


app = FastAPI(
    title="MAILO Legal AI Engine",
    version="0.1.0",
    description="Offline graph, reviewed-query, and SHACL-conformance workflows.",
)
_RESOURCE_DIR = Path(str(files("mailo_cli").joinpath("resources")))


def _bad_request(operation):
    try:
        return operation()
    except (ValueError, TypeError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal processing error") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Report whether packaged runtime resources needed by the API are present."""
    if not (_RESOURCE_DIR / "demo-shapes.ttl").is_file():
        raise HTTPException(status_code=503, detail="Packaged validation shapes unavailable")
    return {"status": "ready"}


@app.post("/graph", response_model=GraphResponse)
def graph(request: GraphRequest) -> GraphResponse:
    def export() -> GraphResponse:
        with TemporaryDirectory() as directory:
            output = Path(directory)
            findings = [item.model_dump(mode="json") for item in request.findings]
            stats = export_findings(findings, output)
            return GraphResponse(
                **stats,
                jsonld=json.loads(
                    (output / "medical_ai_knowledge_graph.jsonld").read_text("utf-8")
                ),
                turtle=(output / "findings.ttl").read_text("utf-8"),
            )

    return _bad_request(export)


@app.post("/validate", response_model=ValidateResponse)
def validate(request: ValidateRequest) -> ValidateResponse:
    def run() -> ValidateResponse:
        turtle = build_turtle(request.system)
        conforms, results_graph, _ = run_shacl(turtle, _RESOURCE_DIR / "demo-shapes.ttl")
        return ValidateResponse(
            system=request.system["system_id"],
            conforms=bool(conforms),
            results=parse_violations(results_graph),
            scope="Conformance to packaged synthetic demo shapes; not a legal compliance determination",
        )

    return _bad_request(run)


@app.post("/sparql", response_model=SparqlResponse)
def sparql(request: SparqlRequest) -> SparqlResponse:
    return _bad_request(
        lambda: SparqlResponse(
            rows=execute_packaged_query(
                request.ontology_turtle,
                _RESOURCE_DIR / "queries" / f"{request.built_in}.sparql",
            )
        )
    )
