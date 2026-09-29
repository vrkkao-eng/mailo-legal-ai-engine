import sqlite3

from mailo_cli.regulatory.persistence import SQLiteWorkflowRepository


def test_repository_migrates_v051_workflow_run_schema(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE workflow_runs (
            run_id TEXT PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE,
            request_sha256 TEXT NOT NULL,
            change_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            request_json TEXT NOT NULL,
            result_json TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()

    SQLiteWorkflowRepository(path)

    connection = sqlite3.connect(path)
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(workflow_runs)").fetchall()
    }
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    connection.close()

    assert {"failed_step", "error_code", "retryable", "error_detail"}.issubset(columns)
    assert "workflow_steps" in tables
