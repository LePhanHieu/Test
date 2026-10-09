# Clean Code Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the verified transaction, medical, upload, API, and security defects; establish regression coverage; and perform evidence-based cleanup without changing successful API contracts, the database schema, or the UI.

**Architecture:** Work in risk order and keep each fix behind a regression test. Introduce small helpers for file publication, image validation, safe CSV cells, and JSON validation while leaving public route and model boundaries intact. Coordinate database and filesystem state explicitly because they cannot participate in one transaction.

**Tech Stack:** Python 3.12, Flask 3.1, SQLAlchemy 2, Flask-Login/WTF/Migrate/Mail, Pillow, pandas, OpenCV, PyTorch, ReportLab, pytest, JavaScript.

**Spec:** `docs/superpowers/specs/2026-10-09-clean-code-refactor-design.md`

## Global Constraints

- Preserve ADMIN, DOCTOR, USER, and temporary-patient workflows.
- Keep AI prediction distinct from Doctor diagnosis.
- Keep measurements in pixels, square pixels, and ratios.
- Keep the PDF medical disclaimer.
- Keep route paths, successful response shapes, database schema, and migration history unchanged.
- Do not remove checkpoints, models, research assets, or runtime data.
- Do not commit credentials, secrets, runtime databases, uploads, reports, or generated private artifacts.
- Make behavior changes only to correct verified defects or documented security gaps.

## Review Focus

- A report version conflict after PDF rendering must leave the winning report file intact; covered in Task 2 concurrency tests.
- An image whose decoded format differs from its extension must fail without leaving a file or a successful database status; covered in Task 4 validation tests.
- A rollback after one successful batch item must remove only files created by that request; covered in Task 4 cleanup tests.
- An AI exception after an Analysis row is allocated must leave a FAILED audit row and must not expose internal exception text; covered in Task 3 route tests.
- Public JSON endpoints must return JSON for malformed top-level payload types without weakening CSRF or authorization; covered in Tasks 1 and 5.

---

