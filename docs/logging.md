# Logging architecture

This document describes the current logger implementation and configuration.

## Logger types

The project defines three dedicated loggers:

- AI logger: `news_agent.ai`
- Code logger: `news_agent.code`
- HTTP logger: `news_agent.http`

Each logger is configured independently and writes to a dedicated output target.

## Module layout

Logger modules are split by responsibility in `backend/core/loggers/`:

- `ai.py`: `get_ai_logger()`
- `code.py`: `get_code_logger()`
- `http.py`: `get_http_logger()`
- `base.py`: shared configuration and handler wiring
- `__init__.py`: exports the logger accessors and `configure_project_loggers()`

## Environment variables

Configured through `backend/core/config.py` (`Config`):

- `OUTPUT_LOGS`
  - `TERM` or unset: log to stdout
  - directory path: log to separate files under that directory
- `LOG_LEVEL`
  - global fallback log level
- `LOG_LEVEL_AI`
  - AI logger override
- `LOG_LEVEL_CODE`
  - code logger override
- `LOG_LEVEL_HTTP`
  - HTTP logger override

Level precedence:

1. specific logger level (for example `LOG_LEVEL_AI`)
2. `LOG_LEVEL`
3. default `INFO`

## Output behavior

When `OUTPUT_LOGS` points to a directory, the logger output is split into:

- `ai.log`
- `code.log`
- `http.log`

When `OUTPUT_LOGS` is unset or set to `TERM`, all logger output is emitted to stdout.

## AI event interception

AI event logging is implemented in `backend/infrastructure/ai/event_logger.py`.

`ProjectPydanticAgent` always attaches AI event interception:

- `run()` uses `run_stream_events(...)` and logs each event
- `stream()` uses `run_stream(..., event_stream_handler=...)`

This keeps event logging mandatory for that agent wrapper without requiring caller-side setup.
