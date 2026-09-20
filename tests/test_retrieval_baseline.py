"""Offline checks for the provisional retrieval-evaluation tooling."""

from __future__ import annotations

import json
from hashlib import sha256

from pypdf import PdfWriter
import pytest

from tools.retrieval_baseline import DEFAULT_SEED, evaluate, load_seed, prepare, score


def test_checked_in_candidate_seed_has_valid_references():
    seed = load_seed(DEFAULT_SEED)
    assert len(seed["sources"]) == 7
    assert len(seed["queries"]) == 15
    assert sum(not query["support_expected"] for query in seed["queries"]) == 2


def test_seed_rejects_non_official_download_url(tmp_path):
    seed = load_seed(DEFAULT_SEED)
    seed["sources"][0]["pdf_url"] = "https://example.com/not-an-official-source.pdf"
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(seed), encoding="utf-8")
    with pytest.raises(ValueError, match="Non-allowlisted"):
        load_seed(path)


def test_source_level_scoring_excludes_unsupported_questions():
    seed = {
        "sources": [{"id": "device"}, {"id": "privacy"}],
        "queries": [
            {
                "id": "Q1",
                "question": "diagnostic medical device software",
                "support_expected": True,
                "targets": [{"source_id": "device", "locator": "Rule 11"}],
            },
            {
                "id": "Q2",
                "question": "Is an unknown device compliant?",
                "support_expected": False,
                "targets": [],
            },
        ],
    }
    pages = [
        {"page_id": "device:p0001", "source_id": "device", "pdf_page": 1, "text": "diagnostic medical device software"},
        {"page_id": "privacy:p0001", "source_id": "privacy", "pdf_page": 1, "text": "credit scoring and privacy"},
    ]
    report = evaluate(seed, pages)
    assert report["status"] == "exploratory_unadjudicated"
    assert report["positive_query_count"] == 1
    assert report["excluded_negative_query_ids"] == ["Q2"]
    assert report["metrics"]["macro_source_recall_at_1"] == 1
    assert report["queries"][0]["ranked_sources"][0]["source_id"] == "device"


def test_offline_prepare_records_pdf_hash_and_rejects_tampering(tmp_path):
    seed = {
        "status": "candidate_unadjudicated",
        "sources": [
            {
                "id": "test_source",
                "version": "test snapshot",
                "url": "https://eur-lex.europa.eu/test",
                "pdf_url": "https://eur-lex.europa.eu/test.pdf",
                "pdf_sha256": "0" * 64,
            }
        ],
        "queries": [
            {"id": "Q1", "question": "test question", "support_expected": True, "targets": [{"source_id": "test_source", "locator": "page 1"}]}
        ],
    }
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(json.dumps(seed), encoding="utf-8")
    corpus_dir = tmp_path / "corpus"
    pdf_dir = corpus_dir / "pdfs"
    pdf_dir.mkdir(parents=True)
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    pdf_path = pdf_dir / "test_source.pdf"
    with pdf_path.open("wb") as output:
        writer.write(output)
    seed["sources"][0]["pdf_sha256"] = sha256(pdf_path.read_bytes()).hexdigest()
    seed_path.write_text(json.dumps(seed), encoding="utf-8")

    manifest = prepare(seed_path, corpus_dir, offline=True)
    assert manifest["sources"][0]["pdf_pages"] == 1
    assert manifest["sources"][0]["nonempty_extracted_pages"] == 0
    assert manifest["sources"][0]["sha256"]
    with pytest.raises(ValueError, match="No extractable page text"):
        score(seed_path, corpus_dir, tmp_path / "report.json")

    pdf_path.write_bytes(pdf_path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="SHA-256 pin"):
        prepare(seed_path, corpus_dir, offline=True)


def test_mismatched_download_is_not_cached(tmp_path, monkeypatch):
    seed = {
        "status": "candidate_unadjudicated",
        "sources": [
            {
                "id": "test_source",
                "version": "test snapshot",
                "url": "https://eur-lex.europa.eu/test",
                "pdf_url": "https://eur-lex.europa.eu/test.pdf",
                "pdf_sha256": "0" * 64,
            }
        ],
        "queries": [
            {"id": "Q1", "question": "test question", "support_expected": True, "targets": [{"source_id": "test_source", "locator": "page 1"}]}
        ],
    }
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(json.dumps(seed), encoding="utf-8")
    monkeypatch.setattr("tools.retrieval_baseline._download_pdf", lambda _url: b"%PDF-not-the-pinned-file")
    corpus_dir = tmp_path / "corpus"

    with pytest.raises(ValueError, match="SHA-256 pin"):
        prepare(seed_path, corpus_dir)
    assert not (corpus_dir / "pdfs" / "test_source.pdf").exists()
