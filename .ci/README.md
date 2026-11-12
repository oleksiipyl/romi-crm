# CI-only backend checks

Proposed synthetic GitHub Actions checks for `oleksiipyl/romi-crm`.
This is not production, Railway, PostgreSQL acceptance, or a merge/deploy path.

## Baseline checkpoint before implementation (2026-11-12 05:05 UTC)

This section records the pre-implementation checkpoint, not the current state after this README is created.

Only `.ci/requirements-main.lock` currently exists in the isolated worktree.

The workflow, test wrapper, and this README have not been created.
Dependency installation, tests, secret scan, and CI have not been run.
No commit, push, or draft PR has been completed.

Descriptions below are proposed behavior, not verified implementation results.

## Scope

Only these four files are permitted in the draft:
- `.github/workflows/backend-ci.yml`
- `.ci/requirements-main.lock`
- `.ci/run_backend_checks.py`
- `.ci/README.md`

Application source, existing tests, runtime requirements, Procfile,
migrations, startup, Railway configuration, and the original untracked
prototype WIP must remain unchanged.

## Tool verification

The coordinator independently confirmed these official references:

| Tool | Pin |
| --- | --- |
| `actions/checkout` v4 | `11d5960a326750d5838078e36cf38b85af677262` |
| `actions/setup-python` v5 | `a26af69be951a213d495a4c3e4e4022e16d87065` |
| CPython release | `3.11.18` |

Release existence does not establish dependency compatibility or a passing build.

Proposed scanner: official Gitleaks `v8.24.2`, Linux x64.
Its artifact checksum remains pending independent verification against
the official release checksums. Do not execute the binary before that check.

## Proposed backend checks

Run from `backend/` on a disposable Actions runner:

```text
python -m pip install --require-hashes -r ../.ci/requirements-main.lock
python -m pip check
python -m compileall -q app tests
python ../.ci/run_backend_checks.py
```

Proposed test settings:
- `DATABASE_URL=sqlite://`
- `APP_ENV=test`
- Synthetic placeholder values only where required.
- No production variables or credentials.
- No Alembic, uvicorn, or external services.

The proposed wrapper must install an outbound socket guard before importing
pytest and run the existing `pytest -q tests`.

This guard protects that runner process; it does not establish isolation
of every child process. Wrapper behavior and baseline tests remain unverified.

If the baseline fails or attempts an external call, report the blocker.
Do not alter application tests or weaken the guard to obtain a passing result.

## Proposed secret scan

Scope: files and directories in the checked-out current snapshot.
This does not cover full Git history or prove the absence of historical secrets.

After independently verifying the official scanner artifact checksum,
the proposed command from the checkout root is:

```text
gitleaks dir --redact=100 --exit-code=1 .
```

Gitleaks `git` mode reads Git patches through `git log -p`; it must not
be described as a complete current-files snapshot scan.

Use redacted output only. Do not print secret values or produce raw reports.
No tokens, license keys, verbose secret output, or broad allowlists.

## Workflow requirements and limits

Proposed triggers: `pull_request` and `workflow_dispatch`.
Do not use `pull_request_target`.

Use:
- `permissions: contents: read`
- Checkout `persist-credentials: false`
- Explicit timeout
- Independently verified exact tool pins and dependency hashes
- No deploy jobs or production secrets

SQLite checks are not PostgreSQL acceptance.
Required checks, rulesets, staging, and deployment require separate decisions.

The only intended publication is a draft PR from the isolated CI branch.
Do not merge: a main-branch merge may trigger the existing Railway deployment.
