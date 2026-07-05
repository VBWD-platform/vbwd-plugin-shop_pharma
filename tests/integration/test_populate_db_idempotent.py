"""S101.1 — populate_db seeds the 5-class catalogue idempotently (DB).

Runs the seeder twice and asserts the product/variant counts are identical
(upsert by slug/sku — re-runs do not duplicate) and all 5 classes are present.
Image import is best-effort; this test does not require real assets.
"""
from plugins.shop_pharma.shop_pharma.domain import category_slug_for_class


def _product_count(db):
    from plugins.shop.shop.models.product import Product

    return db.session.query(Product).count()


def _variant_count(db):
    from plugins.shop.shop.models.product_variant import ProductVariant

    return db.session.query(ProductVariant).count()


def test_seeder_is_idempotent_and_covers_all_classes(db):
    from plugins.shop_pharma import populate_db

    first = populate_db.populate()
    products_after_first = _product_count(db)
    variants_after_first = _variant_count(db)
    assert first["products"] == 70

    second = populate_db.populate()
    assert second["products"] == 0  # nothing new
    assert _product_count(db) == products_after_first
    assert _variant_count(db) == variants_after_first

    # All 5 class categories carry products (segment by category, D5).
    from plugins.shop.shop.repositories.product_repository import ProductRepository

    repo = ProductRepository(db.session)
    for product_class in (
        "RX",
        "OTC",
        "MEDICAL_DEVICE",
        "FMCG_PERSONAL",
        "FMCG_HOSPITAL",
    ):
        slug = category_slug_for_class(product_class)
        assert repo.find_by_category_slug(slug, 1, 100), product_class
