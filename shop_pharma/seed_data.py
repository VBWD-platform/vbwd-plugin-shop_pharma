"""Demo pharmacy catalogue (S101.1) — "fewer, higher-fidelity" products.

The single source for the seed dataset. ``populate_db`` imports it and upserts
through services (upsert by slug/sku); ``build_envelope`` emits the same data as
the envelope-aware data-exchange JSON under ``docs/import/``. REAL generic names
and active substances; national codes are SYNTHETIC and clearly marked
operator-verify (see ``SYNTHETIC_CODE_NOTICE``).
"""
from __future__ import annotations

from typing import Any, Dict, List

from plugins.shop_pharma.shop_pharma.domain import (
    PRODUCT_CLASS_FMCG_HOSPITAL,
    PRODUCT_CLASS_FMCG_PERSONAL,
    PRODUCT_CLASS_MEDICAL_DEVICE,
    PRODUCT_CLASS_OTC,
    PRODUCT_CLASS_RX,
)

SEED_ENVELOPE_KEY = "shop_pharma_products"
SEED_ENVELOPE_VERSION = 1

# Synthetic national codes are placeholders, NOT real PZN/CIP/NDC values.
SYNTHETIC_CODE_NOTICE = "SYNTHETIC-OPERATOR-VERIFY"


def _variant(name: str, code_suffix: str, price: float, stock: int) -> Dict[str, Any]:
    """One pack variant; its sku encodes the synthetic national code (D1)."""
    return {
        "name": name,
        "sku": f"{SYNTHETIC_CODE_NOTICE}-{code_suffix}",
        "price": price,
        "stock": stock,
        "attributes": {"pack": name},
    }


def _product(
    *,
    slug: str,
    name: str,
    product_class: str,
    profile: Dict[str, Any],
    variants: List[Dict[str, Any]],
    tags: List[str],
    image_hint: str,
) -> Dict[str, Any]:
    merged_profile = {"product_class": product_class, **profile}
    return {
        "slug": slug,
        "name": name,
        "product_class": product_class,
        "tax_class": "reduced"
        if product_class in (PRODUCT_CLASS_OTC, PRODUCT_CLASS_RX)
        else "standard",
        "pharma_profile": merged_profile,
        "variants": variants,
        "tags": tags,
        "image_hint": image_hint,
    }


# --- OTC medicines (sold with age/qty gates) ---
def _otc_products() -> List[Dict[str, Any]]:
    rows = []
    otc_specs = [
        ("ibuprofen-400mg", "Ibuprofen 400mg", ["ibuprofen"], "400 mg", "tablet"),
        ("paracetamol-500mg", "Paracetamol 500mg", ["paracetamol"], "500 mg", "tablet"),
        ("cetirizine-10mg", "Cetirizine 10mg", ["cetirizine"], "10 mg", "tablet"),
        ("loratadine-10mg", "Loratadine 10mg", ["loratadine"], "10 mg", "tablet"),
        (
            "aspirin-500mg",
            "Aspirin 500mg",
            ["acetylsalicylic_acid"],
            "500 mg",
            "tablet",
        ),
        ("diclofenac-25mg", "Diclofenac 25mg", ["diclofenac"], "25 mg", "tablet"),
        ("omeprazole-20mg", "Omeprazole 20mg", ["omeprazole"], "20 mg", "capsule"),
        ("loperamide-2mg", "Loperamide 2mg", ["loperamide"], "2 mg", "capsule"),
        ("ibuprofen-200mg", "Ibuprofen 200mg", ["ibuprofen"], "200 mg", "tablet"),
        (
            "paracetamol-1000mg",
            "Paracetamol 1000mg",
            ["paracetamol"],
            "1000 mg",
            "tablet",
        ),
        (
            "cetirizine-syrup",
            "Cetirizine 1mg/ml syrup",
            ["cetirizine"],
            "1 mg/ml",
            "syrup",
        ),
        (
            "ibuprofen-lysine-400",
            "Ibuprofen-lysine 400mg",
            ["ibuprofen_lysine"],
            "400 mg",
            "tablet",
        ),
        (
            "paracetamol-suppository",
            "Paracetamol 250mg suppository",
            ["paracetamol"],
            "250 mg",
            "suppository",
        ),
        (
            "aspirin-100mg",
            "Aspirin 100mg",
            ["acetylsalicylic_acid"],
            "100 mg",
            "tablet",
        ),
        ("diclofenac-gel", "Diclofenac 1% gel", ["diclofenac"], "1%", "gel"),
        (
            "loratadine-syrup",
            "Loratadine 1mg/ml syrup",
            ["loratadine"],
            "1 mg/ml",
            "syrup",
        ),
        ("omeprazole-10mg", "Omeprazole 10mg", ["omeprazole"], "10 mg", "capsule"),
        ("ibuprofen-600mg", "Ibuprofen 600mg", ["ibuprofen"], "600 mg", "tablet"),
        (
            "paracetamol-effervescent",
            "Paracetamol effervescent 500mg",
            ["paracetamol"],
            "500 mg",
            "effervescent",
        ),
        (
            "cetirizine-drops",
            "Cetirizine 10mg/ml drops",
            ["cetirizine"],
            "10 mg/ml",
            "drops",
        ),
    ]
    for slug, name, substances, strength, form in otc_specs:
        rows.append(
            _product(
                slug=slug,
                name=name,
                product_class=PRODUCT_CLASS_OTC,
                profile={
                    "active_substances": substances,
                    "strength": strength,
                    "pharmaceutical_form": form,
                    "leaflet_url": f"https://leaflets.example/{slug}-pil.pdf",
                    "max_quantity_per_order": 3,
                    "withdrawal_right_exempt": True,
                    "warnings": "Read the package leaflet before use.",
                },
                variants=[
                    _variant("Pack of 20", f"{slug}-20", 4.99, 120),
                    _variant("Pack of 50", f"{slug}-50", 9.99, 60),
                ],
                tags=["otc", "self-care"],
                image_hint=name,
            )
        )
    return rows


