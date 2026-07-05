"""S116.4 — the ``medical`` MARKER type is registered on enable and reconciles
into shop's ``shop_product_type`` (coexistence with the S77 ``product_class``
axis; no migration).
"""
from plugins.shop_pharma.shop_pharma.domain import (
    MEDICAL_PRODUCT_TYPE_DESCRIPTOR,
    MEDICAL_PRODUCT_TYPE_SLUG,
)


def test_on_enable_registers_medical_on_the_shop_registry_singleton(db):
    """shop_pharma ``on_enable`` (run at app-fixture setup) registers the marker
    on the module-singleton registry via the seam."""
    from plugins.shop.shop.services.product_type_registry import (
        product_type_registry,
    )

    slugs = [descriptor["slug"] for descriptor in product_type_registry.descriptors()]
    assert MEDICAL_PRODUCT_TYPE_SLUG in slugs


def test_medical_descriptor_reconciles_into_shop_product_type(db):
    """The marker descriptor upserts exactly one empty-cluster row, idempotently."""
    from plugins.shop.shop.repositories.product_type_repository import (
        ProductTypeRepository,
    )
    from plugins.shop.shop.services.product_type_registry import (
        ProductTypeRegistry,
        reconcile_product_types,
    )

    registry = ProductTypeRegistry()
    registry.register(MEDICAL_PRODUCT_TYPE_DESCRIPTOR)

    reconcile_product_types(db.session, registry)
    reconcile_product_types(db.session, registry)

    repository = ProductTypeRepository(db.session)
    rows = [row for row in repository.list_all() if row.slug == MEDICAL_PRODUCT_TYPE_SLUG]
    assert len(rows) == 1
    medical_row = rows[0]
    assert medical_row.source == "plugin"
    assert (medical_row.product_type_fields or []) == []
