# Roadmap

## Phase 1 — Engineering Foundation
- [x] Define six target languages
- [x] Define domain models
- [x] Define translation-provider contract
- [x] Add token protection component
- [x] Add initial tests
- [x] Add Ruff configuration
- [x] Add GitHub Actions CI
- [x] DOCX reader/writer

## Phase 2 — DOCX Engine
- [x] Read paragraphs and runs
- [x] Read headings
- [x] Read tables
- [x] Preserve supported document structure
- [x] Reconstruct translated DOCX
- [x] Round-trip tests
- [x] Preserve translated run formatting

## Phase 3 — Translation Engine
- [x] Implement a real provider adapter
- [x] Batch/chunk translation safely
- [x] Retry transient failures
- [x] Protect and restore non-translatable tokens
- [x] Translation error model
- [x] Provider integration tests with mocks

**Current provider:** Google Cloud Translation Basic API (v2), using the six configured Indian target languages.

## Phase 4 — Validation & Reporting
- [x] Detect missing translated content
- [x] Verify protected-token restoration
- [x] Unicode validation
- [x] Translation validation report model
- [x] Failure/warning classification
- [x] Human-readable document-level report
- [x] Validate complete translated DOCX output

## Phase 5 — Application Interface
- [x] CLI foundation
- [x] Input/output handling
- [x] Language selection
- [x] Batch translation
- [x] User-friendly errors
- [x] CLI output validation and report

## Phase 6 — Web Application
- [x] Upload DOCX document
- [x] Select one or more target languages
- [x] Translation progress and job status
- [x] Download translated DOCX outputs
- [x] Download validation reports
- [x] Re-validate generated DOCX before exposing downloads

## Phase 7 — Production Hardening
- [x] Configuration and secrets handling
- [x] Structured logging
- [x] File/type/size limits
- [x] DOCX archive validation
- [x] Job TTL cleanup
- [x] Basic authentication support
- [x] Request rate limiting
- [x] Concurrent-job limit
- [x] Security review
- [x] Dependency review
- [x] Performance controls
- [x] Release workflow
- [x] CI build and wheel-install verification
- [x] Production deployment documentation

**Release scope:** production-ready for a controlled single-instance deployment. The application is intentionally not a distributed multi-instance service; persistent shared jobs, durable object storage, and a worker queue remain future scaling work.

**Release gate:** all CI matrix jobs must be green before tagging a release.
