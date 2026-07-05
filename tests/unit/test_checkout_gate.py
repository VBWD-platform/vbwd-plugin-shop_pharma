"""S101.1 — class-based checkout gate (D2), server-authoritative, fail-closed."""
from unittest.mock import MagicMock
from uuid import uuid4

from plugins.shop_pharma.shop_pharma.services.checkout_gate import (
    PharmaCheckoutGate,
    REASON_AGE_RESTRICTED,
    REASON_MAX_QUANTITY,
    REASON_PRESCRIPTION_REQUIRED,
    REASON_PROFESSIONAL_ONLY,
)


def _gate(profile_values, region=None, buyer=None):
    port = MagicMock()
    port.get_custom_fields.return_value = profile_values
    return PharmaCheckoutGate(
        port, region or {}, buyer_resolver=lambda user_id: buyer or {}
    )


def _line(quantity=1):
    return {"product_id": str(uuid4()), "quantity": quantity}


def test_rx_is_rejected():
    gate = _gate({"product_class": "RX"})
    assert gate.validate_cart(items=[_line()], user_id="u") == (
        REASON_PRESCRIPTION_REQUIRED
    )


def test_fmcg_personal_is_free():
    gate = _gate({"product_class": "FMCG_PERSONAL"})
    assert gate.validate_cart(items=[_line(99)], user_id="u") is None


def test_otc_over_max_quantity_rejected():
    gate = _gate({"product_class": "OTC", "max_quantity_per_order": 2})
    assert gate.validate_cart(items=[_line(3)], user_id="u") == REASON_MAX_QUANTITY


def test_otc_within_quantity_allowed_when_no_age_gate():
    gate = _gate({"product_class": "OTC", "max_quantity_per_order": 5})
    assert gate.validate_cart(items=[_line(2)], user_id="u") is None


def test_otc_age_gate_fails_closed_for_unverified_buyer():
    gate = _gate(
        {"product_class": "OTC", "age_restriction_years": 18},
        buyer={"age": 25, "age_verified": False},
    )
    assert gate.validate_cart(items=[_line()], user_id="u") == REASON_AGE_RESTRICTED


def test_otc_age_gate_passes_for_verified_adult():
    gate = _gate(
        {"product_class": "OTC", "age_restriction_years": 18},
        buyer={"age": 25, "age_verified": True},
    )
    assert gate.validate_cart(items=[_line()], user_id="u") is None


def test_medical_device_sells_with_info_no_gate():
    gate = _gate({"product_class": "MEDICAL_DEVICE"})
    assert gate.validate_cart(items=[_line()], user_id="u") is None


def test_fmcg_hospital_professional_only_rejected_for_non_pro():
    gate = _gate(
        {"product_class": "FMCG_HOSPITAL", "professional_only": True},
        buyer={"is_professional": False},
    )
    assert gate.validate_cart(items=[_line()], user_id="u") == (
        REASON_PROFESSIONAL_ONLY
    )


def test_fmcg_hospital_professional_allowed_for_pro():
    gate = _gate(
        {"product_class": "FMCG_HOSPITAL", "professional_only": True},
        buyer={"is_professional": True},
    )
    assert gate.validate_cart(items=[_line()], user_id="u") is None


def test_region_default_quantity_cap_applies_when_product_unset():
    gate = _gate({"product_class": "OTC"}, region={"default_max_quantity_per_order": 1})
    assert gate.validate_cart(items=[_line(2)], user_id="u") == REASON_MAX_QUANTITY
