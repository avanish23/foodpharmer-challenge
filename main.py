"""Demo CLI for the evidence-driven claim analysis prototype.

Two modes:

* ``--provider fixture --case <name>`` — offline, uses recorded JSON. Never
  contacts an LLM. Ideal for reproducing the canonical demo cases.
* ``--provider openai --image <path>`` — hits the live OpenAI Responses API
  for vision extraction and claim normalization; requires ``OPENAI_API_KEY``
  in the environment.

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
    parser.add_argument("--image", help="Path to a package image (JPG/PNG/WebP).")
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
            "Requires --provider openai (implied), --case, and --image."
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


def _run_fixture(args: argparse.Namespace, sources) -> int:
    if not args.case:
        print("--case is required when --provider is fixture.", file=sys.stderr)
        return 2
    provider = FixtureProvider.for_case(args.case, args.fixtures_dir)
    image_bytes = b""
    image_path = args.image or args.case
    if args.image:
        image_bytes = Path(args.image).read_bytes()
    result = analyze(image_bytes, "image/png", provider, sources, image_path=image_path)
    _print_result(result, as_json=args.json)
    return 0


def _run_openai(args: argparse.Namespace, sources) -> int:
    if not args.image:
        print("--image is required with --provider openai.", file=sys.stderr)
        return 2
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        return 2
    from foodpharmer.providers.openai_provider import (
        OpenAIProvider,
        guess_media_type,
    )

    provider = OpenAIProvider(model=args.model)
    image_bytes = Path(args.image).read_bytes()
    result = analyze(
        image_bytes,
        guess_media_type(args.image),
        provider,
        sources,
        image_path=args.image,
    )
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
    if not args.image:
        print("--record requires --image.", file=sys.stderr)
        return 2
    if not os.environ.get("OPENAI_API_KEY"):
        print("--record requires OPENAI_API_KEY.", file=sys.stderr)
        return 2
    from foodpharmer.providers.openai_provider import (
        OpenAIProvider,
        guess_media_type,
    )

    provider = OpenAIProvider(model=args.model)
    image_bytes = Path(args.image).read_bytes()
    extraction = provider.extract_package(image_bytes, guess_media_type(args.image))
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
