from document_translator.protection.tokens import protect, restore


def test_protect_and_restore_supported_tokens() -> None:
    source = "Contact test@example.com for Order ORD-10291 at https://example.com."
    protected = protect(source)

    assert "test@example.com" not in protected.text
    assert "ORD-10291" not in protected.text
    assert "https://example.com." not in protected.text
    assert restore(protected.text, protected.tokens) == source


def test_unicode_text_survives_protection() -> None:
    source = "Welcome नमस्ते নমস্কার ಕನ್ನಡ తెలుగు தமிழ் മലയാളം"
    protected = protect(source)

    assert protected.text == source
