"""Region service (S101.1 / S101.R0 seam) — region-pluggable compliance data.

The active region pack resolves from
``${VBWD_VAR_DIR}/shop_pharma/regions/<cc>.json`` (host-mounted, operator
override); the plugin ships a bundled default ``de.json`` as the reference
region used as a fallback when the var-dir pack is absent. No jurisdiction
string is baked into code (D5) — the country code is config; the data is JSON.

An unknown country code fails loud (``UnknownRegionError``) so a misconfigured
instance never silently serves the wrong jurisdiction's compliance affordances.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

_DEFAULT_VAR_DIR = "/app/var"
# The plugin's bundled region packs (reference data), used as a fallback when
# the host var-dir pack is absent.
_BUNDLED_REGIONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "var_seed", "regions")
)


class UnknownRegionError(ValueError):
    """Raised when no region pack exists for the requested country code."""


class RegionService:
    """Resolve the active region pack (var-dir override → bundled default)."""

    def __init__(self, active_country_code: str = "DE"):
        self._active_country_code = (active_country_code or "DE").upper()

    @property
    def active_country_code(self) -> str:
        return self._active_country_code

    def get_active_region(self) -> Dict[str, Any]:
        return self.get_region(self._active_country_code)

    def get_region(self, country_code: str) -> Dict[str, Any]:
        """Load a region pack by country code, var-dir first then bundled."""
        code = (country_code or "").upper()
        for path in (self._var_dir_path(code), self._bundled_path(code)):
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
        raise UnknownRegionError(f"No region pack for country code '{code}'")

    def _var_dir_path(self, code: str) -> str:
        var_dir = os.environ.get("VBWD_VAR_DIR", _DEFAULT_VAR_DIR)
        return os.path.join(var_dir, "shop_pharma", "regions", f"{code.lower()}.json")

    def _bundled_path(self, code: str) -> str:
        return os.path.join(_BUNDLED_REGIONS_DIR, f"{code.lower()}.json")
