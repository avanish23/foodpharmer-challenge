"""Command-line entry point for the FoodPharmer V1 analyzer."""

import argparse
import json
from pathlib import Path

from foodpharmer.analyzer import analyze_package


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate visible package marketing claims against supplied FSSAI rules."
    )
    parser.add_argument("--image", required=True, help="Path to a JPG, PNG, or WebP package image.")
    parser.add_argument("--rules", required=True, help="Path to a text file containing applicable FSSAI rules.")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model to use.")
    args = parser.parse_args()

    rules = Path(args.rules).read_text(encoding="utf-8")
    result = analyze_package(args.image, rules, model=args.model)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
