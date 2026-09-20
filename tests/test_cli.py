import json
from click.testing import CliRunner
from mailo_cli.cli import main, RESOURCE_DIR, QUERIES


def test_demo_offline(tmp_path):
    result = CliRunner().invoke(main, ["demo", "--output", str(tmp_path)])
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "validation-report.json").read_text())
    assert report["conforms"] is True
    assert len(report["shapes_sha256"]) == 64
    assert (tmp_path / "findings.ttl").exists()


def test_invalid_instance_nonzero_and_report_keeps_anonymous_shape(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(
        json.dumps(
            {
                "system_id": "test",
                "classes": ["MedicalAISystem"],
                "individual_non_automated_review": False,
            }
        )
    )
    result = CliRunner().invoke(
        main,
        [
            "validate",
            "--instance",
            str(path),
            "--shapes",
            str(RESOURCE_DIR / "demo-shapes.ttl"),
            "--output",
            str(tmp_path / "report"),
        ],
    )
    assert result.exit_code == 1, result.output
    report = json.loads((tmp_path / "report/validation-report.json").read_text())
    assert report["conforms"] is False
    assert report["results"][0]["path"].endswith("hasIndividualNonAutomatedReview")


def test_missing_file_nonzero():
    result = CliRunner().invoke(
        main, ["graph", "--input", "nonexistent.json", "--output", "unused"]
    )
    assert result.exit_code == 2


def test_all_packaged_queries_execute(tmp_path):
    ontology = tmp_path / "tiny.ttl"
    ontology.write_text(
        '@prefix m: <https://w3id.org/mailo#> .\n@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\nm:Demo a m:EURegulation; rdfs:label "Synthetic"@en .'
    )
    for name in QUERIES:
        result = CliRunner().invoke(
            main, ["sparql", "--ontology", str(ontology), "--built-in", name]
        )
        assert result.exit_code == 0, result.output
        rows = json.loads(result.output)
        if name == "frameworks":
            assert rows[0]["framework"] == "https://w3id.org/mailo#Demo"
            assert rows[0]["articles"] == "0"


def test_live_research_requires_key(tmp_path):
    result = CliRunner().invoke(
        main,
        [
            "research",
            "--input",
            str(RESOURCE_DIR / "findings.json"),
            "--model",
            "mock-model",
            "--output",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output
