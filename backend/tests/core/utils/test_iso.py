from core.utils.iso import parse_iso_8601_duration


def test_parse_iso_8601_duration_parses_hours_minutes_seconds() -> None:
    duration_seconds = parse_iso_8601_duration("PT1H2M3S")

    assert duration_seconds == 3723.0


def test_parse_iso_8601_duration_parses_days() -> None:
    duration_seconds = parse_iso_8601_duration("P2DT1H")

    assert duration_seconds == 176400.0


def test_parse_iso_8601_duration_returns_zero_for_invalid_values() -> None:
    duration_seconds = parse_iso_8601_duration("not-a-duration")

    assert duration_seconds == 0.0
