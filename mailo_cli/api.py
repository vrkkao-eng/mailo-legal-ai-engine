"""Thin HTTP adapter for selected offline MAILO engine workflows."""

import asyncio
import json
import logging
import os
import time
import uuid
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from mailo_cli.pipeline import export_findings
from mailo_cli.services import execute_packaged_query
from mailo_cli.shape_registry import ShapeRegistry
from mailo_cli.settings import load_api_settings
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
    """A system description checked against an operator-registered shape profile."""

    system: dict[str, Any]
    shapes: str = Field(default="demo", pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")


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
    shapes_profile: str
    shapes_sha256: str
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
_SHAPE_REGISTRY = ShapeRegistry(_RESOURCE_DIR, os.getenv("MAILO_SHAPES_MANIFEST"))
_SETTINGS = load_api_settings()
_LOGGER = logging.getLogger("mailo.api")

if _SETTINGS.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_SETTINGS.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )


@app.middleware("http")
async def harden_http(request: Request, call_next):
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > _SETTINGS.max_request_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "Request body exceeds configured size limit"},
                )
            else:
                response = await asyncio.wait_for(
                    call_next(request), timeout=_SETTINGS.request_timeout_seconds
                )
        except ValueError:
            response = JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
        except TimeoutError:
            response = JSONResponse(status_code=504, content={"detail": "Request timed out"})
    else:
        try:
            response = await asyncio.wait_for(
                call_next(request), timeout=_SETTINGS.request_timeout_seconds
            )
        except TimeoutError:
            response = JSONResponse(status_code=504, content={"detail": "Request timed out"})
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    _LOGGER.info(json.dumps({
        "event": "http_request",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }))
    return response


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
    try:
        _SHAPE_REGISTRY.ready()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
        profile = _SHAPE_REGISTRY.get(request.shapes)
        conforms, results_graph, _ = run_shacl(turtle, profile.path)
        return ValidateResponse(
            system=request.system["system_id"],
            conforms=bool(conforms),
            results=parse_violations(results_graph),
            shapes_profile=profile.name,
            shapes_sha256=profile.sha256,
            scope=profile.scope,
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
