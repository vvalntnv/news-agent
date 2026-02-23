from bs4 import Tag


def get_string_from_tag_attribute(tag: Tag, attribute_name: str) -> str | None:
    attribute_value = tag.get(attribute_name)
    return get_string_from_attribute_value(attribute_value)


def get_string_from_attribute_value(
    attribute_value: object | list[str] | None,
) -> str | None:
    if isinstance(attribute_value, str):
        cleaned_value = attribute_value.strip()
        return cleaned_value or None

    if isinstance(attribute_value, list):
        for entry in attribute_value:
            if isinstance(entry, str):
                cleaned_entry = entry.strip()
                if cleaned_entry:
                    return cleaned_entry

    return None
