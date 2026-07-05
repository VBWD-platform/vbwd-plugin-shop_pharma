"""RequiredFieldsByClass policy (S101.1).

S77 defs carry no ``required`` flag, so requiredness is class-conditional and
**module-enforced on save**. This is the v1 default and is operator-verify
(jurisdiction-dependent); a region pack MAY tighten the set via config.

Matrix (● required) per ``s101-1`` — the commerce fields + ``product_class`` +
a priced/stocked variant are always required (checked by the product/variant
layer); this policy enforces the per-class regulated-field requiredness.
"""
from __future__ import annotations

from typing import Dict, List

from plugins.shop_pharma.shop_pharma.domain import (
    PRODUCT_CLASS_FMCG_HOSPITAL,
    PRODUCT_CLASS_FMCG_PERSONAL,
    PRODUCT_CLASS_MEDICAL_DEVICE,
    PRODUCT_CLASS_OTC,
    PRODUCT_CLASS_RX,
)

# Required regulated fields per class (the ● cells in the s101-1 matrix).
REQUIRED_BY_CLASS: Dict[str, List[str]] = {
    PRODUCT_CLASS_RX: [
        "active_substances",
        "strength",
        "pharmaceutical_form",
        "marketing_authorisation_holder",
        "leaflet_url",
    ],
    PRODUCT_CLASS_OTC: [
        "active_substances",
        "strength",
        "pharmaceutical_form",
        "leaflet_url",
    ],
    PRODUCT_CLASS_MEDICAL_DEVICE: [
        "device_marking",
        "leaflet_url",
    ],
    PRODUCT_CLASS_FMCG_PERSONAL: [],
    PRODUCT_CLASS_FMCG_HOSPITAL: [],
}


class RequiredFieldsValidationError(ValueError):
    """Raised when a save is missing required fields for its product_class."""

    def __init__(self, product_class: str, missing: List[str]):
        self.product_class = product_class
        self.missing = missing
        super().__init__(f"Class '{product_class}' requires: {', '.join(missing)}")


class RequiredFieldsByClass:
    """Validate that a value set satisfies its class's required fields."""

    @staticmethod
    def required_for(product_class: str) -> List[str]:
        return list(REQUIRED_BY_CLASS.get(product_class, []))

    @classmethod
    def validate(cls, product_class: str, values: Dict) -> None:
        """Raise if any required field for ``product_class`` is missing/empty."""
        if product_class is None:
            raise RequiredFieldsValidationError("<none>", ["product_class"])
        missing = [
            key for key in cls.required_for(product_class) if _is_empty(values.get(key))
        ]
        if missing:
            raise RequiredFieldsValidationError(product_class, missing)


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple)):
        return len(value) == 0
    return False
