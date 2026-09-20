# TODO

## Active phase: Phase 1 — Engineering Foundation

- [x] Language registry
- [x] Translation provider protocol
- [x] Translation result/error models
- [x] Protected-token model and basic protection
- [x] Unit tests
- [x] Ruff configuration
- [x] CI workflow
- [ ] DOCX reader/writer

## Engineering rules

1. Do not add UI before the document and translation domain contracts are stable.
2. Do not couple document processing to a specific translation provider.
3. Do not silently discard translation failures.
4. Treat identifiers, URLs, emails, numbers, and placeholders as protected data.
5. Keep Unicode handling explicit and tested.
6. Update this file and ROADMAP.md when a phase changes.
