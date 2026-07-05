"""S101.1 — the catalogue loads custom fields via the BULK port (no N+1, D6).

Asserts that listing a segment of N products issues a BOUNDED number of
custom-field value queries (one bulk ``WHERE entity_id IN (...)`` per segment),
not one-per-product.
"""
from uuid import uuid4

import pytest

from plugins.shop_pharma.shop_pharma.domain import (
    PHARMA_ENTITY_TYPE,
    category_slug_for_class,
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


@pytest.fixture(autouse=True)
def _seed(db):
    from plugins.shop.shop.models.product_category import ProductCategory
    from plugins.shop_pharma.shop_pharma.domain import CLASS_CATEGORY

    seed_pharma_field_set(_custom_field_service(db))
    for mapping in CLASS_CATEGORY.values():
        if (
            db.session.query(ProductCategory).filter_by(slug=mapping["slug"]).first()
            is None
        ):
            db.session.add(ProductCategory(name=mapping["name"], slug=mapping["slug"]))
    db.session.commit()


def _seed_products(db, count):
    from plugins.shop.shop.models.product import Product
    from plugins.shop.shop.models.product_category import ProductCategory

    category = (
        db.session.query(ProductCategory)
        .filter_by(slug=category_slug_for_class("OTC"))
        .first()
    )
    service = _custom_field_service(db)
    for index in range(count):
        product = Product(
            id=uuid4(),
            name=f"OTC {index}",
            slug=f"otc-bulk-{uuid4().hex[:8]}",
            price=4.0,
            is_active=True,
        )
        product.categories = [category]
        db.session.add(product)
        db.session.commit()
        service.set_custom_fields(
            PHARMA_ENTITY_TYPE,
            product.id,
            {"product_class": "OTC", "active_substances": ["ibuprofen"]},
        )


def test_catalogue_uses_bulk_custom_field_load(db):
    """A page of N products must NOT issue N per-product custom-field queries."""
    from unittest.mock import MagicMock

    from plugins.shop.shop.repositories.product_repository import ProductRepository
    from plugins.shop.shop.repositories.product_variant_repository import (
        ProductVariantRepository,
    )
    from plugins.shop_pharma.shop_pharma.services.pharma_service import PharmaService

    _seed_products(db, 5)

    bulk_spy = MagicMock(wraps=_custom_field_service(db).get_custom_fields_bulk)
    by_id_spy = MagicMock(wraps=_custom_field_service(db).get_custom_fields)
    port = MagicMock()
    port.get_custom_fields_bulk.side_effect = bulk_spy
    port.get_custom_fields.side_effect = by_id_spy

    service = PharmaService(
        ProductRepository(db.session),
        ProductVariantRepository(db.session),
        port,
    )
    service.get_catalogue_segments(page=1, per_page=20)

    # One bulk call per non-empty segment; ZERO per-product by-id calls.
    assert by_id_spy.call_count == 0
    assert bulk_spy.call_count >= 1