### Task 1: Test Foundation and Security Characterization

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_auth_authorization.py`
- Create: `tests/test_migrations.py`
- Modify: `pytest.ini`

**Interfaces:**
- Consumes: `skin_cancer.webapp.database_app:create_app`, SQLAlchemy models, existing route contracts.
- Produces: `app`, `client`, `db_session`, `users`, and `case_graph` pytest fixtures for later tasks.

- [ ] **Step 1: Create isolated SQLite/temp-storage fixtures and tests for CSRF, password hashing, role/ownership visibility, report download IDOR, temporary-patient snapshots, and JSON error content type.**
- [ ] **Step 2: Run `python -m pytest tests/test_auth_authorization.py -q`; expect characterization tests to pass against the baseline.**
- [ ] **Step 3: Add migration tests that invoke Alembic upgrade on a fresh temporary database and assert one head plus no metadata drift.**
- [ ] **Step 4: Run `python -m pytest tests/test_migrations.py -q`; expect pass.**
- [ ] **Step 5: Run the combined suite and commit as `test: establish application regression harness`.**

### Task 2: Atomic Report Publication and Reviewer Attribution

**Files:**
- Create: `tests/test_report_service.py`
- Modify: `skin_cancer/webapp/services/report_service.py`

**Interfaces:**
- Consumes: Task 1 database fixtures; `ReportService.generate(case, analysis, generated_by) -> Report`.
- Produces: request-owned temporary PDF publication and reviewer identity sourced from `DoctorReview.doctor`.

- [ ] **Step 1: Add a concurrent-generation test that asserts every committed Report has a readable final PDF and a failed operation cannot unlink another operation's file; run it and verify RED.**
- [ ] **Step 2: Add a PDF review-card test where ADMIN authored the review and another DOCTOR owns the Case; assert the persisted reviewer name is used; run it and verify RED.**
- [ ] **Step 3: Implement unique temporary paths, bounded unique-version retry, atomic final publication, ownership-aware cleanup, and review-author rendering.**
- [ ] **Step 4: Run `python -m pytest tests/test_report_service.py -q`; expect pass, then run the full suite.**
- [ ] **Step 5: Commit as `fix: make report publication and attribution reliable`.**

### Task 3: AI Interpretation and Failure Audit

**Files:**
- Create: `skin_cancer/webapp/services/ai_interpretation.py`
- Create: `tests/test_ai_interpretation.py`
- Create: `tests/test_ai_error_handling.py`
- Modify: `skin_cancer/webapp/app.py`

**Interfaces:**
- Consumes: binary prediction/probability, multiclass class/probability, and existing Analysis models.
- Produces: `generate_interpretation(binary_prediction, probability_malignant, predicted_class, predicted_probability) -> dict` and durable FAILED analysis state.

- [ ] **Step 1: Add the 99%-malignant/30%-NV regression test and assert the lesion-class sentence uses 30%, not 99%; run it and verify RED.**
- [ ] **Step 2: Extract a side-effect-free interpretation service and delegate from `app.py`; run the test and verify GREEN.**
- [ ] **Step 3: Add a stubbed inference failure test asserting generic JSON without exception detail and a persisted FAILED Analysis; run it and verify RED.**
- [ ] **Step 4: Separate incomplete-result rollback from FAILED audit persistence and replace `traceback.print_exc()`/client detail with structured server logging; run targeted and full tests.**
- [ ] **Step 5: Commit as `fix: separate AI confidence and preserve failure audits`.**

### Task 4: Upload Validation and Artifact Cleanup

**Files:**
- Create: `tests/test_batch_upload.py`
- Modify: `skin_cancer/webapp/config.py`
- Modify: `skin_cancer/webapp/services/batch_upload.py`
- Modify: `skin_cancer/webapp/routes/uploads.py`

**Interfaces:**
- Consumes: existing `BatchUploadService.process(files) -> BatchUploadResult` route contract.
- Produces: decoded-format validation, `BATCH_MAX_IMAGE_PIXELS`, correct aggregate request cap, and service-owned cleanup.

- [ ] **Step 1: Add tests for two valid 6 MiB files, per-file overflow, PNG bytes named JPEG, excessive pixel dimensions, and JPEG/JPG equivalence; run and verify the known failures.**
- [ ] **Step 2: Set aggregate `MAX_CONTENT_LENGTH` from batch count × per-file limit plus multipart allowance, validate decoded format/dimensions, and use a canonical stored extension.**
- [ ] **Step 3: Add a test that forces an exception on the second file and asserts the first artifact is removed while unrelated files remain; run and verify RED.**
- [ ] **Step 4: Track request-owned paths inside the service and clean them on exceptional exit; run targeted and full tests.**
- [ ] **Step 5: Commit as `fix: harden batch upload validation and cleanup`.**

### Task 5: CSV, JSON, and Rate-Limit Security

**Files:**
- Create: `skin_cancer/webapp/services/api_validation.py`
- Create: `tests/test_api_security.py`
- Modify: `skin_cancer/webapp/services/batch_upload.py`
- Modify: `skin_cancer/webapp/routes/report_generation.py`
- Modify: `skin_cancer/webapp/extensions.py`
- Modify: `skin_cancer/webapp/bootstrap.py`
- Modify: `skin_cancer/webapp/config.py`
- Modify: `requirements-database.txt`

**Interfaces:**
- Consumes: Flask request JSON and endpoint identity.
- Produces: `json_object_or_400() -> dict`, spreadsheet-safe CSV values, and configurable limits for login and expensive endpoints.

- [ ] **Step 1: Add tests for formula prefixes (`=`, `+`, `-`, `@`, tab, CR) and verify RED.**
- [ ] **Step 2: Add `spreadsheet_safe(value: object) -> object` and apply it only to exported string cells; verify GREEN.**
- [ ] **Step 3: Add malformed report JSON tests for list/string/number/null and assert JSON 400; verify RED, then add/use `json_object_or_400`.**
- [ ] **Step 4: Add rate-limit tests for repeated failed login and an expensive authenticated endpoint; integrate Flask-Limiter with memory storage for local/test and configurable production storage.**
- [ ] **Step 5: Run targeted tests, the full suite, and `pip check`; commit as `fix: protect API and exported batch data`.**

### Task 6: Storage Lifecycle and Evidence-Based Cleanup

**Files:**
- Create: `tests/test_measurement_artifacts.py`
- Modify: `skin_cancer/webapp/routes/measurements.py`
- Modify: Python modules identified by import analysis
- Modify: `requirements.txt`
- Modify: `requirements-database.txt`

**Interfaces:**
- Consumes: measurement service contour path result and the current import graph.
- Produces: post-commit deletion of replaced contour artifacts and a dependency/import set backed by repository-wide evidence.

- [ ] **Step 1: Add a re-measure test asserting the old contour is deleted only after the new path commits; run and verify RED.**
- [ ] **Step 2: Implement replacement cleanup with containment checks and rollback safety; run targeted and full tests.**
- [ ] **Step 3: Run AST/import search across tracked Python and notebooks/scripts; remove only imports/helpers proven unused and only direct dependencies with no source, script, notebook, or documented runtime use.**
- [ ] **Step 4: Run Python compilation, JavaScript syntax checks, full tests, and `pip check`.**
- [ ] **Step 5: Commit as `refactor: clean verified dead code and artifact lifecycle`.**

### Task 7: Configuration, Ignore Rules, Documentation, and Migration QA

**Files:**
- Modify: `.env.example`
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-10-09-clean-code-refactor-design.md` only if implementation decisions require factual synchronization
- Test: `tests/test_config.py`
- Test: `tests/test_migrations.py`

