"""Adapted JSON -> RDF -> SHACL flow from DH_THESIS validate_cmd.py.
Uses RDFLib terms instead of interpolated Turtle, and retains every SHACL result.
Legal interpretations and private report metadata are not embedded here.
"""

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from pyshacl import validate as shacl_validate

MAILO = Namespace("https://w3id.org/mailo#")
INST = Namespace("urn:mailo:instance:")
SH = Namespace("http://www.w3.org/ns/shacl#")
BOOL_FIELDS = {
    "produces_significant_impact": "producesSignificantImpact",
    "individual_non_automated_review": "hasIndividualNonAutomatedReview",
    "has_predetermined_criteria": "hasPredeterminedCriteria",
    "uses_health_status_as_criterion": "usesHealthStatusAsCriterion",
    "has_defined_scope": "hasDefinedScope",
    "has_purpose_limitation": "hasPurposeLimitation",
    "has_temporal_limitation": "hasTemporalLimitation",
    "is_high_risk_ai_act": "isHighRiskAIAct",
}
TEXT_FIELDS = {
    "developer": "hasDeveloper",
    "intended_purpose": "hasIntendedPurpose",
    "art22_exception": "art22ExceptionApplied",
}


def _term(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError("Class and mdr_class values must be local vocabulary names")
    return MAILO[value]


def _boolean(value):
    if type(value) is not bool:
        raise ValueError("Boolean fields require JSON true or false")
    return Literal(value, datatype=XSD.boolean)


def build_turtle(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValueError("System description must be an object")
    allowed = (
        {
            "system_id",
            "classes",
            "label",
            "mdr_class",
            "oversight",
            "explanation",
            "dpia",
        }
        | BOOL_FIELDS.keys()
        | TEXT_FIELDS.keys()
    )
    if set(data) - allowed:
        raise ValueError(
            "Unknown system fields: " + ", ".join(sorted(set(data) - allowed))
        )
    sid = data.get("system_id")
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError("system_id is required")
    subject = URIRef(str(INST) + quote(sid, safe=""))
    g = Graph()
    g.bind("mailo", MAILO)
    classes = data.get("classes", ["MedicalAISystem", "AutomatedDecisionSystem"])
    if not isinstance(classes, list) or not classes:
        raise ValueError("classes must be a nonempty array")
    for cls in classes:
        g.add((subject, RDF.type, _term(cls)))
    for field, prop in TEXT_FIELDS.items():
        if field in data:
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
            g.add((subject, MAILO[prop], Literal(data[field], datatype=XSD.string)))
    if "label" in data:
        if not isinstance(data["label"], str):
            raise ValueError("label must be a string")
        g.add((subject, RDFS.label, Literal(data["label"], datatype=XSD.string)))
    if "mdr_class" in data:
        g.add((subject, MAILO.classifiedUnder, _term(data["mdr_class"])))
    for field, prop in BOOL_FIELDS.items():
        if field in data:
            g.add((subject, MAILO[prop], _boolean(data[field])))
    linked = [
        (
            "oversight",
            "hasHumanOversightRecord",
            "HumanOversightRecord",
            {"is_substantive": "oversightIsSubstantive"},
        ),
        (
            "explanation",
            "hasExplanation",
            "Explanation",
            {
                "actionable": "isActionable",
                "non_technical": "isNonTechnical",
                "identifies_input_factors": "identifiesInputFactors",
            },
        ),
    ]
    for field, prop, cls, mapping in linked:
        if field not in data:
            continue
        obj = data[field]
        if not isinstance(obj, dict) or set(obj) - mapping.keys():
            raise ValueError(f"Invalid {field} object")
        node = URIRef(str(subject) + ":" + field)
        g.add((subject, MAILO[prop], node))
        g.add((node, RDF.type, MAILO[cls]))
        for key, predicate in mapping.items():
            if key in obj:
                g.add((node, MAILO[predicate], _boolean(obj[key])))
    if "dpia" in data:
        _boolean(data["dpia"])
        if data["dpia"]:
            node = URIRef(str(subject) + ":dpia")
            g.add((subject, MAILO.hasDPIA, node))
            g.add((node, RDF.type, MAILO.DPIARecord))
    return g.serialize(format="turtle")


def run_shacl(turtle_data: str, shapes_path: Path):
    shapes = Graph().parse(
        data=shapes_path.read_text(encoding="utf-8"), format="turtle"
    )
    if not any(shapes.subjects(RDF.type, SH.NodeShape)) and not any(
        shapes.subjects(RDF.type, SH.PropertyShape)
    ):
        raise ValueError("Shapes file contains no declared SHACL shapes")
    return shacl_validate(
        data_graph=turtle_data,
        shacl_graph=shapes,
        data_graph_format="turtle",
        inference="none",
        abort_on_first=False,
        meta_shacl=True,
        advanced=False,
        js=False,
        do_owl_imports=False,
    )


def parse_violations(results_graph):
    """Keep all results, including anonymous property shapes and all severities."""
    if not isinstance(results_graph, Graph):
        raise ValueError(f"SHACL validation failure: {results_graph}")
    results = []
    for result in results_graph.subjects(RDF.type, SH.ValidationResult):
        item = {}
        for key, predicate in {
            "severity": SH.resultSeverity,
            "shape": SH.sourceShape,
            "focus": SH.focusNode,
            "path": SH.resultPath,
            "value": SH.value,
            "constraint": SH.sourceConstraintComponent,
        }.items():
            value = results_graph.value(result, predicate)
            item[key] = "" if value is None else str(value)
        item["messages"] = sorted(
            str(m) for m in results_graph.objects(result, SH.resultMessage)
        )
        results.append(item)
    return sorted(
        results,
        key=lambda v: (v["focus"], v["path"], v["severity"], str(v["messages"])),
    )


def run_validate(instance_path: Path, shapes_path: Path, output_dir: Path):
    raw = json.loads(instance_path.read_text(encoding="utf-8"))
    turtle = build_turtle(raw)
    conforms, graph, _ = run_shacl(turtle, shapes_path)
    results = parse_violations(graph)
    report = {
        "system": raw["system_id"],
        "conforms": bool(conforms),
        "results": results,
        "shapes_sha256": hashlib.sha256(shapes_path.read_bytes()).hexdigest(),
        "instance_sha256": hashlib.sha256(instance_path.read_bytes()).hexdigest(),
        "scope": "Conformance to supplied shapes; not a legal compliance determination",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "instance.ttl").write_text(turtle, encoding="utf-8")
    graph.serialize(
        destination=str(output_dir / "validation-report.ttl"), format="turtle"
    )
    (output_dir / "validation-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (output_dir / "validation-report.md").write_text(
        "# SHACL validation\n\nConforms: "
        + str(bool(conforms))
        + "\n\n"
        + report["scope"]
        + "\n\n"
        + "\n".join("- " + json.dumps(item, ensure_ascii=False) for item in results),
        encoding="utf-8",
    )
    return report
