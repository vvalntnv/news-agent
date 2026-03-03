from pydantic_ai import ModelMessage


class BasicHistoryProcessor:
    def __init__(self) -> None:
        pass

    def __call__(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        print("Ima neshto")
        return messages