**Interfaces:**
- Consumes: final behavior and route/config inventory.
- Produces: accurate setup/deployment documentation without a schema migration.

- [ ] **Step 1: Add configuration tests for TLS/SSL exclusivity, aggregate upload limits, pixel limits, rate-limit settings, and secure-cookie environment parsing.**
- [ ] **Step 2: Add `MAIL_USE_SSL` and new non-secret configuration keys to `.env.example`; extend `.gitignore` for model/checkpoint policy, worktrees, ZIP output, and runtime artifacts without deleting files.**
- [ ] **Step 3: Update README tree, migration head, actual endpoints, upload limits, test commands, WSGI/proxy caveats, and the distinction between required external checkpoints and tracked class weights.**
- [ ] **Step 4: Run config tests and fresh migration upgrade/current/heads/check; assert schema/head unchanged.**
- [ ] **Step 5: Commit as `docs: synchronize configuration and operating guidance`.**

### Task 8: Final Quality Gate, Review, Pull Request, and Archive

**Files:**
- Modify: any file required by Critical/Important final review findings
- Create outside Git: `Project_Clean_Final.zip`

**Interfaces:**
- Consumes: completed Tasks 1–7.
- Produces: verified branch, review findings resolved, pushed PR, and source archive.

- [ ] **Step 1: Run the complete pytest suite, compileall, JavaScript syntax checks, `pip check`, migration checks, secret scan, `git diff --check`, and inspect the full diff.**
- [ ] **Step 2: Request an independent whole-branch code review; fix Critical/Important findings with RED→GREEN tests and rerun the full quality gate.**
- [ ] **Step 3: Build `Project_Clean_Final.zip` from tracked files at HEAD and inspect its file list for secrets/runtime data.**
- [ ] **Step 4: Commit any final review fixes, verify a clean worktree, and push `refactor/clean-code`.**
- [ ] **Step 5: Create a Pull Request against `main` with behavior changes, validation evidence, and remaining limitations.**
