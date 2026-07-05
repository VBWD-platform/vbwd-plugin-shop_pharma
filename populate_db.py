"""shop_pharma demo data (S101.1) — idempotent, upsert by slug/sku.

Seeds the 5-class demo pharmacy catalogue THROUGH services/repositories (never
raw SQL): the S77 field set + class categories + shop products + pack variants +
per-variant warehouse stock + S77 profile values + a gallery image per product
(imported via the cms ``CmsImageService`` and linked to the product). Re-runs do
not duplicate.

Run standalone:  python plugins/shop_pharma/populate_db.py
"""
import logging
from uuid import uuid4

from plugins.shop_pharma.shop_pharma.domain import (
    CLASS_CATEGORY,
    PHARMA_ENTITY_TYPE,
    category_slug_for_class,
)
from plugins.shop_pharma.shop_pharma.seed_data import all_products

logger = logging.getLogger(__name__)


def populate(app=None):
    """Idempotently seed the demo pharmacy catalogue."""
    from vbwd.extensions import db

    _ensure_entity_type()
    _seed_field_set(db.session)
    _seed_categories(db.session)
    warehouse = _ensure_warehouse(db.session)

    summary = {"products": 0, "variants": 0, "images": 0}
    image_service = _build_image_service()
    for product_data in all_products():
        result = _upsert_product(db.session, warehouse, product_data, image_service)
        summary["products"] += result["product"]
        summary["variants"] += result["variants"]
        summary["images"] += result["images"]
    logger.info("[shop_pharma] seed summary: %s", summary)
    return summary


# --- foundations ---
def _ensure_entity_type():
    from vbwd.services.entity_type_registry import (
        EntityTypeRegistration,
        register_entity_type,
    )

    register_entity_type(
        EntityTypeRegistration(PHARMA_ENTITY_TYPE, "Product", "shop.products.manage")
    )


def _custom_field_service(session):
    from vbwd.repositories.custom_field_def_repository import CustomFieldDefRepository
    from vbwd.repositories.custom_field_value_repository import (
        CustomFieldValueRepository,
    )
    from vbwd.services.custom_field_service import CustomFieldService

    return CustomFieldService(
        def_repo=CustomFieldDefRepository(session),
        value_repo=CustomFieldValueRepository(session),
    )


def _seed_field_set(session):
    from plugins.shop_pharma.shop_pharma.services.field_set_seeder import (
        seed_pharma_field_set,
    )

    seed_pharma_field_set(_custom_field_service(session))


def _seed_categories(session):
    from plugins.shop.shop.models.product_category import ProductCategory

    for mapping in CLASS_CATEGORY.values():
        existing = (
            session.query(ProductCategory).filter_by(slug=mapping["slug"]).first()
        )
        if existing is None:
            session.add(ProductCategory(name=mapping["name"], slug=mapping["slug"]))
    session.commit()


def _ensure_warehouse(session):
    from plugins.shop.shop.models.warehouse import Warehouse

    warehouse = session.query(Warehouse).filter_by(slug="main-warehouse").first()
    if warehouse is None:
        warehouse = Warehouse(
            id=uuid4(),
            name="Main Warehouse",
            slug="main-warehouse",
            is_active=True,
            is_default=True,
        )
        session.add(warehouse)
        session.commit()
    return warehouse


