# Clean Code Refactor and Quality Assurance Design

## Purpose

Improve the repository's correctness, security, maintainability, and operational reliability while preserving its current business rules, successful API contracts, database schema, and user interface. The work targets findings verified during the preceding repository review and avoids feature development or a broad rewrite.

## Constraints

- Preserve the ADMIN, DOCTOR, USER, and temporary-patient workflows.
- Keep AI prediction distinct from Doctor diagnosis.
- Keep measurements in pixels, square pixels, and ratios without introducing physical units.
- Keep the PDF medical disclaimer.
- Keep all current route paths and successful response shapes.
- Keep the current database tables, columns, relationships, and migration history.
- Do not remove checkpoints, models, research assets, or runtime data needed by the application.
- Do not add credentials, secrets, or production data to Git.
- Make behavior changes only where required to correct verified defects or close a documented security gap.

## Approach

Use an incremental, risk-first refactor. Every correctness or security fix begins with a regression test that demonstrates the original failure. High-risk medical and transaction issues are fixed before validation and cleanup work. Structural extraction is limited to code touched by those fixes or code whose size prevents reliable testing.

This approach is preferred over a broad modular rewrite because the repository starts without an executable test suite. Large-scale movement before characterization would create unnecessary regression risk. It is also preferred over a bug-fix-only patch because the request explicitly includes cleanup, configuration synchronization, and maintainability work.

## Scope

### Transaction and medical correctness

- Make report version allocation and PDF publication safe when two reports are generated concurrently.
- Ensure failed report generation removes only artifacts created by the failing operation.
- Render the stored review author in the PDF instead of the Case's currently assigned doctor.
- Keep binary malignancy probability and multiclass lesion-class probability separate in AI interpretation.
- Preserve a durable FAILED analysis audit record while returning a stable client-safe error.

### Upload and input security

- Separate aggregate request size from the existing per-file size limit.
- Validate decoded image format against the allowed extension and normalize equivalent formats.
- Enforce an image dimension and total-pixel budget before expensive processing.
- Prevent spreadsheet formula execution in generated upload CSV files.
- Clean partial batch artifacts when processing fails.
- Validate top-level JSON types and return JSON client errors instead of HTML 500 responses.
- Add scoped rate limiting for authentication and expensive state-changing endpoints without changing successful payloads.

### Maintainability and performance

- Extract focused helpers for report file publication, upload validation/cleanup, API payload validation, and AI interpretation where the extraction directly supports tests.
- Remove imports, helpers, and direct dependencies only when repository-wide search and executable checks show that they are unused.
- Preserve existing naming at public boundaries; normalize private names when touched.
- Add bounded pagination only if it can preserve the existing response contract. Otherwise document it as a remaining limitation.
- Avoid changing CSS or JavaScript organization unless a change is covered by syntax checks and preserves rendered behavior.

### Configuration and documentation

- Synchronize `requirements.txt` with imports and introduce compatible constraints only where runtime validation is possible.
- Add missing documented environment variables, including the SMTP SSL setting.
- Keep runtime, model, archive, and worktree artifacts out of Git through `.gitignore` without deleting local assets.
- Update README tree, migration head, test instructions, endpoint descriptions, upload limits, and production caveats.
- Verify that Alembic still has one head and that a fresh database upgrades without schema drift. No schema migration is planned.

## Error Handling

Client errors use stable JSON messages and appropriate 4xx statuses. Internal exception text remains in server logs and is not returned to clients. Filesystem operations use request-owned temporary paths and cleanup in `finally` blocks. Database rollback and artifact cleanup are coordinated explicitly because they cannot share one atomic transaction.

## Report Publication Design

Each render writes to an operation-unique temporary file. Version allocation is attempted inside the database transaction. A unique-constraint conflict is retried with a newly computed version. The final path is published by atomic rename only after the database record can be committed safely. Cleanup tracks the temporary file and never unlinks a final file belonging to another request. Tests exercise two concurrent generators and verify that every committed report has a readable file.

## Upload Validation Design

The service decodes the image once for verification, reads the actual Pillow format and dimensions, applies a configurable pixel budget, and maps JPEG/JPG equivalently. Files are written under a batch-owned staging area or tracked immediately so a later failure can clean all partial artifacts. CSV text originating from filenames is escaped for spreadsheet consumers.

## AI and Review Design

AI interpretation receives named binary and multiclass values rather than a shared confidence variable. Generated text identifies the source probability explicitly. PDF review sections receive the persisted `DoctorReview` identity. AI failures log the exception, return a generic error code/message, and record FAILED status using a transaction that survives rollback of incomplete result data.

## Testing Strategy

Create a real `tests/` suite with isolated SQLite databases and temporary upload/report directories. Tests must not require production secrets, SMTP delivery, GPU hardware, or absent checkpoints unless explicitly marked as integration tests.

Required regression coverage:

- report generation concurrency and cleanup ownership;
- AI binary/multiclass interpretation;
- ADMIN and DOCTOR review attribution in PDF data;
- aggregate and per-file upload limits;
- decoded image format and pixel-budget validation;
- partial batch cleanup and CSV formula escaping;
- malformed JSON response behavior;
- authorization/IDOR and CSRF smoke coverage;
- AI error response and FAILED audit behavior where model calls can be stubbed;
- fresh Alembic upgrade, single head, and schema drift check.

Verification includes the full pytest suite, Python compilation, JavaScript syntax checks, dependency consistency, migration checks, secret scanning, Git diff review, and a clean worktree after commit.

## Delivery

- Branch: `refactor/clean-code`.
- Commits remain reviewable and may be split by risk area.
- A Pull Request targets `main` and documents behavior changes, verification evidence, and remaining limitations.
- `Project_Clean_Final.zip` is created from tracked source at the final branch commit and excludes `.git`, virtual environments, secrets, runtime databases, uploads, reports, and generated private artifacts.

## Acceptance Criteria

- Regression tests reproduce the verified defects before their fixes and pass afterward.
- The full test suite finishes with zero failures.
- Python, JavaScript, dependency, and migration checks pass.
- No API route or successful response contract changes unintentionally.
- Database schema and migration head remain unchanged.
- No secret or private runtime data enters the commit or ZIP.
- The final branch is pushed and a Pull Request is created against `main`.
