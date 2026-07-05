"""PharmaService (S101.1) — catalogue + profile assembly over shop products.

Reuses shop's commerce engine (products / variants / categories) and the core
S77 port for the regulated fields. Reads are by-id / bulk only (D5/D6):
- the catalogue segments by CATEGORY (indexed FK) — never by EAV value;
- list pages load custom fields via the BULK port (no N+1);
- detail assembles a single ``PharmaProfile`` VO from a by-id custom-field read.

The service holds no shop/core models directly beyond what shop's repositories
return — it depends on the abstractions (shop repos via the container, the S77
port).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from plugins.shop_pharma.shop_pharma.domain import (
    CLASS_CATEGORY,
    PHARMA_ENTITY_TYPE,
    PRODUCT_CLASSES,
)
from plugins.shop_pharma.shop_pharma.profile import PharmaProfile


class PharmaService:
    """Assemble the pharmacy catalogue + product profile read models."""

    def __init__(self, product_repository, variant_repository, custom_fields_port):
        """Initialize the service.

        Args:
            product_repository: shop ``ProductRepository``.
            variant_repository: shop ``ProductVariantRepository``.
            custom_fields_port: the core S77 ``ITagsAndCustomFields`` port.
        """
        self._product_repository = product_repository
        self._variant_repository = variant_repository
        self._custom_fields = custom_fields_port

    # --- catalogue (segment by category, bulk custom-field load) ---
    def get_catalogue_segments(
        self, page: int = 1, per_page: int = 20
    ) -> List[Dict[str, Any]]:
        """The class-segmented catalogue: one segment per class/category.

        Each segment lists its products with the bulk-loaded ``PharmaProfile``
        (one ``WHERE entity_id IN (...)`` per segment — no N+1, D6).
        """
        segments = []
        for product_class in PRODUCT_CLASSES:
            category = CLASS_CATEGORY[product_class]
            products = self._product_repository.find_by_category_slug(
                category["slug"], page, per_page
            )
            profiles = self._bulk_profiles([product.id for product in products])
            segments.append(
                {
                    "product_class": product_class,
                    "category_slug": category["slug"],
                    "category_name": category["name"],
                    "products": [
                        self._catalogue_entry(product, profiles.get(product.id))
                        for product in products
                    ],
                }
            )
        return segments

    def get_product_detail(self, slug: str) -> Optional[Dict[str, Any]]:
        """A product + its ``PharmaProfile`` VO + its variants (by-id reads)."""
        product = self._product_repository.find_by_slug(slug)
        if product is None:
            return None
        profile = self.get_profile(product.id)
        variants = self._variant_repository.list_for_product(product.id)
        payload = product.to_dict()
        payload["pharma_profile"] = profile.to_dict()
        payload["variants"] = [variant.to_dict() for variant in variants]
        return payload

    def get_profile(self, product_id: UUID) -> PharmaProfile:
        """Assemble the ``PharmaProfile`` VO from a by-id custom-field read."""
        values = self._custom_fields.get_custom_fields(PHARMA_ENTITY_TYPE, product_id)
        return PharmaProfile.from_custom_fields(values)

    # --- internals ---
    def _bulk_profiles(self, product_ids: List[UUID]) -> Dict[UUID, PharmaProfile]:
        if not product_ids:
            return {}
        bulk = self._custom_fields.get_custom_fields_bulk(
            PHARMA_ENTITY_TYPE, product_ids
        )
        return {
            product_id: PharmaProfile.from_custom_fields(bulk.get(product_id, {}))
            for product_id in product_ids
        }

    @staticmethod
    def _catalogue_entry(product, profile: Optional[PharmaProfile]) -> Dict[str, Any]:
        entry = {
            "id": str(product.id),
            "name": product.name,
            "slug": product.slug,
            "primary_image_url": product.primary_image_url,
            "price": product.raw_price,
        }
        entry["pharma_profile"] = (
            profile.to_dict() if profile is not None else PharmaProfile().to_dict()
        )
        return entry
