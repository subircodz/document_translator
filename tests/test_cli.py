import pytest

from document_translator.cli import _default_output, _language, build_parser
from document_translator.models import Language


def test_language_accepts_target_code() -> None:
    assert _language("HI") is Language.HINDI


def test_language_rejects_english() -> None:
    with pytest.raises(Exception, match="six Indian languages"):
        _language("en")


def test_default_output() -> None:
    assert _default_output(__import__("pathlib").Path("report.docx"), Language.TAMIL).name == "report.ta.docx"


def test_parser_requires_target() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["input.docx"])
