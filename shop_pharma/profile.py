"""PharmaProfile read-model VO (S101.1) — assembled in code, no DB table (D3).

The "profile" is the typed view over a product's S77 custom-field values. It is
built from ``get_custom_fields(...)`` / ``get_custom_fields_bulk(...)`` — there
is NO ``pharma_product_profile`` model and NO migration for these fields. The
VO is product-scoped (no user data, D7/GDPR).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from plugins.shop_pharma.shop_pharma.domain import PHARMA_FIELD_KEYS


@dataclass(frozen=True)
class PharmaProfile:
    """Typed read-model over a product's pharma custom-field values."""

    product_class: Optional[str] = None
    active_substances: List[str] = field(default_factory=list)
    strength: Optional[str] = None
    pharmaceutical_form: Optional[str] = None
    atc_code: Optional[str] = None
    marketing_authorisation_holder: Optional[str] = None
    device_marking: Optional[str] = None
    leaflet_url: Optional[str] = None
    smpc_url: Optional[str] = None
    pharmacovigilance_url: Optional[str] = None
    storage_conditions: Optional[str] = None
    warnings: Optional[str] = None
    age_restriction_years: Optional[int] = None
    max_quantity_per_order: Optional[int] = None
    professional_only: bool = False
    withdrawal_right_exempt: bool = False

    @classmethod
    def from_custom_fields(cls, values: Dict[str, Any]) -> "PharmaProfile":
        """Build the VO from a product's raw S77 custom-field value dict."""
        substances = values.get("active_substances") or []
        if not isinstance(substances, list):
            substances = [substances]
        return cls(
            product_class=values.get("product_class"),
            active_substances=list(substances),
            strength=values.get("strength"),
            pharmaceutical_form=values.get("pharmaceutical_form"),
            atc_code=values.get("atc_code"),
            marketing_authorisation_holder=values.get("marketing_authorisation_holder"),
            device_marking=values.get("device_marking"),
            leaflet_url=values.get("leaflet_url"),
            smpc_url=values.get("smpc_url"),
            pharmacovigilance_url=values.get("pharmacovigilance_url"),
            storage_conditions=values.get("storage_conditions"),
            warnings=values.get("warnings"),
            age_restriction_years=_as_int(values.get("age_restriction_years")),
            max_quantity_per_order=_as_int(values.get("max_quantity_per_order")),
            professional_only=bool(values.get("professional_only") or False),
            withdrawal_right_exempt=bool(
                values.get("withdrawal_right_exempt") or False
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_class": self.product_class,
            "active_substances": self.active_substances,
            "strength": self.strength,
            "pharmaceutical_form": self.pharmaceutical_form,
            "atc_code": self.atc_code,
            "marketing_authorisation_holder": self.marketing_authorisation_holder,
            "device_marking": self.device_marking,
            "leaflet_url": self.leaflet_url,
            "smpc_url": self.smpc_url,
            "pharmacovigilance_url": self.pharmacovigilance_url,
            "storage_conditions": self.storage_conditions,
            "warnings": self.warnings,
            "age_restriction_years": self.age_restriction_years,
            "max_quantity_per_order": self.max_quantity_per_order,
            "professional_only": self.professional_only,
            "withdrawal_right_exempt": self.withdrawal_right_exempt,
        }


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# Sanity: keep the VO's known keys aligned with the field set.
assert set(PHARMA_FIELD_KEYS) == set(PharmaProfile().to_dict().keys())
