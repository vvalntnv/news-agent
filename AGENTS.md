# Project Rules & Guidelines

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
