"""Command-line entry point for the FoodPharmer V2 analyzer."""

import argparse
import json

from foodpharmer.analyzer import analyze_package
from foodpharmer.retrieval import LocalFssaiRetriever


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate visible package marketing claims using local FSSAI documents."
    )
    parser.add_argument("--image", required=True, help="Path to a JPG, PNG, or WebP package image.")
    parser.add_argument(
        "--fssai-dir",
        default="data/fssai",
        help="Directory containing official FSSAI PDF documents (default: data/fssai).",
    )
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model to use.")
    args = parser.parse_args()

    retriever = LocalFssaiRetriever.from_directory(args.fssai_dir)
    result = analyze_package(args.image, retriever, model=args.model)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
