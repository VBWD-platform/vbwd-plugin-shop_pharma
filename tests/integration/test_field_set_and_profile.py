"""S101.1 — S77 field-set seeds idempotently + profile values round-trip (DB)."""
from uuid import uuid4

from plugins.shop_pharma.shop_pharma.domain import (
    PHARMA_ENTITY_TYPE,
    PHARMA_FIELD_KEYS,
)
from plugins.shop_pharma.shop_pharma.services.field_set_seeder import (
    seed_pharma_field_set,
)


def _custom_field_service(db):
    from vbwd.repositories.custom_field_def_repository import CustomFieldDefRepository
    from vbwd.repositories.custom_field_value_repository import (
        CustomFieldValueRepository,
    )
    from vbwd.services.custom_field_service import CustomFieldService

    return CustomFieldService(
        def_repo=CustomFieldDefRepository(db.session),
        value_repo=CustomFieldValueRepository(db.session),
    )


def test_field_set_seeds_all_keys_idempotently(db):
    service = _custom_field_service(db)
    # Seed (may be a no-op if the plugin already seeded the shared schema on
    # enable — the contract is idempotency, not a specific first-run count).
    seed_pharma_field_set(service)

    defs = {
        definition["key"] for definition in service.get_field_defs(PHARMA_ENTITY_TYPE)
    }
    assert set(PHARMA_FIELD_KEYS) <= defs

    # Re-run creates nothing (idempotent).
    assert seed_pharma_field_set(service) == 0


def test_profile_values_round_trip(db):
    service = _custom_field_service(db)
    seed_pharma_field_set(service)
    product_id = uuid4()

    values = {
        "product_class": "OTC",
        "active_substances": ["ibuprofen"],
        "strength": "400 mg",
        "max_quantity_per_order": 3,
        "professional_only": False,
    }
    service.set_custom_fields(PHARMA_ENTITY_TYPE, product_id, values)

    from plugins.shop_pharma.shop_pharma.profile import PharmaProfile

    stored = service.get_custom_fields(PHARMA_ENTITY_TYPE, product_id)
    profile = PharmaProfile.from_custom_fields(stored)
    assert profile.product_class == "OTC"
    assert profile.active_substances == ["ibuprofen"]
    assert profile.max_quantity_per_order == 3
