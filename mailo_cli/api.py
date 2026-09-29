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

from fastapi import FastAPI, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from mailo_cli import __version__
from mailo_cli.pipeline import export_findings
from mailo_cli.services import execute_packaged_query
from mailo_cli.shape_registry import ShapeRegistry
from mailo_cli.settings import load_api_settings
from mailo_cli.validate_cmd import build_turtle, parse_violations, run_shacl
from mailo_cli.regulatory.execution import WorkflowExecutionError, execute_durable_workflow
from mailo_cli.regulatory.persistence import (
    IdempotencyConflict,
    SQLiteWorkflowRepository,
    WorkflowRunNotFound,
)
from mailo_cli.regulatory.service import evaluate_workflow
from mailo_cli.regulatory.workflow_demo import run_fixed_workflow_scenario
from mailo_cli.workflow_api import (
    AuditEventResponse,
    HumanResponsePersistRequest,
    HumanResponsePersistResponse,
    PersistedReviewCaseResponse,
    WorkflowEvaluateRequest,
    WorkflowEvaluateResponse,
    WorkflowRunResponse,
    WorkflowStepResponse,
    to_domain_request,
)


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
    version=__version__,
    description="Offline graph, reviewed-query, SHACL, and stateless RegAI workflow services.",
)
_RESOURCE_DIR = Path(str(files("mailo_cli").joinpath("resources")))
_SHAPE_REGISTRY = ShapeRegistry(_RESOURCE_DIR, os.getenv("MAILO_SHAPES_MANIFEST"))
_SETTINGS = load_api_settings()
_LOGGER = logging.getLogger("mailo.api")
if not _LOGGER.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _LOGGER.addHandler(_handler)
_LOGGER.setLevel(logging.INFO)
_LOGGER.propagate = False
_WORKFLOW_REPOSITORY: SQLiteWorkflowRepository | None = None


def _get_workflow_repository() -> SQLiteWorkflowRepository:
    global _WORKFLOW_REPOSITORY
    if _WORKFLOW_REPOSITORY is None:
        database_path = os.getenv("MAILO_WORKFLOW_DB", "artifacts/workflow.db")
        _WORKFLOW_REPOSITORY = SQLiteWorkflowRepository(database_path)
    return _WORKFLOW_REPOSITORY


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
    except WorkflowExecutionError as exc:
        status_code = 503 if exc.retryable else 400
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": exc.detail,
                "workflow_run_id": exc.run_id,
                "failed_step": exc.failed_step.value,
                "error_code": exc.error_code.value,
                "retryable": exc.retryable,
            },
        ) from exc
    except WorkflowRunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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


@app.post("/workflow/evaluate", response_model=WorkflowEvaluateResponse)
def workflow_evaluate(request: WorkflowEvaluateRequest) -> WorkflowEvaluateResponse:
    """Evaluate one supplied reviewed change against organisation workflow data.

    The endpoint is stateless: it returns evidence-gap, regulatory-impact, and
    focused review-routing outputs without persisting review cases or producing
    a legal-compliance determination.
    """

    def run() -> WorkflowEvaluateResponse:
        change, obligations, mappings, controls, evidence = to_domain_request(request)
        result = evaluate_workflow(
            change,
            obligations=obligations,
            mappings=mappings,
            controls=controls,
            evidence=evidence,
        )
        return WorkflowEvaluateResponse.from_domain(result)

    return _bad_request(run)


@app.get("/workflow/demo")
def workflow_demo() -> dict[str, object]:
    """Run the deterministic offline FRIA workflow scenario."""

    return _bad_request(lambda: run_fixed_workflow_scenario().to_dict())


@app.post("/workflow/runs", response_model=WorkflowRunResponse)
def create_workflow_run(
    request: WorkflowEvaluateRequest,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
) -> WorkflowRunResponse:
    """Evaluate and atomically persist one durable workflow run."""

    def run() -> WorkflowRunResponse:
        change, obligations, mappings, controls, evidence = to_domain_request(request)
        repository = _get_workflow_repository()
        persisted, created = execute_durable_workflow(
            repository=repository,
            idempotency_key=idempotency_key,
            request_payload=request.model_dump(mode="json"),
            change=change,
            obligations=obligations,
            mappings=mappings,
            controls=controls,
            evidence=evidence,
        )
        response.status_code = 201 if created else 200
        return WorkflowRunResponse(
            run_id=persisted.run_id,
            idempotency_key=persisted.idempotency_key,
            request_sha256=persisted.request_sha256,
            change_id=persisted.change_id,
            status=persisted.status,
            created_at=persisted.created_at.isoformat(),
            created=created,
            failed_step=persisted.failed_step,
            error_code=persisted.error_code,
            retryable=persisted.retryable,
            error_detail=persisted.error_detail,
            result=persisted.result_payload,
            steps=[
                WorkflowStepResponse.model_validate(item)
                for item in repository.list_steps(persisted.run_id)
            ],
            review_cases=[
                PersistedReviewCaseResponse.model_validate(item)
                for item in repository.list_review_cases(persisted.run_id)
            ],
            audit_events=[
                AuditEventResponse.model_validate(item)
                for item in repository.list_audit_events(persisted.run_id)
            ],
        )

    return _bad_request(run)


@app.get("/workflow/runs/{run_id}", response_model=WorkflowRunResponse)
def get_workflow_run(run_id: str) -> WorkflowRunResponse:
    """Retrieve one durable workflow run and its review/audit snapshot."""

    def run() -> WorkflowRunResponse:
        repository = _get_workflow_repository()
        persisted = repository.get_run(run_id)
        return WorkflowRunResponse(
            run_id=persisted.run_id,
            idempotency_key=persisted.idempotency_key,
            request_sha256=persisted.request_sha256,
            change_id=persisted.change_id,
            status=persisted.status,
            created_at=persisted.created_at.isoformat(),
            created=False,
            failed_step=persisted.failed_step,
            error_code=persisted.error_code,
            retryable=persisted.retryable,
            error_detail=persisted.error_detail,
            result=persisted.result_payload,
            steps=[
                WorkflowStepResponse.model_validate(item)
                for item in repository.list_steps(persisted.run_id)
            ],
            review_cases=[
                PersistedReviewCaseResponse.model_validate(item)
                for item in repository.list_review_cases(persisted.run_id)
            ],
            audit_events=[
                AuditEventResponse.model_validate(item)
                for item in repository.list_audit_events(persisted.run_id)
            ],
        )

    return _bad_request(run)


@app.post(
    "/workflow/reviews/{review_id}/responses",
    response_model=HumanResponsePersistResponse,
)
def persist_human_response(
    review_id: str,
    request: HumanResponsePersistRequest,
) -> HumanResponsePersistResponse:
    """Persist a focused human response and terminal review transition."""

    def run() -> HumanResponsePersistResponse:
        repository = _get_workflow_repository()
        review_case = repository.record_response(
            review_id=review_id,
            response_id=request.response_id,
            answer=request.answer,
            reviewer_role=request.reviewer_role,
            rationale=request.rationale,
            responded_at=request.responded_at,
            escalation_target=request.escalation_target,
        )
        audit_events = [
            item
            for item in repository.list_audit_events(review_case["run_id"])
            if item["review_id"] == review_id
        ]
        return HumanResponsePersistResponse(
            review_case=PersistedReviewCaseResponse.model_validate(review_case),
            audit_events=[
                AuditEventResponse.model_validate(item) for item in audit_events
            ],
        )

    return _bad_request(run)
