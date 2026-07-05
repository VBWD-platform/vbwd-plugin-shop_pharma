"""PharmaAdminService (S101.1) — manage a medicine/device end to end.

One module-owned flow that drives shop's commerce engine + the S77 values:
- create/update the shop ``Product`` (via shop's ``ProductRepository``),
- author its pack ``ProductVariant``s (via shop's ``ProductVariantService`` —
  the S101.0 API),
- map it onto the class category (segment by category, D5),
- write its S77 custom-field values (via the core port),
- enforce the ``RequiredFieldsByClass`` matrix on save (fail-closed).

It never edits shop or core; it composes their public seams.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from plugins.shop_pharma.shop_pharma.domain import (
    MEDICAL_PRODUCT_TYPE_SLUG,
    PHARMA_ENTITY_TYPE,
    PHARMA_FIELD_KEYS,
    category_slug_for_class,
)
from plugins.shop_pharma.shop_pharma.required_fields import RequiredFieldsByClass


class PharmaProductNotFoundError(ValueError):
    """Raised when a pharma product id does not resolve to a shop product."""


class PharmaAdminService:
    """Create / update / delete a pharma product (shop product + profile)."""

    def __init__(
        self,
        product_repository,
        product_category_repository,
        variant_service,
        custom_fields_port,
    ):
        self._product_repository = product_repository
        self._category_repository = product_category_repository
        self._variant_service = variant_service
        self._custom_fields = custom_fields_port

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a shop product + variants + profile (required-fields enforced)."""
        from plugins.shop.shop.models.product import Product

        profile_values = self._extract_profile_values(data)
        RequiredFieldsByClass.validate(
            profile_values.get("product_class"), profile_values
        )

        name = data.get("name")
        if not name:
            raise ValueError("Product name is required")
        slug = data.get("slug") or name.lower().replace(" ", "-")
        if self._product_repository.find_by_slug(slug) is not None:
            raise ValueError(f"Product with slug '{slug}' already exists")

        variants = data.get("variants") or []
        if not variants:
            raise ValueError("At least one pack variant is required")

        product = Product(
            id=uuid4(),
            name=name,
            slug=slug,
            description=data.get("description"),
            sku=data.get("sku"),
            price=float(data.get("price", 0)),
            is_active=data.get("is_active", True),
            has_variants=True,
            tax_class=data.get("tax_class", "standard"),
            # S116.4 — shop-axis MARKER tag; orthogonal to ``product_class``.
            # Empty cluster (``type_field_values`` stays empty) — all pharma
            # data remains in the S77 store.
            product_type_slug=MEDICAL_PRODUCT_TYPE_SLUG,
        )
        self._product_repository.save(product)

        self._assign_class_category(product, profile_values.get("product_class"))
        for variant_data in variants:
            self._variant_service.create_variant(product.id, variant_data)
        self._write_profile(product.id, profile_values)

        return self._serialise(product.id)

    def update_product(self, product_id, data: Dict[str, Any]) -> Dict[str, Any]:
        product = self._require_product(product_id)
        profile_values = self._extract_profile_values(data)

        # The effective class drives the required-set; fall back to the stored one.
        stored = self._custom_fields.get_custom_fields(PHARMA_ENTITY_TYPE, product.id)
        effective_class = profile_values.get(
            "product_class", stored.get("product_class")
        )
        merged = {**stored, **profile_values}
        RequiredFieldsByClass.validate(effective_class, merged)

        for field_name in ("name", "description", "sku", "is_active", "tax_class"):
            if field_name in data:
                setattr(product, field_name, data[field_name])
        if "price" in data:
            product.price = float(data["price"])
        self._product_repository.save(product)

        if "product_class" in profile_values:
            self._assign_class_category(product, profile_values["product_class"])
        if profile_values:
            self._write_profile(product.id, profile_values)
        return self._serialise(product.id)

    def delete_product(self, product_id) -> None:
        product = self._require_product(product_id)
        self._product_repository.delete(product.id)

    # --- internals ---
    def _require_product(self, product_id):
        product = self._product_repository.find_by_id(product_id)
        if product is None:
            raise PharmaProductNotFoundError(f"Product {product_id} not found")
        return product

    @staticmethod
    def _extract_profile_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """Pull the pharma custom-field keys out of the admin payload.

        Accepts either a nested ``pharma_profile`` block or top-level keys.
        """
        source = data.get("pharma_profile")
        if not isinstance(source, dict):
            source = data
        return {key: source[key] for key in PHARMA_FIELD_KEYS if key in source}

    def _write_profile(self, product_id: UUID, values: Dict[str, Any]) -> None:
        if values:
            self._custom_fields.set_custom_fields(
                PHARMA_ENTITY_TYPE, product_id, values
            )

    def _assign_class_category(self, product, product_class: Optional[str]) -> None:
        if not product_class:
            return
        slug = category_slug_for_class(product_class)
        if not slug:
            return
        category = self._category_repository.find_by_slug(slug)
        if category is None:
            return
        existing = {str(cat.id) for cat in (product.categories or [])}
        if str(category.id) not in existing:
            product.categories = list(product.categories or []) + [category]
            self._product_repository.save(product)

    def _serialise(self, product_id: UUID) -> Dict[str, Any]:
        product = self._product_repository.find_by_id(product_id)
        values = self._custom_fields.get_custom_fields(PHARMA_ENTITY_TYPE, product_id)
        variants = self._variant_service.list_variants(product_id)
        payload = product.to_dict()
        payload["pharma_profile"] = values
        payload["variants"] = [variant.to_dict() for variant in variants]
        return payload
