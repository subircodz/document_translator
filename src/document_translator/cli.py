"""Command-line interface for document translation."""

import argparse
import os
from pathlib import Path

from document_translator.document.reader import read_docx
from document_translator.document.writer import write_docx
from document_translator.models import Language, TARGET_LANGUAGES
from document_translator.translation.document import translate_document
from document_translator.translation.google_cloud import GoogleCloudTranslationProvider
from document_translator.translation.service import TranslationService


def _language(value: str) -> Language:
    try:
        language = Language(value.lower())
    except ValueError as exc:
        choices = ", ".join(lang.value for lang in sorted(TARGET_LANGUAGES, key=lambda item: item.value))
        raise argparse.ArgumentTypeError(
            f"Unsupported target language '{value}'. Choose from: {choices}."
        ) from exc
    if language not in TARGET_LANGUAGES:
        raise argparse.ArgumentTypeError("Target language must be one of the six Indian languages.")
    return language


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="document-translator",
        description="Translate an English DOCX document into an Indian language.",
    )
    parser.add_argument("input", type=Path, help="Input DOCX file.")
    parser.add_argument("-o", "--output", type=Path, help="Output DOCX file.")
    parser.add_argument(
        "-t", "--target", required=True, type=_language,
        help="Target language: hi, bn, kn, te, ta, or ml.",
    )
    return parser


def _default_output(input_path: Path, target: Language) -> Path:
    return input_path.with_name(f"{input_path.stem}.{target.value}.docx")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.input.suffix.lower() != ".docx":
        parser.error("Input must be a .docx file.")
    if not args.input.is_file():
        parser.error(f"Input file does not exist: {args.input}")
    output = args.output or _default_output(args.input, args.target)
    if output.resolve() == args.input.resolve():
        parser.error("Output file must differ from input file.")
    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        parser.error("GOOGLE_TRANSLATE_API_KEY is not configured.")

    try:
        source = read_docx(args.input)
        service = TranslationService(GoogleCloudTranslationProvider(api_key=api_key))
        translated = translate_document(source, service, args.target)
        write_docx(translated, output)
    except OSError as exc:
        parser.error(f"Document file error: {exc}")
    except RuntimeError as exc:
        parser.error(f"Translation failed: {exc}")

    print(f"Translated document written to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
