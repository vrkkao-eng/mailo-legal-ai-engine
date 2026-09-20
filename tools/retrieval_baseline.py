"""Offline, source-level retrieval baseline for the unadjudicated seed.

This tool does not make legal findings and is not part of the MAILO API/CLI.
Downloaded source PDFs and extracted page text stay under an ignored data directory.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ALLOWED_HOSTS = {"eur-lex.europa.eu", "health.ec.europa.eu"}
MAX_PDF_BYTES = 25_000_000
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SOURCE_ID_PATTERN = re.compile(r"[a-z0-9_]+\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
DEFAULT_SEED = Path(__file__).resolve().parents[1] / "evals" / "retrieval_seed.json"


def _check_official_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
    ):
        raise ValueError(f"Non-allowlisted source URL: {url}")


class _OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        _check_official_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def load_seed(path: Path) -> dict:
    seed = json.loads(path.read_text(encoding="utf-8"))
    if seed.get("status") != "candidate_unadjudicated":
        raise ValueError("Expected an explicitly unadjudicated candidate seed")
    sources = seed.get("sources")
    queries = seed.get("queries")
    if not isinstance(sources, list) or not sources or not isinstance(queries, list):
        raise ValueError("Seed needs non-empty sources and queries lists")
    source_ids: set[str] = set()
    for source in sources:
        source_id = source.get("id")
        if not isinstance(source_id, str) or not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise ValueError(f"Invalid source ID: {source_id!r}")
        if source_id in source_ids:
            raise ValueError(f"Duplicate source ID: {source_id}")
        source_ids.add(source_id)
        for key in ("url", "pdf_url"):
            if not isinstance(source.get(key), str):
                raise ValueError(f"Missing {key} for {source_id}")
            _check_official_url(source[key])
        expected_hash = source.get("pdf_sha256")
        if not isinstance(expected_hash, str) or not SHA256_PATTERN.fullmatch(expected_hash):
            raise ValueError(f"Missing or invalid PDF SHA-256 pin for {source_id}")
    query_ids: set[str] = set()
    for query in queries:
        query_id = query.get("id")
        if not isinstance(query_id, str) or not query_id:
            raise ValueError("Query ID is missing")
        if query_id in query_ids:
            raise ValueError(f"Duplicate query ID: {query_id}")
        query_ids.add(query_id)
        if not isinstance(query.get("question"), str) or not query["question"].strip():
            raise ValueError(f"Question text is missing for {query_id}")
        if not isinstance(query.get("support_expected"), bool):
            raise ValueError(f"support_expected must be Boolean for {query_id}")
        targets = query.get("targets")
        if not isinstance(targets, list):
            raise ValueError(f"targets must be a list for {query_id}")
        if query["support_expected"] != bool(targets):
            raise ValueError(f"Targets disagree with support_expected for {query_id}")
        for target in targets:
            if target.get("source_id") not in source_ids or not target.get("locator"):
                raise ValueError(f"Invalid target for {query_id}")
        if any(related not in source_ids for related in query.get("related_sources", [])):
            raise ValueError(f"Invalid related source for {query_id}")
    if not any(query["support_expected"] for query in queries):
        raise ValueError("At least one positive query is needed for retrieval scoring")
    return seed


def _download_pdf(url: str) -> bytes:
    _check_official_url(url)
    opener = build_opener(_OfficialRedirects())
    request = Request(url, headers={"User-Agent": "MAILO-retrieval-evaluation/0.1"})
    with opener.open(request, timeout=45) as response:
        _check_official_url(response.geturl())
        data = response.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise ValueError(f"PDF exceeds {MAX_PDF_BYTES} bytes: {url}")
    if not data.startswith(b"%PDF-"):
        raise ValueError(f"Source did not return a PDF: {url}")
    return data


def prepare(seed_path: Path, output_dir: Path, *, offline: bool = False) -> dict:
    try:
        from pypdf import PdfReader, __version__ as pypdf_version
    except ImportError as exc:
        raise RuntimeError('Install the optional retrieval dependencies: pip install ".[retrieval]"') from exc

    seed = load_seed(seed_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir = output_dir / "pdfs"
    pdf_dir.mkdir(exist_ok=True)
    previous_manifest_path = output_dir / "manifest.json"
    previous_sources = {}
    if previous_manifest_path.exists():
        previous_manifest = json.loads(previous_manifest_path.read_text(encoding="utf-8"))
        if previous_manifest.get("seed_sha256") != sha256(seed_path.read_bytes()).hexdigest():
            raise ValueError("Existing corpus uses a different seed; choose a new --out directory")
        previous_sources = {item["source_id"]: item for item in previous_manifest["sources"]}
    all_pages: list[dict] = []
    manifest_sources: list[dict] = []
    for source in seed["sources"]:
        source_id = source["id"]
        pdf_path = pdf_dir / f"{source_id}.pdf"
        downloaded = False
        if pdf_path.exists():
            pdf_bytes = pdf_path.read_bytes()
        elif offline:
            raise FileNotFoundError(f"Offline PDF missing: {pdf_path}")
        else:
            pdf_bytes = _download_pdf(source["pdf_url"])
            downloaded = True
        if not pdf_bytes.startswith(b"%PDF-") or len(pdf_bytes) > MAX_PDF_BYTES:
            raise ValueError(f"Invalid cached PDF: {pdf_path}")
        pdf_sha256 = sha256(pdf_bytes).hexdigest()
        if pdf_sha256 != source["pdf_sha256"]:
            raise ValueError(f"PDF does not match the seed's SHA-256 pin: {source_id}")
        if source_id in previous_sources and previous_sources[source_id]["sha256"] != pdf_sha256:
            raise ValueError(f"PDF hash changed for {source_id}; choose a new --out directory")
        if downloaded:
            pdf_path.write_bytes(pdf_bytes)
        reader = PdfReader(BytesIO(pdf_bytes))
        nonempty_pages = 0
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = " ".join((page.extract_text() or "").split())
            nonempty_pages += bool(page_text)
            all_pages.append(
                {
                    "page_id": f"{source_id}:p{page_number:04d}",
                    "source_id": source_id,
                    "pdf_page": page_number,
                    "text": page_text,
                }
            )
        manifest_sources.append(
            {
                "source_id": source_id,
                "version": source["version"],
                "pdf_url": source["pdf_url"],
                "sha256": pdf_sha256,
                "bytes": len(pdf_bytes),
                "pdf_pages": len(reader.pages),
                "nonempty_extracted_pages": nonempty_pages,
            }
        )
    pages_path = output_dir / "pages.jsonl"
    pages_path.write_text(
        "".join(json.dumps(page, ensure_ascii=False) + "\n" for page in all_pages),
        encoding="utf-8",
    )
    manifest = {
        "status": "candidate_unadjudicated",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed_sha256": sha256(seed_path.read_bytes()).hexdigest(),
        "extractor": f"pypdf {pypdf_version}",
        "page_text_sha256": sha256(pages_path.read_bytes()).hexdigest(),
        "sources": manifest_sources,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def rank_sources(question: str, pages: list[dict], source_ids: list[str]) -> list[dict]:
    documents = [tokenize(page["text"]) for page in pages]
    if not documents or not any(documents):
        raise ValueError("No extractable page text in corpus")
    document_frequency = Counter(token for doc in documents for token in set(doc))
    average_length = sum(map(len, documents)) / len(documents)
    source_best: dict[str, tuple[float, int]] = {source_id: (0.0, 0) for source_id in source_ids}
    for page, tokens in zip(pages, documents):
        counts = Counter(tokens)
        score = 0.0
        for token in set(tokenize(question)):
            frequency = counts[token]
            if not frequency:
                continue
            df = document_frequency[token]
            idf = math.log(1 + (len(documents) - df + 0.5) / (df + 0.5))
            score += idf * frequency * 2.2 / (
                frequency + 1.2 * (0.25 + 0.75 * len(tokens) / average_length)
            )
        source_id = page["source_id"]
        if score > source_best[source_id][0]:
            source_best[source_id] = (score, page["pdf_page"])
    ranked = sorted(
        (source_id for source_id in source_best if source_best[source_id][0] > 0),
        key=lambda source_id: (-source_best[source_id][0], source_id),
    )
    return [
        {"source_id": source_id, "score": round(source_best[source_id][0], 6), "best_pdf_page": source_best[source_id][1]}
        for source_id in ranked
    ]


def evaluate(seed: dict, pages: list[dict], *, ks: tuple[int, ...] = (1, 3, 5)) -> dict:
    source_ids = [source["id"] for source in seed["sources"]]
    if {page["source_id"] for page in pages} != set(source_ids):
        raise ValueError("Corpus source IDs do not match the seed")
    if len({page["page_id"] for page in pages}) != len(pages):
        raise ValueError("Duplicate page IDs in corpus")
    positive_results = []
    negative_ids = []
    for query in seed["queries"]:
        if not query["support_expected"]:
            negative_ids.append(query["id"])
            continue
        ranking = rank_sources(query["question"], pages, source_ids)
        gold = {target["source_id"] for target in query["targets"]}
        ranks = {item["source_id"]: index for index, item in enumerate(ranking, start=1)}
        positive_results.append(
            {
                "query_id": query["id"],
                "candidate_gold_sources": sorted(gold),
                "ranked_sources": ranking,
                "first_relevant_rank": min((ranks[source_id] for source_id in gold if source_id in ranks), default=None),
            }
        )
    metrics = {}
    for k in ks:
        metrics[f"macro_source_recall_at_{k}"] = round(
            sum(
                len(set(result["candidate_gold_sources"]) & {item["source_id"] for item in result["ranked_sources"][:k]})
                / len(result["candidate_gold_sources"])
                for result in positive_results
            )
            / len(positive_results),
            6,
        )
        metrics[f"complete_source_coverage_at_{k}"] = round(
            sum(
                set(result["candidate_gold_sources"]).issubset(
                    {item["source_id"] for item in result["ranked_sources"][:k]}
                )
                for result in positive_results
            )
            / len(positive_results),
            6,
        )
    metrics["mean_reciprocal_rank_first_source"] = round(
        sum(1 / result["first_relevant_rank"] if result["first_relevant_rank"] else 0 for result in positive_results)
        / len(positive_results),
        6,
    )
    return {
        "status": "exploratory_unadjudicated",
        "method": "BM25 over extracted PDF pages; each source ranked by its highest-scoring page",
        "positive_query_count": len(positive_results),
        "excluded_negative_query_ids": negative_ids,
        "metrics": metrics,
        "queries": positive_results,
    }


def score(seed_path: Path, corpus_dir: Path, report_path: Path) -> dict:
    seed = load_seed(seed_path)
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    pages_path = corpus_dir / "pages.jsonl"
    if manifest.get("seed_sha256") != sha256(seed_path.read_bytes()).hexdigest():
        raise ValueError("Corpus was prepared from a different seed; prepare it again")
    if manifest.get("page_text_sha256") != sha256(pages_path.read_bytes()).hexdigest():
        raise ValueError("Extracted page text does not match its manifest hash")
    for source in manifest["sources"]:
        pdf_path = corpus_dir / "pdfs" / f"{source['source_id']}.pdf"
        if sha256(pdf_path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"PDF does not match its manifest hash: {source['source_id']}")
    pages = [json.loads(line) for line in pages_path.read_text(encoding="utf-8").splitlines()]
    report = evaluate(seed, pages)
    report["corpus_manifest_sha256"] = sha256((corpus_dir / "manifest.json").read_bytes()).hexdigest()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare", help="Download and extract version-pinned PDFs")
    prepare_parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    prepare_parser.add_argument("--out", type=Path, default=Path("data/retrieval"))
    prepare_parser.add_argument("--offline", action="store_true", help="Only use existing PDFs under --out/pdfs")
    score_parser = subparsers.add_parser("score", help="Run a provisional source-level BM25 baseline")
    score_parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    score_parser.add_argument("--corpus", type=Path, default=Path("data/retrieval"))
    score_parser.add_argument("--report", type=Path, default=Path("data/retrieval/report.json"))
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.seed, args.out, offline=args.offline)
            print(f"Prepared {len(result['sources'])} sources in {args.out}")
        else:
            result = score(args.seed, args.corpus, args.report)
            print(f"Scored {result['positive_query_count']} unadjudicated positive queries: {args.report}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Retrieval baseline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