# --- RX (hospital drugs; blocked online) ---
def _rx_products() -> List[Dict[str, Any]]:
    rows = []
    rx_specs = [
        (
            "amoxicillin-500mg",
            "Amoxicillin 500mg",
            ["amoxicillin"],
            "500 mg",
            "capsule",
            "Generic Pharma GmbH",
        ),
        (
            "ceftriaxone-1g",
            "Ceftriaxone 1g",
            ["ceftriaxone"],
            "1 g",
            "powder for solution",
            "Hospital Labs AG",
        ),
        (
            "azithromycin-250mg",
            "Azithromycin 250mg",
            ["azithromycin"],
            "250 mg",
            "tablet",
            "Generic Pharma GmbH",
        ),
        (
            "amoxicillin-250mg",
            "Amoxicillin 250mg",
            ["amoxicillin"],
            "250 mg",
            "capsule",
            "Generic Pharma GmbH",
        ),
        (
            "ceftriaxone-2g",
            "Ceftriaxone 2g",
            ["ceftriaxone"],
            "2 g",
            "powder for solution",
            "Hospital Labs AG",
        ),
        (
            "azithromycin-500mg",
            "Azithromycin 500mg",
            ["azithromycin"],
            "500 mg",
            "tablet",
            "Generic Pharma GmbH",
        ),
        (
            "amoxicillin-suspension",
            "Amoxicillin 125mg/5ml suspension",
            ["amoxicillin"],
            "125 mg/5 ml",
            "suspension",
            "Generic Pharma GmbH",
        ),
        (
            "azithromycin-suspension",
            "Azithromycin 200mg/5ml suspension",
            ["azithromycin"],
            "200 mg/5 ml",
            "suspension",
            "Generic Pharma GmbH",
        ),
    ]
    for slug, name, substances, strength, form, holder in rx_specs:
        rows.append(
            _product(
                slug=slug,
                name=name,
                product_class=PRODUCT_CLASS_RX,
                profile={
                    "active_substances": substances,
                    "strength": strength,
                    "pharmaceutical_form": form,
                    "marketing_authorisation_holder": holder,
                    "leaflet_url": f"https://leaflets.example/{slug}-pil.pdf",
                    "withdrawal_right_exempt": True,
                    "warnings": "Prescription only. Not dispensed online.",
                },
                variants=[_variant("Pack of 20", f"{slug}-20", 12.50, 40)],
                tags=["rx", "antibiotic"],
                image_hint=name,
            )
        )
    return rows


# --- MEDICAL_DEVICE (sold with regulatory info) ---
def _device_products() -> List[Dict[str, Any]]:
    rows = []
    device_specs = [
        ("digital-thermometer", "Digital thermometer", "CE 0123 / class I"),
        ("bp-monitor", "Blood pressure monitor (upper arm)", "CE 0123 / class IIa"),
        ("pulse-oximeter", "Fingertip pulse oximeter", "CE 0123 / class IIa"),
        ("covid-antigen-test", "COVID-19 antigen self-test", "CE 0123 / IVD"),
        ("ear-thermometer", "Infrared ear thermometer", "CE 0123 / class IIa"),
        ("nebulizer", "Compressor nebulizer", "CE 0123 / class IIa"),
        ("blood-glucose-meter", "Blood glucose meter", "CE 0123 / IVD"),
        ("wrist-bp-monitor", "Wrist blood pressure monitor", "CE 0123 / class IIa"),
        (
            "forehead-thermometer",
            "Non-contact forehead thermometer",
            "CE 0123 / class IIa",
        ),
        ("peak-flow-meter", "Peak flow meter", "CE 0123 / class I"),
    ]
    for slug, name, marking in device_specs:
        rows.append(
            _product(
                slug=slug,
                name=name,
                product_class=PRODUCT_CLASS_MEDICAL_DEVICE,
                profile={
                    "device_marking": marking,
                    "leaflet_url": f"https://leaflets.example/{slug}-ifu.pdf",
                    "withdrawal_right_exempt": False,
                    "storage_conditions": "Store at room temperature.",
                },
                variants=[_variant("Single unit", f"{slug}-1", 19.90, 80)],
                tags=["device", "diagnostics"],
                image_hint=name,
            )
        )
    return rows


