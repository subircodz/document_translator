from document_translator.models import Language, TARGET_LANGUAGES


def test_all_target_languages_are_registered() -> None:
    assert TARGET_LANGUAGES == {
        Language.HINDI,
        Language.BENGALI,
        Language.KANNADA,
        Language.TELUGU,
        Language.TAMIL,
        Language.MALAYALAM,
    }


def test_english_is_source_language() -> None:
    assert Language.ENGLISH.value == "en"
