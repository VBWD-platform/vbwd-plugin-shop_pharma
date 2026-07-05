"""Field-set seeder (S101.1) — register the S77 custom-field SET (D3).

Seeds the pharma ``custom_field_defs`` on ``entity_type=shop_product`` once,
idempotently. NO new table and NO migration — S77's tables already exist; this
only inserts def rows (and updates options if they drift). Runs from
``on_enable`` (and ``populate_db``).
"""
from __future__ import annotations

from plugins.shop_pharma.shop_pharma.domain import (
    PHARMA_ENTITY_TYPE,
    PHARMA_FIELD_DEFS,
)


def seed_pharma_field_set(custom_field_service) -> int:
    """Create any missing pharma defs; update options if they changed.

    Args:
        custom_field_service: a core ``CustomFieldService`` bound to the session.

    Returns:
        The number of defs created (0 on a re-run with no drift).
    """
    created = 0
    existing = {
        definition["key"]: definition
        for definition in custom_field_service.get_field_defs(PHARMA_ENTITY_TYPE)
    }
    for sort_order, field in enumerate(PHARMA_FIELD_DEFS):
        current = existing.get(field["key"])
        if current is None:
            custom_field_service.create_def(
                entity_type=PHARMA_ENTITY_TYPE,
                key=field["key"],
                label=field["label"],
                field_type=field["type"],
                options=field["options"],
                sort_order=sort_order,
            )
            created += 1
        elif field["options"] and current.get("options") != field["options"]:
            # Keep the option vocabulary in sync (e.g. new substances added).
            custom_field_service.update_def(
                PHARMA_ENTITY_TYPE,
                field["key"],
                options=field["options"],
            )
    return created
