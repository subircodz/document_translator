import time

from document_translator.protection.tokens import protect_text


def test_token_protection_scales_to_large_document() -> None:
    text = " ".join(
        f"Order ORD-ABC-{index:06d} email user{index}@example.com amount {index * 10}.50"
        for index in range(5000)
    )
    started = time.perf_counter()
    protected = protect_text(text)
    elapsed = time.perf_counter() - started
    assert len(protected.tokens) >= 5000
    assert elapsed < 2.0
