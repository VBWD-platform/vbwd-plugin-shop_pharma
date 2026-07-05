"""S101.1 — admin pharma product CRUD + required-fields enforcement (DB)."""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from vbwd.models.enums import UserRole, UserStatus
from vbwd.models.user import User

from plugins.shop_pharma.shop_pharma.services.field_set_seeder import (
    seed_pharma_field_set,
)


@pytest.fixture
def client(app):
    return app.test_client()


HEADERS = {"Authorization": "Bearer valid"}


@pytest.fixture(autouse=True)
def _seed_defs(db):
    from vbwd.repositories.custom_field_def_repository import CustomFieldDefRepository
    from vbwd.repositories.custom_field_value_repository import (
        CustomFieldValueRepository,
    )
    from vbwd.services.custom_field_service import CustomFieldService

    seed_pharma_field_set(
        CustomFieldService(
            def_repo=CustomFieldDefRepository(db.session),
            value_repo=CustomFieldValueRepository(db.session),
        )
    )
    # Seed the OTC category so the create flow can link it.
    from plugins.shop.shop.models.product_category import ProductCategory

    if (
        db.session.query(ProductCategory).filter_by(slug="otc-medicines").first()
        is None
    ):
        db.session.add(ProductCategory(name="OTC", slug="otc-medicines"))
        db.session.commit()


def _make_admin(db):
    admin = User(
        id=uuid4(),
        email=f"admin-{uuid4().hex[:8]}@example.com",
        password_hash="x",
        status=UserStatus.ACTIVE,
        role=UserRole.ADMIN,
    )
    db.session.add(admin)
    db.session.commit()
    return admin


def _auth_as_admin(monkeypatch, admin):
    import vbwd.middleware.auth as auth_mod

    repo = MagicMock()
    repo.find_by_id.return_value = admin
    svc = MagicMock()
    svc.verify_token.return_value = str(admin.id)
    monkeypatch.setattr(auth_mod, "UserRepository", lambda *a, **k: repo)
    monkeypatch.setattr(auth_mod, "AuthService", lambda *a, **k: svc)
    monkeypatch.setattr(type(admin), "is_admin", property(lambda self: True))
    monkeypatch.setattr(type(admin), "has_permission", lambda self, perm: True)


def _otc_payload(slug):
    return {
        "name": "Ibuprofen 400mg",
        "slug": slug,
        "price": 4.0,
        "tax_class": "reduced",
        "variants": [
            {"name": "Pack of 20", "sku": f"PZN-{uuid4().hex[:6]}", "price": 4.99}
        ],
        "pharma_profile": {
            "product_class": "OTC",
            "active_substances": ["ibuprofen"],
            "strength": "400 mg",
            "pharmaceutical_form": "tablet",
            "leaflet_url": "https://x/pil.pdf",
            "max_quantity_per_order": 3,
        },
    }


def test_create_otc_product_with_profile_and_variant(db, client, monkeypatch):
    admin = _make_admin(db)
    _auth_as_admin(monkeypatch, admin)
    slug = f"ibuprofen-{uuid4().hex[:8]}"

    resp = client.post(
        "/api/v1/admin/pharma/products", json=_otc_payload(slug), headers=HEADERS
    )
    assert resp.status_code == 201, resp.get_json()
    payload = resp.get_json()["product"]
    assert payload["pharma_profile"]["product_class"] == "OTC"
    assert len(payload["variants"]) == 1
    # Linked to the OTC category (segment by category, D5).
    assert any(c["slug"] == "otc-medicines" for c in payload["categories"])


def test_create_pharma_product_stamped_with_medical_shop_type(db, client, monkeypatch):
    """S116.4 — the created shop product carries the ``medical`` shop-axis tag
    while its S77 ``product_class`` axis is untouched (orthogonal coexistence)."""
    admin = _make_admin(db)
    _auth_as_admin(monkeypatch, admin)
    slug = f"medtag-{uuid4().hex[:8]}"

    resp = client.post(
        "/api/v1/admin/pharma/products", json=_otc_payload(slug), headers=HEADERS
    )
    assert resp.status_code == 201, resp.get_json()
    product = resp.get_json()["product"]
    # Shop axis: tagged with the marker type.
    assert product["product_type_slug"] == "medical"
    # MARKER type carries NO cluster — all pharma data stays in the S77 store.
    assert product["type_field_values"] == {}
    # Pharma axis: product_class untouched, orthogonal to the shop type.
    assert product["pharma_profile"]["product_class"] == "OTC"


def test_create_otc_missing_required_fields_rejected(db, client, monkeypatch):
    admin = _make_admin(db)
    _auth_as_admin(monkeypatch, admin)
    payload = _otc_payload(f"bad-otc-{uuid4().hex[:8]}")
    # Drop required OTC fields.
    payload["pharma_profile"] = {"product_class": "OTC"}

    resp = client.post("/api/v1/admin/pharma/products", json=payload, headers=HEADERS)
    assert resp.status_code == 400, resp.get_json()
    assert "active_substances" in resp.get_json().get("missing", [])


def test_create_medical_device_requires_marking(db, client, monkeypatch):
    admin = _make_admin(db)
    _auth_as_admin(monkeypatch, admin)
    payload = {
        "name": "Thermometer",
        "slug": f"thermo-{uuid4().hex[:8]}",
        "price": 9.0,
        "variants": [{"name": "Unit", "sku": f"DEV-{uuid4().hex[:6]}", "price": 9.0}],
        "pharma_profile": {
            "product_class": "MEDICAL_DEVICE",
            "leaflet_url": "https://x/ifu.pdf",
        },
    }
    resp = client.post("/api/v1/admin/pharma/products", json=payload, headers=HEADERS)
    assert resp.status_code == 400
    assert "device_marking" in resp.get_json().get("missing", [])


def test_update_and_delete_product(db, client, monkeypatch):
    admin = _make_admin(db)
    _auth_as_admin(monkeypatch, admin)
    created = client.post(
        "/api/v1/admin/pharma/products",
        json=_otc_payload(f"upd-{uuid4().hex[:8]}"),
        headers=HEADERS,
    )
    product_id = created.get_json()["product"]["id"]

    updated = client.put(
        f"/api/v1/admin/pharma/products/{product_id}",
        json={"name": "Ibuprofen 400 forte"},
        headers=HEADERS,
    )
    assert updated.status_code == 200, updated.get_json()
    assert updated.get_json()["product"]["name"] == "Ibuprofen 400 forte"

    deleted = client.delete(
        f"/api/v1/admin/pharma/products/{product_id}", headers=HEADERS
    )
    assert deleted.status_code == 200
