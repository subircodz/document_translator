"""Command-line interface for document translation."""

import argparse
import os
from pathlib import Path

from document_translator.models import Language


def _language(value: str) -> Language:
    try:
        return Language(value.lower())
    except ValueError as exc:
        choices = ", ".join(lang.value for lang in Language)
        raise argparse.ArgumentTypeError(
            f"Unsupported language '{value}'. Choose from: {choices}."
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    """Build the document-translator CLI parser."""
    parser = argparse.ArgumentParser(
        prog="document-translator",
        description="Translate a supported English DOCX document.",
    )
    parser.add_argument("input", type=Path, help="Input DOCX file.")
    parser.add_argument("-o", "--output", type=Path, help="Output DOCX file.")
    parser.add_argument(
        "-t",
        "--target",
        required=True,
        type=_language,
        help="Target language code (hi, bn, kn, te, ta, ml).",
    )
    return parser


def _default_output(input_path: Path, target: Language) -> Path:
    return input_path.with_name(f"{input_path.stem}.{target.value}.docx")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.target is Language.ENGLISH:
        parser.error("Target language must differ from English.")
    if args.input.suffix.lower() != ".docx":
        parser.error("Input must be a .docx file.")
    if not args.input.is_file():
        parser.error(f"Input file does not exist: {args.input}")

    output = args.output or _default_output(args.input, args.target)
    if output.resolve() == args.input.resolve():
        parser.error("Output file must differ from input file.")
    if not os.environ.get("GOOGLE_TRANSLATE_API_KEY"):
        parser.error("GOOGLE_TRANSLATE_API_KEY is not configured.")

    parser.error(
        "DOCX translation orchestration is not yet enabled. "
        "Phase 5 CLI foundation is installed, but orchestration is still in progress."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
