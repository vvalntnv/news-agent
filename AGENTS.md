# Project Rules & Guidelines

All of the backend impotrs should happen as backend as the root directory. NO backend.<anything> imports. backend is the ROOT

## 1. Strong Typing
- **No `Any` Types**: Utilization of `Any` is strictly forbidden. All variables, function arguments, and return types must be explicitly typed.
- **Pydantic**: Use Pydantic models for all data validation and serialization.
- **Type Checking**: Code must pass static type checking (e.g., mypy).

## 2. Documentation
- **`docs/` Directory**: All major components, modules, and agents must be documented in the `docs/` directory using Markdown (`.md`) files.
- **Content**: Documentation should explain the purpose, arguments, and return values of functions and classes, as well as the overall flow of the agents.

## 3. Testing
- **Mandatory Tests**: Every new feature, agent, or utility must have accompanying tests.
- **Test Location**: Tests should be located in a `tests/` directory, mirroring the structure of the source code.
- **Framework**: Use `pytest` for all testing needs.

## 4. Code Quality
- Follow PEP 8 style guidelines.
- Keep functions small and focused on a single task.

## 5. Configuration
- Any behavior that users/operators might want to tune must be exposed via
  `backend/core/config.py` (and environment variables through that config).
- Avoid hardcoded operational values in services/resolvers/muxers/downloaders
  when they can be configurable.

---

# Agent Operational Guide (Expanded)

This extends the original rules above and reflects the current repository state.
Preserve the original rules as hard constraints.

## Repo Layout
- Backend code: `backend/`
- App orchestration: `backend/application/`
- Domain contracts/models: `backend/domain/`
- Infrastructure adapters: `backend/infrastructure/`
- Shared config/errors/utils: `backend/core/`
- Tests: `backend/tests/`
- Documentation: `docs/`

## Import Root Rule (Critical)
- Treat `backend/` as the Python import root when running commands.
- Use imports like `from application...`, `from domain...`, `from core...`.
- Do not use `backend.<...>` imports.
- Run commands from `backend/` unless specifically noted otherwise.

## Runtime and Dependencies
- Python version: `>=3.13` (`backend/pyproject.toml`).
- Dependency/runtime tool: `uv` (`backend/uv.lock` is committed).
- Core stack includes FastAPI, Tortoise ORM, Aerich, pydantic, httpx, pytest.
- `ffmpeg` must exist in `PATH` for media muxing flows.

## Build, Lint, Test Commands
Run these from `backend/`.

### Install / Sync
- `uv sync`
- `uv sync --dev`

### Build
- There is no separate artifact build pipeline right now.
- Use this quality gate sequence as the effective build check:
  1) `uv run pytest`
  2) `uvx ruff check .`
  3) `uvx mypy .`

### Test (full)
- `uv run pytest`
- `uv run pytest -q`

### Test (single test) - key commands
- Single file:
  - `uv run pytest tests/test_rss_source.py`
- Single test function by node id:
  - `uv run pytest tests/test_rss_source.py::test_rss_source_parses_entries`
- Single class method by node id:
  - `uv run pytest tests/test_html_extractor.py::TestHtmlExtractor::test_extract_success`
- By test name pattern:
  - `uv run pytest -k media_download_handler`
- Stop at first failure:
  - `uv run pytest -x`

### Lint / Format / Types
- Lint: `uvx ruff check .`
- Format: `uvx ruff format .`
- Type-check: `uvx mypy .`
- Note: if official project-specific config is added later, prefer that command.

### Migrations (when schema changes)
- Apply migrations: `uv run aerich upgrade`
- Create migration: `uv run aerich migrate --name <short_description>`

## Testing Conventions
- Add or update tests for every behavior change.
- Mirror source structure under `backend/tests/`.
- Async tests generally use `pytest.mark.anyio` in this repo.
- Prefer deterministic unit tests; keep network-dependent tests skipped unless needed.
- For bug fixes, include a regression test that fails before the fix.

## Code Style Guidelines

### Imports
- Group imports as: standard library, third-party, first-party.
- Keep first-party imports rooted at backend packages (`application`, `core`, etc.).
- Avoid circular imports; move shared contracts into `domain/` when needed.

### Formatting
- Follow PEP 8 and existing repository formatting style.
- Keep functions short, clear, and single-purpose.
- Avoid unused imports, commented-out blocks, and stray debug statements.

### Types
- No `Any`.
- Type all function signatures and key locals.
- Prefer modern typing syntax: `list[str]`, `dict[str, str]`, `X | None`.
- Use Pydantic models for validated boundary data and payloads.

### Naming
- Files/modules: `snake_case.py`
- Classes/exceptions: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Tests: `test_*.py` and `test_*` function names
- Internal helpers: `_leading_underscore` where appropriate

### Error Handling
- Use typed custom exceptions instead of raw `Exception` where feasible.
- Use `ClientError` for client-visible HTTP errors.
- Use `InternalError` for internal failures with sanitized public payloads.
- Build errors with `ErrorPayload(code, message, details)`.
- Register/keep FastAPI handlers via `application/error_handlers.py`.
- Log internal details safely; do not expose secrets or internals to clients.

### Configuration
- Route tunable behavior through `backend/core/config.py`.
- Prefer environment-backed settings (`BaseSettings`) for operational values.
- Avoid hardcoding paths/timeouts/codec/thread/network values if configurable.

### Async and I/O
- Keep network/subprocess operations async on hot paths.
- Set explicit timeout/redirect/header behavior for HTTP clients.
- Close async clients/subprocess resources correctly.

## Documentation Rules
- Keep `docs/` updated for major component or behavior changes.
- Document purpose, interfaces, return values, and flow.
- Ensure docs and implementation stay aligned (especially media/error flows).

## Security and Hygiene
- Never commit secrets or `.env` values.
- Avoid logging credentials/tokens/sensitive payloads.
- Validate external URLs and file paths before processing.

## Cursor / Copilot Rules Check
- `.cursorrules`: not found.
- `.cursor/rules/`: not found.
- `.github/copilot-instructions.md`: not found.

If any of these rule files are added later, merge their guidance into this file
without removing existing guidance.
