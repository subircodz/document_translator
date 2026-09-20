# Roadmap

## Phase 1 — Engineering Foundation
- [x] Define six target languages
- [x] Define domain models
- [x] Define translation-provider contract
- [x] Add token protection component
- [x] Add initial tests
- [x] Add Ruff configuration
- [x] Add GitHub Actions CI
- [ ] DOCX reader/writer

**Exit criteria:** foundation tests and CI are green; core contracts are stable.

## Phase 2 — DOCX Engine
- [ ] Read paragraphs and runs
- [ ] Read headings
- [ ] Read tables
- [ ] Preserve supported document structure
- [ ] Reconstruct translated DOCX
- [ ] Round-trip tests

## Phase 3 — Translation Engine
- [ ] Implement a real provider adapter
- [ ] Batch/chunk translation safely
- [ ] Retry transient failures
- [ ] Protect and restore non-translatable tokens
- [ ] Translation error model
- [ ] Provider integration tests with mocks

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
