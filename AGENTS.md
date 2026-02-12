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
- When doing complex checks with if, or while or whatever, always use variables to make the check more meaningful. Rather than complex checks like age < 18 and age >= 60, use is_underaged = age < 18 and is_senior = age >=60, for example, and then if is_underaged and not is_seniod: ... That way the checks get super readable.
