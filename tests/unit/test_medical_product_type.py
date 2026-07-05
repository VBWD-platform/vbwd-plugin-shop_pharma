"""S116.4 — the ``medical`` shop-axis MARKER type (coexistence, not migration).

Pharma keeps its S77 ``product_class`` axis untouched; this sprint ADDS a thin
shop-axis tag. The ``medical`` type is a MARKER — an empty field cluster, all
regulatory data stays in the S77 store.
"""
from plugins.shop_pharma.shop_pharma.domain import (
    MEDICAL_PRODUCT_TYPE_DESCRIPTOR,
    MEDICAL_PRODUCT_TYPE_SLUG,
)


def test_medical_descriptor_is_a_marker_with_empty_cluster():
    assert MEDICAL_PRODUCT_TYPE_SLUG == "medical"
    assert MEDICAL_PRODUCT_TYPE_DESCRIPTOR["slug"] == MEDICAL_PRODUCT_TYPE_SLUG
    # MARKER type — no cluster; pharma data stays in the S77 store.
    assert MEDICAL_PRODUCT_TYPE_DESCRIPTOR["product_type_fields"] == []
    assert MEDICAL_PRODUCT_TYPE_DESCRIPTOR["source"] == "plugin"
    assert MEDICAL_PRODUCT_TYPE_DESCRIPTOR.get("name")


def test_descriptor_registers_into_the_shop_registry_seam():
    from plugins.shop.shop.services.product_type_registry import (
        ProductTypeRegistry,
    )

    registry = ProductTypeRegistry()
    registry.register(MEDICAL_PRODUCT_TYPE_DESCRIPTOR)

    slugs = [descriptor["slug"] for descriptor in registry.descriptors()]
    assert "medical" in slugs
