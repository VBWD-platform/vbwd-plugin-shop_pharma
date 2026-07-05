"""S101.1 — field-set seeder is idempotent (no migration, D3)."""
from unittest.mock import MagicMock

from plugins.shop_pharma.shop_pharma.domain import PHARMA_FIELD_DEFS
from plugins.shop_pharma.shop_pharma.services.field_set_seeder import (
    seed_pharma_field_set,
)


def test_seeds_all_defs_on_empty():
    service = MagicMock()
    service.get_field_defs.return_value = []
    created = seed_pharma_field_set(service)
    assert created == len(PHARMA_FIELD_DEFS)
    assert service.create_def.call_count == len(PHARMA_FIELD_DEFS)


def test_rerun_creates_nothing():
    service = MagicMock()
    service.get_field_defs.return_value = [
        {"key": field["key"], "options": field["options"]}
        for field in PHARMA_FIELD_DEFS
    ]
    created = seed_pharma_field_set(service)
    assert created == 0
    service.create_def.assert_not_called()
