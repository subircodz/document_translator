from document_translator.models import Language
from document_translator.translation.provider import TranslationProvider


def test_package_imports() -> None:
    assert Language.TAMIL.value == "ta"
    assert TranslationProvider is not None