# --- per-product upsert ---
def _upsert_product(session, warehouse, product_data, image_service):
    from plugins.shop.shop.models.product import Product
    from plugins.shop.shop.models.product_category import ProductCategory
    from plugins.shop.shop.models.product_variant import ProductVariant
    from plugins.shop.shop.models.warehouse_stock import WarehouseStock

    result = {"product": 0, "variants": 0, "images": 0}
    slug = product_data["slug"]
    product = session.query(Product).filter_by(slug=slug).first()
    if product is None:
        product = Product(
            id=uuid4(),
            name=product_data["name"],
            slug=slug,
            price=float(product_data["variants"][0]["price"]),
            tax_class=product_data.get("tax_class", "standard"),
            has_variants=True,
            is_active=True,
        )
        session.add(product)
        session.flush()
        result["product"] = 1

    # Link to the class category.
    category_slug = category_slug_for_class(product_data["product_class"])
    category = (
        session.query(ProductCategory).filter_by(slug=category_slug).first()
        if category_slug
        else None
    )
    if category is not None and category not in (product.categories or []):
        product.categories = list(product.categories or []) + [category]

    # Variants + per-variant stock (upsert by sku).
    for variant_data in product_data["variants"]:
        variant = (
            session.query(ProductVariant).filter_by(sku=variant_data["sku"]).first()
        )
        if variant is None:
            variant = ProductVariant(
                id=uuid4(),
                product_id=product.id,
                name=variant_data["name"],
                sku=variant_data["sku"],
                price=variant_data["price"],
                price_float=float(variant_data["price"]),
                attributes=variant_data.get("attributes", {}),
                is_active=True,
            )
            session.add(variant)
            session.flush()
            result["variants"] += 1
            existing_stock = (
                session.query(WarehouseStock)
                .filter_by(
                    warehouse_id=warehouse.id,
                    product_id=product.id,
                    variant_id=variant.id,
                )
                .first()
            )
            if existing_stock is None:
                session.add(
                    WarehouseStock(
                        id=uuid4(),
                        warehouse_id=warehouse.id,
                        product_id=product.id,
                        variant_id=variant.id,
                        quantity=variant_data.get("stock", 0),
                    )
                )

    session.commit()

    # S77 profile values (idempotent set).
    _custom_field_service(session).set_custom_fields(
        PHARMA_ENTITY_TYPE, product.id, dict(product_data["pharma_profile"])
    )

    # Gallery image (imported via cms; linked to the product).
    if image_service is not None and not product.images:
        if _attach_gallery_image(session, product, product_data, image_service):
            result["images"] = 1

    return result


# --- image gallery import (proves the cms gallery path end to end) ---
def _build_image_service():
    """A cms ``CmsImageService`` bound to the configured filesystem, or None.

    Returns ``None`` when cms is unavailable so the seeder still runs the
    commerce + profile path (the image step is best-effort).
    """
    try:
        from flask import current_app
        from vbwd.extensions import db
        from vbwd.interfaces.file_storage import ManagerBackedFileStorage
        from plugins.cms.src.repositories.cms_image_repository import (
            CmsImageRepository,
        )
        from plugins.cms.src.services.cms_image_service import CmsImageService

        storage = ManagerBackedFileStorage(current_app.container.filesystem_manager())
        return CmsImageService(CmsImageRepository(db.session), storage)
    except Exception as error:
        logger.warning("[shop_pharma] cms image service unavailable: %s", error)
        return None


# A 1x1 transparent PNG — the placeholder used when no real image can be
# fetched in this environment (proves the gallery-import wiring, not the asset).
_PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _fetch_image_bytes(product_data):
    """Try a placeholder web image; fall back to a bundled 1x1 PNG.

    Real CC0/Wikimedia asset curation is operator-side; in this environment we
    use placehold.co (text placeholder) when reachable, else the bundled PNG.
    Returns ``(bytes, mime, is_placeholder)``.
    """
    label = product_data["image_hint"].replace(" ", "+")
    url = f"https://placehold.co/400x400?text={label}"
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=4) as response:
            data = response.read()
            if data:
                return data, "image/png", True
    except Exception as error:
        logger.info("[shop_pharma] placeholder fetch failed (%s); using 1x1 PNG", error)
    return _PLACEHOLDER_PNG, "image/png", True


def _attach_gallery_image(session, product, product_data, image_service):
    from plugins.shop.shop.models.product_image import ProductImage

    try:
        data, mime, _is_placeholder = _fetch_image_bytes(product_data)
        uploaded = image_service.upload_image(
            file_data=data,
            filename=f"{product_data['slug']}.png",
            mime_type=mime,
            caption=product_data["name"],
        )
        session.add(
            ProductImage(
                id=uuid4(),
                product_id=product.id,
                url=uploaded.get("url_path") or uploaded.get("url", ""),
                alt=product_data["name"],
                is_primary=True,
            )
        )
        # Keep the cms_image id on the product metadata for traceability.
        metadata = dict(product.product_metadata or {})
        metadata["cms_image_id"] = uploaded.get("id")
        product.product_metadata = metadata
        session.commit()
        return True
    except Exception as error:
        session.rollback()
        logger.warning("[shop_pharma] gallery image import failed: %s", error)
        return False


if __name__ == "__main__":
    from vbwd.app import create_app

    application = create_app()
    with application.app_context():
        populate(application)
