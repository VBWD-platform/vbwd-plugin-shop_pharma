"""S101.1 — RequiredFieldsByClass policy (module-enforced requiredness)."""
import pytest

from plugins.shop_pharma.shop_pharma.required_fields import (
    RequiredFieldsByClass,
    RequiredFieldsValidationError,
)


def test_otc_requires_substance_strength_form_leaflet():
    with pytest.raises(RequiredFieldsValidationError) as caught:
        RequiredFieldsByClass.validate("OTC", {"product_class": "OTC"})
    missing = set(caught.value.missing)
    assert {
        "active_substances",
        "strength",
        "pharmaceutical_form",
        "leaflet_url",
    } <= missing


def test_otc_passes_when_required_present():
    RequiredFieldsByClass.validate(
        "OTC",
        {
            "active_substances": ["ibuprofen"],
            "strength": "400 mg",
            "pharmaceutical_form": "tablet",
            "leaflet_url": "https://example/pil.pdf",
        },
    )


def test_medical_device_requires_device_marking():
    with pytest.raises(RequiredFieldsValidationError) as caught:
        RequiredFieldsByClass.validate(
            "MEDICAL_DEVICE", {"leaflet_url": "https://x/ifu.pdf"}
        )
    assert "device_marking" in caught.value.missing


def test_rx_requires_marketing_authorisation_holder():
    with pytest.raises(RequiredFieldsValidationError) as caught:
        RequiredFieldsByClass.validate(
            "RX",
            {
                "active_substances": ["amoxicillin"],
                "strength": "500 mg",
                "pharmaceutical_form": "capsule",
                "leaflet_url": "https://x/pil.pdf",
            },
        )
    assert "marketing_authorisation_holder" in caught.value.missing


def test_fmcg_personal_saves_with_only_commerce_and_class():
    RequiredFieldsByClass.validate("FMCG_PERSONAL", {"product_class": "FMCG_PERSONAL"})


def test_missing_product_class_is_rejected():
    with pytest.raises(RequiredFieldsValidationError):
        RequiredFieldsByClass.validate(None, {})