# --- FMCG_HOSPITAL (clinical consumables; optional professional_only) ---
def _hospital_products() -> List[Dict[str, Any]]:
    rows = []
    hospital_specs = [
        ("sterile-gauze-swabs", "Sterile gauze swabs 10x10cm", True),
        ("nitrile-gloves-m", "Nitrile examination gloves (M)", False),
        ("disposable-syringes-5ml", "Disposable syringes 5ml", True),
        ("antiseptic-solution", "Antiseptic skin solution 250ml", False),
        ("sterile-bandages", "Sterile bandages 5cm", False),
        ("alcohol-swabs", "Alcohol prep swabs", False),
        ("nitrile-gloves-l", "Nitrile examination gloves (L)", False),
        ("disposable-syringes-10ml", "Disposable syringes 10ml", True),
        ("wound-dressing", "Adhesive wound dressing 10x10cm", False),
        ("surgical-face-masks", "Surgical face masks type IIR", False),
        ("examination-gowns", "Disposable examination gowns", True),
        ("cotton-wool-rolls", "Cotton wool rolls 500g", False),
        ("hypodermic-needles", "Hypodermic needles 21G", True),
        ("saline-irrigation", "Sterile saline irrigation 100ml", True),
        ("crepe-bandages", "Crepe support bandages 7.5cm", False),
        ("instrument-wipes", "Surface disinfectant wipes", False),
        ("medical-tape", "Microporous medical tape", False),
        ("sterile-drapes", "Sterile surgical drapes", True),
        ("examination-couch-roll", "Examination couch roll", False),
        ("biohazard-bags", "Biohazard waste bags", True),
    ]
    for slug, name, professional_only in hospital_specs:
        rows.append(
            _product(
                slug=slug,
                name=name,
                product_class=PRODUCT_CLASS_FMCG_HOSPITAL,
                profile={
                    "professional_only": professional_only,
                    "storage_conditions": "Store in a dry place.",
                    "withdrawal_right_exempt": False,
                    "max_quantity_per_order": 50,
                },
                variants=[
                    _variant("Box of 100", f"{slug}-100", 14.50, 200),
                    _variant("Case of 10 boxes", f"{slug}-case", 120.00, 25),
                ],
                tags=["clinical", "consumable"],
                image_hint=name,
            )
        )
    return rows


# --- FMCG_PERSONAL (consumer health & personal care; sold freely) ---
def _personal_products() -> List[Dict[str, Any]]:
    rows = []
    personal_specs = [
        ("vitamin-d3-1000iu", "Vitamin D3 1000 IU", ["cholecalciferol"], "1000 IU"),
        ("vitamin-c-500mg", "Vitamin C 500mg", ["ascorbic_acid"], "500 mg"),
        ("vitamin-d3-2000iu", "Vitamin D3 2000 IU", ["cholecalciferol"], "2000 IU"),
        (
            "vitamin-c-1000mg",
            "Vitamin C 1000mg effervescent",
            ["ascorbic_acid"],
            "1000 mg",
        ),
        ("hand-sanitiser-gel", "Hand sanitiser gel 500ml", [], None),
        ("toothpaste-fluoride", "Fluoride toothpaste 75ml", [], None),
        ("moisturising-cream", "Moisturising body cream 250ml", [], None),
        ("sunscreen-spf50", "Sunscreen SPF 50 200ml", [], None),
        ("lip-balm", "Lip balm with SPF 15", [], None),
        ("shower-gel", "Gentle shower gel 300ml", [], None),
        ("multivitamin-tablets", "Daily multivitamin tablets", [], None),
        ("omega3-capsules", "Omega-3 fish oil capsules", [], None),
    ]
    for slug, name, substances, strength in personal_specs:
        profile: Dict[str, Any] = {
            "withdrawal_right_exempt": False,
            "storage_conditions": "Store at room temperature.",
        }
        if substances:
            profile["active_substances"] = substances
        if strength:
            profile["strength"] = strength
        rows.append(
            _product(
                slug=slug,
                name=name,
                product_class=PRODUCT_CLASS_FMCG_PERSONAL,
                profile=profile,
                variants=[_variant("Single unit", f"{slug}-1", 7.49, 150)],
                tags=["personal-care", "wellness"],
                image_hint=name,
            )
        )
    return rows


def all_products() -> List[Dict[str, Any]]:
    return (
        _otc_products()
        + _rx_products()
        + _device_products()
        + _hospital_products()
        + _personal_products()
    )


def build_envelope() -> Dict[str, Any]:
    """The envelope-aware data-exchange JSON for the demo catalogue."""
    return {
        "vbwd_export": SEED_ENVELOPE_KEY,
        "version": SEED_ENVELOPE_VERSION,
        "_notice": (
            "Demo catalogue. National codes are SYNTHETIC placeholders "
            "(prefixed SYNTHETIC-OPERATOR-VERIFY) — verify per jurisdiction. "
            "Not legal advice."
        ),
        SEED_ENVELOPE_KEY: all_products(),
    }
