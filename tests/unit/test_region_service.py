"""S101.1 / R0 — region service: bundled default + unknown-region fails loud."""
import pytest

from plugins.shop_pharma.shop_pharma.services.region_service import (
    RegionService,
    UnknownRegionError,
)


def test_bundled_de_is_the_reference_region():
    region = RegionService("DE").get_active_region()
    assert region["country_code"] == "DE"
    assert region["national_code_scheme"] == "PZN"
    assert region["display_currency"] == "EUR"
    assert region["locale"] == "de-DE"
    # Operator-verify flag is present and true (not legal advice).
    assert region["operator_verify"] is True


def test_unknown_region_fails_loud():
    with pytest.raises(UnknownRegionError):
        RegionService("ZZ").get_active_region()


def test_var_dir_pack_overrides_bundled(tmp_path, monkeypatch):
    import json

    regions_dir = tmp_path / "shop_pharma" / "regions"
    regions_dir.mkdir(parents=True)
    (regions_dir / "de.json").write_text(
        json.dumps({"country_code": "DE", "national_code_scheme": "OVERRIDE"})
    )
    monkeypatch.setenv("VBWD_VAR_DIR", str(tmp_path))

    region = RegionService("DE").get_active_region()
    assert region["national_code_scheme"] == "OVERRIDE"
