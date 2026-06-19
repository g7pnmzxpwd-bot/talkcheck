"""Korean business registration number helpers."""

from __future__ import annotations

import re


def normalize_business_number(value: str) -> str:
    return "".join(character for character in str(value) if character.isdigit())


def is_valid_business_number(value: str) -> bool:
    number = normalize_business_number(value)
    if len(number) != 10:
        return False

    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    total = sum(int(number[index]) * weights[index] for index in range(8))
    ninth = int(number[8]) * 5
    total += ninth // 10 + ninth % 10
    check_digit = (10 - total % 10) % 10
    return check_digit == int(number[9])


def format_business_number(value: str) -> str:
    number = normalize_business_number(value)
    if len(number) != 10:
        return number
    return f"{number[:3]}-{number[3:5]}-{number[5:]}"


def find_business_number(text: str) -> str | None:
    match = re.search(r"(?<!\d)(\d{3})[-\s]?(\d{2})[-\s]?(\d{5})(?!\d)", text)
    if not match:
        return None
    return "".join(match.groups())

