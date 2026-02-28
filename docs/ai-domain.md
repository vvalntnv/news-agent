# AI domain contracts

These domain contracts describe the shape of the AI layer that powers agents across the application.

## Agent protocol

The `Agent` protocol defines the minimal async surface that every AI-backed actor must expose. Implementations call `respond` with a natural language prompt plus sampling hints and always return the textual reply.

```
async def respond(
    prompt: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    stop_sequences: list[str] | None = None,
) -> str
```

## AIConfiguration

`AIConfiguration` is a Pydantic model that captures the tunable knobs for any AI provider. Every field has an explicit type, uses sane defaults, and forbids unexpected keys:

- `model_name`: required provider model identifier
- `provider_name`: optional provider nickname for telemetry
- `api_base_url`, `api_key`, `api_version`: optional connection metadata
- `temperature`, `top_p`, `max_tokens`, `timeout_seconds`, `stop_sequences`: sampling and safety controls with validation
- `metadata`: freeform string dictionary to persist provider-specific tags

## AIFactory

The `AIFactory` protocol lets the application instantiate concrete agents from configuration.

```
def create_agent(self, config: AIConfiguration) -> Agent
```

Every implementation can keep provider-specific wiring isolated while the rest of the code interacts with the `Agent` and configuration contracts.
