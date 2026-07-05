"""S101.1 — PharmaProfile read-model VO (assembled in code, no DB)."""
from plugins.shop_pharma.shop_pharma.profile import PharmaProfile


def test_from_custom_fields_maps_typed_fields():
    profile = PharmaProfile.from_custom_fields(
        {
            "product_class": "OTC",
            "active_substances": ["ibuprofen"],
            "strength": "400 mg",
            "age_restriction_years": 16,
            "max_quantity_per_order": 3,
            "professional_only": False,
            "withdrawal_right_exempt": True,
        }
    )
    assert profile.product_class == "OTC"
    assert profile.active_substances == ["ibuprofen"]
    assert profile.strength == "400 mg"
    assert profile.age_restriction_years == 16
    assert profile.max_quantity_per_order == 3
    assert profile.withdrawal_right_exempt is True


def test_empty_values_yield_safe_defaults():
    profile = PharmaProfile.from_custom_fields({})
    assert profile.product_class is None
    assert profile.active_substances == []
    assert profile.professional_only is False


def test_single_substance_string_is_listified():
    profile = PharmaProfile.from_custom_fields({"active_substances": "ibuprofen"})
    assert profile.active_substances == ["ibuprofen"]


def test_to_dict_round_trips_keys():
    data = PharmaProfile(product_class="RX").to_dict()
    assert data["product_class"] == "RX"
    assert "max_quantity_per_order" in data
