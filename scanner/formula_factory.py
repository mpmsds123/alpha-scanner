"""Abstract experiment specifications for three search orders.

The public repository intentionally does not contain production expressions,
field identifiers, region-specific group names, or a reversible copy of the
private template library.  These objects preserve the orchestration boundary:
an adapter may translate an abstract specification into a platform-native job.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Order(int, Enum):
    FIRST = 1
    SECOND = 2
    THIRD = 3


@dataclass(frozen=True)
class FormulaSpec:
    candidate_key: str
    field_key: str
    template_key: str
    order: Order
    parent_key: str | None = None
    wrapper_key: str | None = None


def first_order_specs(field_keys: Iterable[str], template_keys: Iterable[str]) -> list[FormulaSpec]:
    """Create an abstract field-by-template grid."""

    templates = list(template_keys)
    return [
        FormulaSpec(
            candidate_key=f"first:{field}:{template}",
            field_key=field,
            template_key=template,
            order=Order.FIRST,
        )
        for field in field_keys
        for template in templates
    ]


def wrap_specs(parents: Iterable[FormulaSpec], wrapper_keys: Iterable[str], order: Order) -> list[FormulaSpec]:
    """Expand selected parents with abstract second- or third-order wrappers."""

    if order not in (Order.SECOND, Order.THIRD):
        raise ValueError("wrappers are only used for second and third order")
    wrappers = list(wrapper_keys)
    return [
        FormulaSpec(
            candidate_key=f"{order.value}:{parent.candidate_key}:{wrapper}",
            field_key=parent.field_key,
            template_key=parent.template_key,
            order=order,
            parent_key=parent.candidate_key,
            wrapper_key=wrapper,
        )
        for parent in parents
        for wrapper in wrappers
    ]

