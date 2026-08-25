"""Demo CLI for the evidence-driven claim analysis prototype.

Two modes:

* ``--provider fixture --case <name>`` — offline, uses recorded JSON. Never
  contacts an LLM. Ideal for reproducing the canonical demo cases.
* ``--provider openai --images <front.jpg> [<back.jpg> ...]`` — hits the live
  OpenAI Responses API for vision extraction and claim normalization; requires
  ``OPENAI_API_KEY`` in the environment. Multiple images of the same product
  pack are merged into a single extraction.

The ``--record`` flag writes a fresh ``extract.json`` and ``normalize.json``
under ``tests/fixtures/<case>/`` — use it to regenerate fixtures after
prompt or schema changes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from foodpharmer.evidence import (
    ComparatorProductSource,
    FssaiRegulationSource,
    MarketDataSource,
    PackagingSource,
)
from foodpharmer.pipeline import analyze
from foodpharmer.providers.fixture_provider import FixtureProvider
from foodpharmer.reporting import render_compact
from foodpharmer.retrieval import LocalFssaiRetriever


DEFAULT_FSSAI_DIR = "data/fssai"
DEFAULT_FIXTURES_DIR = "tests/fixtures"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidence-driven claim analysis demo.")
    parser.add_argument(
        "--images",
        nargs="+",
        metavar="PATH",
        help=(
            "One or more package images (JPG/PNG/WebP) of the same product. "
            "Typical usage: --images front.jpg back.jpg"
        ),
    )
    parser.add_argument(
        "--provider",
        choices=("fixture", "openai"),
        default="fixture",
        help="LLM backend. Defaults to fixture (offline).",
    )
    parser.add_argument(
        "--case",
        help="Fixture case name (required with --provider fixture and with --record).",
    )
    parser.add_argument(
        "--fixtures-dir",
        default=DEFAULT_FIXTURES_DIR,
        help=f"Directory of case fixtures (default: {DEFAULT_FIXTURES_DIR}).",
    )
    parser.add_argument(
        "--fssai-dir",
        default=DEFAULT_FSSAI_DIR,
        help=f"Directory of FSSAI PDFs (default: {DEFAULT_FSSAI_DIR}).",
    )
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full ClaimAnalysisResult JSON instead of the compact summary.",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help=(
            "Record extraction+normalization to the case fixtures directory. "
            "Requires --provider openai (implied), --case, and --images."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    retriever = LocalFssaiRetriever.from_directory(args.fssai_dir)
    sources = [
        PackagingSource(),
        FssaiRegulationSource(retriever),
        ComparatorProductSource(),
        MarketDataSource(),
    ]

    if args.record:
        return _run_record(args, sources)
    if args.provider == "fixture":
        return _run_fixture(args, sources)
    return _run_openai(args, sources)


def _load_images(paths: list[str]) -> list[tuple[bytes, str]]:
    from foodpharmer.providers.openai_provider import guess_media_type

    return [(Path(p).read_bytes(), guess_media_type(p)) for p in paths]


def _run_fixture(args: argparse.Namespace, sources) -> int:
    if not args.case:
        print("--case is required when --provider is fixture.", file=sys.stderr)
        return 2
    provider = FixtureProvider.for_case(args.case, args.fixtures_dir)
    # Fixture provider ignores the actual image bytes; passing a single empty
    # image satisfies the "at least one image" contract without doing I/O.
    if args.images:
        images = _load_images(args.images)
        image_paths: list[str] = list(args.images)
    else:
        images = [(b"", "image/png")]
        image_paths = [args.case]
    result = analyze(images, provider, sources, image_paths=image_paths)
    _print_result(result, as_json=args.json)
    return 0


def _run_openai(args: argparse.Namespace, sources) -> int:
    if not args.images:
        print("--images is required with --provider openai.", file=sys.stderr)
        return 2
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        return 2
    from foodpharmer.providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider(model=args.model)
    images = _load_images(args.images)
    result = analyze(images, provider, sources, image_paths=list(args.images))
    _print_result(result, as_json=args.json)
    return 0


def _print_result(result, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        print(render_compact(result), end="")


def _run_record(args: argparse.Namespace, sources) -> int:
    if not args.case:
        print("--record requires --case.", file=sys.stderr)
        return 2
    if not args.images:
        print("--record requires --images.", file=sys.stderr)
        return 2
    if not os.environ.get("OPENAI_API_KEY"):
        print("--record requires OPENAI_API_KEY.", file=sys.stderr)
        return 2
    from foodpharmer.providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider(model=args.model)
    images = _load_images(args.images)
    extraction = provider.extract_package(images)
    normalizations = {
        claim.claim: provider.normalize_claim(claim.claim, extraction).model_dump(mode="json")
        for claim in extraction.claims
    }
    case_dir = Path(args.fixtures_dir) / args.case
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "extract.json").write_text(
        json.dumps(extraction.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    (case_dir / "normalize.json").write_text(
        json.dumps(normalizations, indent=2), encoding="utf-8"
    )
    print(f"Recorded fixtures for case {args.case} in {case_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
