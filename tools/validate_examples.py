"""Smoke-test installed package resources without source-tree path injection."""

from tempfile import TemporaryDirectory
from pathlib import Path
from mailo_cli.cli import RESOURCE_DIR
from mailo_cli.pipeline import read_json, export_findings
from mailo_cli.validate_cmd import run_validate


def main():
    with TemporaryDirectory() as directory:
        out = Path(directory)
        stats = export_findings(read_json(RESOURCE_DIR / "findings.json"), out)
        report = run_validate(
            RESOURCE_DIR / "system.json", RESOURCE_DIR / "demo-shapes.ttl", out
        )
        assert stats["findings"] == 1 and report["conforms"]
        print("Synthetic examples passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
