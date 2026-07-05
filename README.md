# vbwd-shop-pharma-backend (`shop_pharma`)

A region-aware online **pharmacy MODULE** on top of the `shop` commerce engine.
It owns the pharma domain (a 5-way classification, regulated metadata, dispensing
+ compliance gates, regional packs) and **reuses** shop's catalogue / variants /
cart / checkout / stock / pricing / orders. It **never edits core or the shop
module** — `dependencies=["shop"]`; shop resolves standalone without it.

> ⚠️ **Not legal advice.** This module ships the *technical scaffolding* for
> compliance (classification, fields, gates, logo/leaflet hosting, region packs)
> and conservative defaults (**RX not dispensed online**). Whether a given
> configuration is *legally* compliant is jurisdiction-specific and the
> operator's responsibility. All regional facts are **operator-verify**.

## 5-way classification (D2)

`product_class ∈ {RX, OTC, MEDICAL_DEVICE, FMCG_PERSONAL, FMCG_HOSPITAL}`. The
class drives purchase gating, the storefront category segmentation and the tax
class. Gates (server-authoritative, fail-closed):

| Class | Gate |
|---|---|
| RX | **Blocked online** (`prescription_required`; e-prescription deferred). |
| OTC | Age + `max_quantity_per_order`. |
| MEDICAL_DEVICE | Regulatory info (CE/UKCA); optional age/qty. |
| FMCG_PERSONAL | Sold freely. |
| FMCG_HOSPITAL | Respects `professional_only`. |

## Regulated fields = a seeded S77 custom-field SET (D3 — NO new table)

The "profile" is an S77 custom-field set on `entity_type=shop_product`, seeded
idempotently on enable (`field_set_seeder.py`). A typed **`PharmaProfile` read
model VO** is assembled **in code** from `get_custom_fields[_bulk]` — there is
**no `pharma_product_profile` table and no migration** for these fields.
Requiredness is **class-conditional and module-enforced** (`RequiredFieldsByClass`).

## Performance guardrails

- Display reads use the **bulk** S77 port (no N+1, D6).
- **Segment by category** (indexed FK), never by EAV value (D5). The 5 classes
  map to a seeded shop category each.
- Catalogue list + detail are cache-frontable.

## Region framework (D5/R0)

Compliance data (code scheme, register/logo/pharmacovigilance URLs, tax map,
age/qty defaults, locale, withdrawal-right copy) resolves from the active region
pack: `${VBWD_VAR_DIR}/shop_pharma/regions/<cc>.json` (host override) →
the bundled reference `de.json`. One active region per instance (D9); unknown
country code fails loud.

## API

Public:
- `GET /api/v1/pharma/catalogue` — class-segmented (by category), region-aware.
- `GET /api/v1/pharma/products/<slug>` — product + `PharmaProfile` VO + variants.
- `GET /api/v1/pharma/region` — active-region summary.

Admin (perm `pharma.manage`):
- `GET|POST /api/v1/admin/pharma/products`
- `GET|PUT|DELETE /api/v1/admin/pharma/products/<id>`

Packs are authored via shop's S101.0 variant API; gates register into shop's
checkout-validation seam. The pharma module ships zero new commerce primitives.

## Seeders

`populate_db.py` (idempotent, upsert by slug/sku) seeds the 5-class demo
catalogue (70 products) THROUGH services: shop products + pack variants + per
variant warehouse stock + S77 profile values + the field-set defs + a gallery
image per product (imported via the cms `CmsImageService`, linked to the
product). National codes are **synthetic placeholders** (prefixed
`SYNTHETIC-OPERATOR-VERIFY`). The same dataset ships as an envelope-aware
data-exchange JSON under `docs/import/pharma_catalogue.json`.

## DoD

`bin/pre-commit-check.sh --plugin shop_pharma --full` green; core + shop
agnosticism oracles green; no schema migration for the regulated fields (S77's
tables already exist). Prod-deploy: enable the plugin → field set + categories
seed on enable.
