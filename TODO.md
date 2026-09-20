# TODO

## Active phase: Phase 5 — Application Interface

- [x] CLI foundation
- [x] Input/output handling
- [x] Language selection
- [x] Single-document translation orchestration
- [ ] Batch translation
- [x] User-friendly errors

## Completed Phase 4


- [x] Language registry
- [x] Translation provider protocol
- [x] Translation result/error models
- [x] Protected-token model and basic protection
- [x] Google Cloud Translation adapter
- [x] Bounded translation batching
- [x] Transient-failure retries
- [x] Provider integration tests with mocks
- [x] Token protection integrated with translation service
- [x] Translation validation rules
- [x] Validation report model
- [x] Human-readable document-level report
- [x] Validate complete translated DOCX output
- [x] Unit tests
- [x] Ruff configuration
- [x] CI workflow
- [x] DOCX reader/writer

## Engineering rules

1. Do not add UI before the document and translation domain contracts are stable.
2. Do not couple document processing to a specific translation provider.
3. Do not silently discard translation failures.
4. Treat identifiers, URLs, emails, numbers, and placeholders as protected data.
5. Keep Unicode handling explicit and tested.
6. Update this file and ROADMAP.md when a phase changes.
