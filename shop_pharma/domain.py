"""Pharma domain constants (S101.1).

The single source of truth for:
- the 5-way product classification,
- the S77 custom-field SET registered on ``shop_product`` (no new table — D3),
- the class -> shop-category mapping (segment by category, never by EAV — D5),
- the required-vs-optional-by-class matrix (module-enforced — S77 has no
  ``required`` flag).

This module names no jurisdiction (region facts live in the region packs); it
only owns the classification + field schema.
"""
from __future__ import annotations

# --- entity type the field set hangs off (shop owns the registration) ---
PHARMA_ENTITY_TYPE = "shop_product"

# --- S116.4 shop-axis MARKER type (coexistence, not migration) ---
# The shop product-type slug stamped on every pharma product. It is a MARKER:
# an EMPTY field cluster — no regulatory data moves here; all pharma fields stay
# in the S77 store keyed by ``product_class``. The two axes are orthogonal: a
# pharma product is ``product_type_slug="medical"`` (shop axis) AND
# ``product_class="RX"`` etc. (pharma axis). Registered into shop's
# ``shop_product_type`` via the ProductTypeRegistry seam on enable.
MEDICAL_PRODUCT_TYPE_SLUG = "medical"
MEDICAL_PRODUCT_TYPE_DESCRIPTOR = {
    "slug": MEDICAL_PRODUCT_TYPE_SLUG,
    "name": "Medical",
    "description": "Pharmacy/medical products (RX, OTC, devices). Regulatory "
    "fields live in the pharma classification store, not on this type.",
    "product_type_fields": [],
    "source": "plugin",
}

# --- the 5-way product classification (D2) ---
PRODUCT_CLASS_RX = "RX"
PRODUCT_CLASS_OTC = "OTC"
PRODUCT_CLASS_MEDICAL_DEVICE = "MEDICAL_DEVICE"
PRODUCT_CLASS_FMCG_PERSONAL = "FMCG_PERSONAL"
PRODUCT_CLASS_FMCG_HOSPITAL = "FMCG_HOSPITAL"

PRODUCT_CLASSES = (
    PRODUCT_CLASS_RX,
    PRODUCT_CLASS_OTC,
    PRODUCT_CLASS_MEDICAL_DEVICE,
    PRODUCT_CLASS_FMCG_PERSONAL,
    PRODUCT_CLASS_FMCG_HOSPITAL,
)

# A controlled active-substance vocabulary for the demo catalogue. Operators
# extend this on the field def (S77 multiselect options) per jurisdiction.
ACTIVE_SUBSTANCE_VOCABULARY = (
    "ibuprofen",
    "paracetamol",
    "acetylsalicylic_acid",
    "cetirizine",
    "loratadine",
    "diclofenac",
    "amoxicillin",
    "ceftriaxone",
    "azithromycin",
    "omeprazole",
    "loperamide",
    "cholecalciferol",
    "ascorbic_acid",
    "ibuprofen_lysine",
)

# --- the S77 custom-field SET (key, label, type, options) ---
# Order here is the admin display order (sort_order = index).
PHARMA_FIELD_DEFS = (
    {
        "key": "product_class",
        "label": "Product class",
        "type": "select",
        "options": list(PRODUCT_CLASSES),
    },
    {
        "key": "active_substances",
        "label": "Active substances",
        "type": "multiselect",
        "options": list(ACTIVE_SUBSTANCE_VOCABULARY),
    },
    {"key": "strength", "label": "Strength", "type": "text", "options": None},
    {
        "key": "pharmaceutical_form",
        "label": "Pharmaceutical form",
        "type": "text",
        "options": None,
    },
    {"key": "atc_code", "label": "ATC code", "type": "text", "options": None},
    {
        "key": "marketing_authorisation_holder",
        "label": "Marketing authorisation holder",
        "type": "text",
        "options": None,
    },
    {
        "key": "device_marking",
        "label": "Device marking (CE/UKCA + class)",
        "type": "text",
        "options": None,
    },
    {
        "key": "leaflet_url",
        "label": "Leaflet / IFU URL",
        "type": "text",
        "options": None,
    },
    {"key": "smpc_url", "label": "SmPC URL", "type": "text", "options": None},
    {
        "key": "pharmacovigilance_url",
        "label": "Pharmacovigilance URL",
        "type": "text",
        "options": None,
    },
    {
        "key": "storage_conditions",
        "label": "Storage conditions",
        "type": "text",
        "options": None,
    },
    {"key": "warnings", "label": "Warnings", "type": "text", "options": None},
    {
        "key": "age_restriction_years",
        "label": "Age restriction (years)",
        "type": "number",
        "options": None,
    },
    {
        "key": "max_quantity_per_order",
        "label": "Max quantity per order",
        "type": "number",
        "options": None,
    },
    {
        "key": "professional_only",
        "label": "Professional only",
        "type": "bool",
        "options": None,
    },
    {
        "key": "withdrawal_right_exempt",
        "label": "Withdrawal right exempt",
        "type": "bool",
        "options": None,
    },
)

# All the keys the module owns (for the read-model VO assembly).
PHARMA_FIELD_KEYS = tuple(field["key"] for field in PHARMA_FIELD_DEFS)

# --- class -> demo shop category (segment by category, indexed FK — D5) ---
# Each class maps to ONE primary storefront category so the catalogue segments
# by category, never by a custom-field value read.
CLASS_CATEGORY = {
    PRODUCT_CLASS_RX: {
        "slug": "prescription-medicines",
        "name": "Prescription medicines",
    },
    PRODUCT_CLASS_OTC: {
        "slug": "otc-medicines",
        "name": "Over-the-counter medicines",
    },
    PRODUCT_CLASS_MEDICAL_DEVICE: {
        "slug": "medical-devices",
        "name": "Medical devices & diagnostics",
    },
    PRODUCT_CLASS_FMCG_PERSONAL: {
        "slug": "personal-care",
        "name": "Personal care & supplements",
    },
    PRODUCT_CLASS_FMCG_HOSPITAL: {
        "slug": "clinical-consumables",
        "name": "Clinical consumables",
    },
}


def category_slug_for_class(product_class: str) -> str | None:
    mapping = CLASS_CATEGORY.get(product_class)
    return mapping["slug"] if mapping else None
