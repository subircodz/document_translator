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

**Exit criteria:** foundation tests and CI are green; core contracts are stable.

## Phase 2 — DOCX Engine
- [x] Read paragraphs and runs
- [x] Read headings
- [x] Read tables
- [x] Preserve supported document structure
- [x] Reconstruct translated DOCX
- [x] Round-trip tests

## Phase 3 — Translation Engine
- [x] Implement a real provider adapter
- [x] Batch/chunk translation safely
- [x] Retry transient failures
- [x] Protect and restore non-translatable tokens
- [x] Translation error model
- [x] Provider integration tests with mocks

**Current provider:** Google Cloud Translation Basic API (v2), using the six configured Indian target languages.

## Phase 4 — Validation & Reporting
- [ ] Detect missing translated content
- [ ] Verify protected-token restoration
- [ ] Unicode validation
- [ ] Translation report
- [ ] Failure/warning classification

## Phase 5 — Application Interface
- [ ] CLI
- [ ] Input/output handling
- [ ] Language selection
- [ ] Batch translation
- [ ] User-friendly errors

## Phase 6 — Web Application
- [ ] Upload document
- [ ] Select target languages
- [ ] Translation progress
- [ ] Download outputs
- [ ] Report download

## Phase 7 — Production Hardening
- [ ] Configuration and secrets handling
- [ ] Structured logging
- [ ] File/type/size limits
- [ ] Security review
- [ ] Dependency review
- [ ] Performance tests
- [ ] Release workflow
