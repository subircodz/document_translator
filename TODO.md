# TODO

## Release status: v0.5.0

- [x] Production web authentication
- [x] Request rate limiting
- [x] Concurrent-job protection
- [x] DOCX archive validation
- [x] CLI output validation
- [x] Translated run-format preservation
- [x] CI matrix
- [x] Built-package verification
- [x] Release workflow verification

## Completed Phase 6 — Web Application

- [x] DOCX upload
- [x] Multiple target language selection
- [x] Background translation job
- [x] Progress/status endpoint
- [x] Translated DOCX downloads
- [x] Validation report downloads
- [x] Validate generated DOCX before download

## Future scaling work — not required for v0.5.0 controlled release

- [ ] Persistent shared job storage
- [ ] Durable object storage
- [ ] Distributed worker/task queue
- [ ] Multi-instance shared rate limiting
- [ ] User/tenant authorization model

## Engineering rules

1. Do not add UI before the document and translation domain contracts are stable.
2. Do not couple document processing to a specific translation provider.
3. Do not silently discard translation failures.
4. Treat identifiers, URLs, emails, numbers, and placeholders as protected data.
5. Keep Unicode handling explicit and tested.
6. Update this file and ROADMAP.md when a phase changes.
7. Do not tag a release until the complete CI matrix is green.
