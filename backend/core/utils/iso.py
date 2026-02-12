import re

ISO_8601_DURATION_PATTERN = re.compile(
    r"^P"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?"
    r")?$"
)


def parse_iso_8601_duration(duration_value: str) -> float:
    match = ISO_8601_DURATION_PATTERN.match(duration_value)
    if match is None:
        return 0.0

    days = float(match.group("days") or 0)
    hours = float(match.group("hours") or 0)
    minutes = float(match.group("minutes") or 0)
    seconds = float(match.group("seconds") or 0)

    return (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
