"""Class-based purchase gate (S101.1, D2) — server-authoritative, fail-closed.

Registered into shop's checkout-validation registry. For each cart line it reads
the product's ``PharmaProfile`` BY ID and applies the class rule:

- RX               -> rejected (``prescription_required``); not dispensed online.
- OTC              -> age + ``max_quantity_per_order`` gates.
- MEDICAL_DEVICE   -> info only; optional age/qty if configured on the product.
- FMCG_PERSONAL    -> free.
- FMCG_HOSPITAL    -> respects ``professional_only`` (rejected for non-pros).

The fe gates are cosmetic; this is the authority. Region defaults fill in caps
the product leaves unset. Returns the first rejection reason, else ``None``.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from plugins.shop_pharma.shop_pharma.domain import (
    PHARMA_ENTITY_TYPE,
    PRODUCT_CLASS_FMCG_HOSPITAL,
    PRODUCT_CLASS_MEDICAL_DEVICE,
    PRODUCT_CLASS_OTC,
    PRODUCT_CLASS_RX,
)
from plugins.shop_pharma.shop_pharma.profile import PharmaProfile

REASON_PRESCRIPTION_REQUIRED = "prescription_required"
REASON_AGE_RESTRICTED = "age_verification_required"
REASON_MAX_QUANTITY = "max_quantity_exceeded"
REASON_PROFESSIONAL_ONLY = "professional_purchase_only"


class PharmaCheckoutGate:
    """Class-based cart gate for the pharma module."""

    def __init__(self, custom_fields_port, region, *, buyer_resolver=None):
        """Initialize the gate.

        Args:
            custom_fields_port: the core S77 port (by-id profile reads).
            region: the active region pack dict (defaults for age/qty caps).
            buyer_resolver: optional callable ``user_id -> {age, is_professional,
                age_verified}`` describing the buyer; defaults to a conservative
                unverified, non-professional, unknown-age buyer (fail-closed).
        """
        self._custom_fields = custom_fields_port
        self._region = region or {}
        self._buyer_resolver = buyer_resolver or (lambda user_id: {})

    def validate_cart(self, *, items: list, user_id) -> Optional[str]:
        buyer = self._buyer_resolver(user_id) or {}
        for line in items:
            reason = self._validate_line(line, buyer)
            if reason:
                return reason
        return None

    # --- per-line rules ---
    def _validate_line(self, line: dict, buyer: dict) -> Optional[str]:
        product_id = line.get("product_id")
        if not product_id:
            return None
        profile = self._load_profile(product_id)
        product_class = profile.product_class
        quantity = int(line.get("quantity", 1) or 1)

        if product_class == PRODUCT_CLASS_RX:
            return REASON_PRESCRIPTION_REQUIRED

        if product_class == PRODUCT_CLASS_FMCG_HOSPITAL:
            if profile.professional_only and not buyer.get("is_professional"):
                return REASON_PROFESSIONAL_ONLY
            return self._quantity_reason(profile, quantity)

        if product_class in (PRODUCT_CLASS_OTC, PRODUCT_CLASS_MEDICAL_DEVICE):
            age_reason = self._age_reason(profile, buyer)
            if age_reason:
                return age_reason
            return self._quantity_reason(profile, quantity)

        # FMCG_PERSONAL and anything unclassified: sold freely.
        return None

    def _age_reason(self, profile: PharmaProfile, buyer: dict) -> Optional[str]:
        required_age = profile.age_restriction_years
        if required_age is None:
            required_age = self._region.get("default_age_restriction_years") or 0
        if not required_age:
            return None
        # Fail-closed: an unknown / unverified age cannot clear an age gate.
        buyer_age = buyer.get("age")
        if not buyer.get("age_verified") or buyer_age is None:
            return REASON_AGE_RESTRICTED
        return REASON_AGE_RESTRICTED if buyer_age < required_age else None

    def _quantity_reason(self, profile: PharmaProfile, quantity: int) -> Optional[str]:
        max_quantity = profile.max_quantity_per_order
        if max_quantity is None:
            max_quantity = self._region.get("default_max_quantity_per_order")
        if max_quantity is None:
            return None
        return REASON_MAX_QUANTITY if quantity > int(max_quantity) else None

    def _load_profile(self, product_id) -> PharmaProfile:
        values = self._custom_fields.get_custom_fields(
            PHARMA_ENTITY_TYPE, _as_uuid(product_id)
        )
        return PharmaProfile.from_custom_fields(values)


def _as_uuid(value):
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
