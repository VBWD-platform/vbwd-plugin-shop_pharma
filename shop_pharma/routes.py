"""Pharma module routes (S101.1) — public storefront + admin management.

Public:  GET /api/v1/pharma/catalogue            (class-segmented, region-aware)
         GET /api/v1/pharma/products/<slug>       (product + PharmaProfile + variants)
         GET /api/v1/pharma/region                (active-region summary)
Admin:   GET|POST          /api/v1/admin/pharma/products
         GET|PUT|DELETE    /api/v1/admin/pharma/products/<id>   (perm pharma.manage)

The blueprint has no url_prefix; routes carry absolute paths (public + admin).
"""
from flask import Blueprint, current_app, jsonify, request

from vbwd.middleware.auth import require_auth, require_admin, require_permission
from vbwd.services.tags_and_custom_fields import resolve_tags_and_custom_fields

pharma_bp = Blueprint("shop_pharma", __name__)

PHARMA_MANAGE_PERMISSION = "pharma.manage"


def _custom_fields_port():
    return resolve_tags_and_custom_fields()


def _pharma_service():
    from vbwd.extensions import db
    from plugins.shop.shop.repositories.product_repository import ProductRepository
    from plugins.shop.shop.repositories.product_variant_repository import (
        ProductVariantRepository,
    )
    from plugins.shop_pharma.shop_pharma.services.pharma_service import PharmaService

    return PharmaService(
        ProductRepository(db.session),
        ProductVariantRepository(db.session),
        _custom_fields_port(),
    )


def _region_service():
    from plugins.shop_pharma.shop_pharma.services.region_service import RegionService
    from plugins.shop_pharma import get_active_region_code

    return RegionService(get_active_region_code())


def _admin_service():
    from vbwd.extensions import db
    from plugins.shop.shop.repositories.product_repository import ProductRepository
    from plugins.shop.shop.repositories.product_category_repository import (
        ProductCategoryRepository,
    )
    from plugins.shop.shop.repositories.product_variant_repository import (
        ProductVariantRepository,
    )
    from plugins.shop.shop.services.product_variant_service import (
        ProductVariantService,
    )
    from plugins.shop_pharma.shop_pharma.services.pharma_admin_service import (
        PharmaAdminService,
    )

    variant_service = ProductVariantService(
        ProductVariantRepository(db.session),
        current_app.container.price_factory(),
    )
    return PharmaAdminService(
        ProductRepository(db.session),
        ProductCategoryRepository(db.session),
        variant_service,
        _custom_fields_port(),
    )


# ── Public ────────────────────────────────────────────────────────────────


@pharma_bp.route("/api/v1/pharma/catalogue", methods=["GET"])
def pharma_catalogue():
    """Class-segmented, region-aware catalogue (segment by category, no N+1)."""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    segments = _pharma_service().get_catalogue_segments(page, per_page)
    region = _region_service().get_active_region()
    return jsonify({"segments": segments, "region": region}), 200


@pharma_bp.route("/api/v1/pharma/products/<slug>", methods=["GET"])
def pharma_product_detail(slug):
    """A product + its PharmaProfile VO + variants."""
    payload = _pharma_service().get_product_detail(slug)
    if payload is None:
        return jsonify({"error": "Product not found"}), 404
    payload["region"] = _region_service().get_active_region()
    return jsonify({"product": payload}), 200


@pharma_bp.route("/api/v1/pharma/region", methods=["GET"])
def pharma_region():
    """The active-region compliance summary."""
    from plugins.shop_pharma.shop_pharma.services.region_service import (
        UnknownRegionError,
    )

    try:
        region = _region_service().get_active_region()
    except UnknownRegionError as error:
        return jsonify({"error": str(error)}), 404
    return jsonify({"region": region}), 200


# ── Admin ─────────────────────────────────────────────────────────────────


@pharma_bp.route("/api/v1/admin/pharma/products", methods=["GET"])
@require_auth
@require_admin
@require_permission(PHARMA_MANAGE_PERMISSION)
def admin_list_pharma_products():
    """List pharma products across all class categories."""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    segments = _pharma_service().get_catalogue_segments(page, per_page)
    products = [product for segment in segments for product in segment["products"]]
    return jsonify({"products": products}), 200


@pharma_bp.route("/api/v1/admin/pharma/products", methods=["POST"])
@require_auth
@require_admin
@require_permission(PHARMA_MANAGE_PERMISSION)
def admin_create_pharma_product():
    """Create a medicine/device (shop product + variants + S77 profile)."""
    from plugins.shop_pharma.shop_pharma.required_fields import (
        RequiredFieldsValidationError,
    )

    data = request.get_json() or {}
    try:
        payload = _admin_service().create_product(data)
    except RequiredFieldsValidationError as error:
        return jsonify({"error": str(error), "missing": error.missing}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"product": payload}), 201


@pharma_bp.route("/api/v1/admin/pharma/products/<product_id>", methods=["GET"])
@require_auth
@require_admin
@require_permission(PHARMA_MANAGE_PERMISSION)
def admin_get_pharma_product(product_id):
    """A single pharma product with its profile + variants."""
    from vbwd.extensions import db
    from plugins.shop.shop.repositories.product_repository import ProductRepository

    product = ProductRepository(db.session).find_by_id(product_id)
    if product is None:
        return jsonify({"error": "Product not found"}), 404
    payload = _pharma_service().get_product_detail(product.slug)
    return jsonify({"product": payload}), 200


@pharma_bp.route("/api/v1/admin/pharma/products/<product_id>", methods=["PUT"])
@require_auth
@require_admin
@require_permission(PHARMA_MANAGE_PERMISSION)
def admin_update_pharma_product(product_id):
    """Update a pharma product's commerce fields + S77 profile."""
    from plugins.shop_pharma.shop_pharma.required_fields import (
        RequiredFieldsValidationError,
    )
    from plugins.shop_pharma.shop_pharma.services.pharma_admin_service import (
        PharmaProductNotFoundError,
    )

    data = request.get_json() or {}
    try:
        payload = _admin_service().update_product(product_id, data)
    except PharmaProductNotFoundError:
        return jsonify({"error": "Product not found"}), 404
    except RequiredFieldsValidationError as error:
        return jsonify({"error": str(error), "missing": error.missing}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"product": payload}), 200


@pharma_bp.route("/api/v1/admin/pharma/products/<product_id>", methods=["DELETE"])
@require_auth
@require_admin
@require_permission(PHARMA_MANAGE_PERMISSION)
def admin_delete_pharma_product(product_id):
    """Delete a pharma product (cascades to shop variants/images/stock)."""
    from plugins.shop_pharma.shop_pharma.services.pharma_admin_service import (
        PharmaProductNotFoundError,
    )

    try:
        _admin_service().delete_product(product_id)
    except PharmaProductNotFoundError:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"message": "Product deleted"}), 200
