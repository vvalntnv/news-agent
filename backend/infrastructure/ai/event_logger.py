from __future__ import annotations

import logging
from collections.abc import AsyncIterable, Awaitable, Callable

from pydantic_ai import (
    AgentRunResultEvent,
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartEndEvent,
    PartStartEvent,
    RunContext,
)

from core.loggers import get_ai_logger

type AIEventStreamHandler[DepsT] = Callable[
    [RunContext[DepsT], AsyncIterable[AgentStreamEvent]], Awaitable[None]
]


def build_ai_event_stream_handler[DepsT](
    logger: logging.Logger | None = None,
) -> AIEventStreamHandler[DepsT]:
    resolved_logger = logger or get_ai_logger()

    async def handle_ai_event_stream(
        _context: RunContext[DepsT],
        event_stream: AsyncIterable[AgentStreamEvent],
    ) -> None:
        _ = _context
        async for event in event_stream:
            log_ai_event(event=event, logger=resolved_logger)

    return handle_ai_event_stream


async def consume_ai_run_events[OutputT](
    run_events: AsyncIterable[AgentStreamEvent | AgentRunResultEvent[OutputT]],
    logger: logging.Logger | None = None,
) -> OutputT:
    resolved_logger = logger or get_ai_logger()

    async for event in run_events:
        log_ai_event(event=event, logger=resolved_logger)
        is_run_result_event = isinstance(event, AgentRunResultEvent)
        if is_run_result_event:
            return event.result.output

    raise RuntimeError("Pydantic AI run stream ended without a final result event")


def log_ai_event(
    event: AgentStreamEvent | AgentRunResultEvent[object],
    logger: logging.Logger | None = None,
) -> None:
    resolved_logger = logger or get_ai_logger()

    if isinstance(event, PartStartEvent):
        resolved_logger.info(
            "ai.part_start index=%s part_type=%s",
            event.index,
            type(event.part).__name__,
        )
        return

    if isinstance(event, PartDeltaEvent):
        resolved_logger.debug(
            "ai.part_delta index=%s delta_type=%s",
            event.index,
            type(event.delta).__name__,
        )
        return

    if isinstance(event, PartEndEvent):
        resolved_logger.info(
            "ai.part_end index=%s part_type=%s",
            event.index,
            type(event.part).__name__,
        )
        return

    if isinstance(event, FunctionToolCallEvent):
        resolved_logger.info(
            "ai.tool_call tool_name=%s tool_call_id=%s",
            event.part.tool_name,
            event.tool_call_id,
        )
        return

    if isinstance(event, FunctionToolResultEvent):
        resolved_logger.info(
            "ai.tool_result tool_call_id=%s result_type=%s",
            event.tool_call_id,
            type(event.result).__name__,
        )
        return

    if isinstance(event, FinalResultEvent):
        resolved_logger.info(
            "ai.final_result tool_name=%s tool_call_id=%s",
            event.tool_name,
            event.tool_call_id,
        )
        return

    if isinstance(event, AgentRunResultEvent):
        resolved_logger.info(
            "ai.run_result output_type=%s",
            type(event.result.output).__name__,
        )
        return

    event_kind = getattr(event, "event_kind", "unknown")
    resolved_logger.debug("ai.event kind=%s data=%s", event_kind, event)
