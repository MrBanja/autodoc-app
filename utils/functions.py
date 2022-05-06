from enum import EnumMeta
from typing import TypeVar

_T = TypeVar('_T')


def get_all_enum_values(
        enum: EnumMeta,
        except_values: set[_T, ...] | None = None,
        extra_values: set[_T, ...] | None = None
) -> list[_T]:
    value_map = map(lambda x: getattr(x, 'value'), enum.__members__.values())
    accepted: list[_T] = list(value_map)

    if extra_values:
        accepted.extend(extra_values)
    if not except_values:
        return accepted

    new_accepted: list[_T] = []
    for key in accepted:
        if key not in except_values:
            new_accepted.append(key)

    return new_accepted
