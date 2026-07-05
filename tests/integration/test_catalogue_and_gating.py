"""S101.1 — catalogue segmentation + region endpoint + class-based gating (DB).

Exercises:
- GET /api/v1/pharma/region returns the active (DE reference) region.
- GET /api/v1/pharma/catalogue segments by CATEGORY (one segment per class).
- the class gate, registered into shop's checkout-validation seam, REJECTS an RX
  line at shop's checkout end-to-end (server-authoritative, D2) and ALLOWS OTC.
"""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from vbwd.models.enums import UserRole, UserStatus
from vbwd.models.user import User

from plugins.shop_pharma.shop_pharma.domain import (
    PHARMA_ENTITY_TYPE,
    category_slug_for_class,
)
from plugins.shop_pharma.shop_pharma.services.field_set_seeder import (
    seed_pharma_field_set,
)


@pytest.fixture
def client(app):
    return app.test_client()


def _custom_field_service(db):
    from vbwd.repositories.custom_field_def_repository import CustomFieldDefRepository
    from vbwd.repositories.custom_field_value_repository import (
        CustomFieldValueRepository,
    )
    from vbwd.services.custom_field_service import CustomFieldService

    return CustomFieldService(
        def_repo=CustomFieldDefRepository(db.session),
        value_repo=CustomFieldValueRepository(db.session),
    )


def _seed_categories(db):
    from plugins.shop.shop.models.product_category import ProductCategory
    from plugins.shop_pharma.shop_pharma.domain import CLASS_CATEGORY

    for mapping in CLASS_CATEGORY.values():
        if (
            db.session.query(ProductCategory).filter_by(slug=mapping["slug"]).first()
            is None
        ):
            db.session.add(ProductCategory(name=mapping["name"], slug=mapping["slug"]))
    db.session.commit()


def _make_product(db, *, slug, product_class, profile):
    from plugins.shop.shop.models.product import Product
    from plugins.shop.shop.models.product_category import ProductCategory

    product = Product(id=uuid4(), name=slug, slug=slug, price=5.0, is_active=True)
    category_slug = category_slug_for_class(product_class)
    category = db.session.query(ProductCategory).filter_by(slug=category_slug).first()
    product.categories = [category]
    db.session.add(product)
    db.session.commit()

    service = _custom_field_service(db)
    service.set_custom_fields(
        PHARMA_ENTITY_TYPE, product.id, {"product_class": product_class, **profile}
    )
    return product


@pytest.fixture(autouse=True)
def _seed(db):
    seed_pharma_field_set(_custom_field_service(db))
    _seed_categories(db)


def test_region_endpoint_returns_de_reference(db, client):
    resp = client.get("/api/v1/pharma/region")
    assert resp.status_code == 200
    region = resp.get_json()["region"]
    assert region["country_code"] == "DE"
    assert region["national_code_scheme"] == "PZN"


def test_catalogue_segments_by_category(db, client):
    _make_product(db, slug=f"otc-{uuid4().hex[:6]}", product_class="OTC", profile={})
    _make_product(
        db, slug=f"dev-{uuid4().hex[:6]}", product_class="MEDICAL_DEVICE", profile={}
    )

    resp = client.get("/api/v1/pharma/catalogue")
    assert resp.status_code == 200
    segments = {s["product_class"]: s for s in resp.get_json()["segments"]}
    assert set(segments) >= {"OTC", "RX", "MEDICAL_DEVICE"}
    assert segments["OTC"]["category_slug"] == "otc-medicines"
    assert len(segments["OTC"]["products"]) >= 1


def test_product_detail_returns_profile_vo(db, client):
    slug = f"ibu-{uuid4().hex[:6]}"
    _make_product(
        db,
        slug=slug,
        product_class="OTC",
        profile={"active_substances": ["ibuprofen"], "strength": "400 mg"},
    )
    resp = client.get(f"/api/v1/pharma/products/{slug}")
    assert resp.status_code == 200
    product = resp.get_json()["product"]
    assert product["pharma_profile"]["product_class"] == "OTC"
    assert product["pharma_profile"]["strength"] == "400 mg"


# --- class gate at shop's checkout (server-authoritative) ---


def _auth_as_user(monkeypatch, user):
    import vbwd.middleware.auth as auth_mod

    repo = MagicMock()
    repo.find_by_id.return_value = user
    svc = MagicMock()
    svc.verify_token.return_value = str(user.id)
    monkeypatch.setattr(auth_mod, "UserRepository", lambda *a, **k: repo)
    monkeypatch.setattr(auth_mod, "AuthService", lambda *a, **k: svc)


def _register_gate(db):
    from plugins.shop.shop.checkout_validation_registry import (
        get_checkout_validation_registry,
    )
    from plugins.shop_pharma.shop_pharma.services.checkout_gate import (
        PharmaCheckoutGate,
    )
    from vbwd.services.tags_and_custom_fields import resolve_tags_and_custom_fields

    registry = get_checkout_validation_registry()
    registry.register(
        PharmaCheckoutGate(
            resolve_tags_and_custom_fields(),
            {"default_max_quantity_per_order": 3},
        )
    )
    return registry


def test_rx_line_rejected_at_checkout(db, client, monkeypatch):
    registry = _register_gate(db)
    try:
        user = User(
            id=uuid4(),
            email=f"buyer-{uuid4().hex[:6]}@example.com",
            password_hash="x",
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
        )
        db.session.add(user)
        db.session.commit()
        _auth_as_user(monkeypatch, user)

        rx = _make_product(
            db,
            slug=f"amox-{uuid4().hex[:6]}",
            product_class="RX",
            profile={"marketing_authorisation_holder": "Generic Pharma"},
        )

        resp = client.post(
            "/api/v1/shop/cart/checkout",
            json={"items": [{"product_id": str(rx.id), "quantity": 1}]},
            headers={"Authorization": "Bearer valid"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "prescription_required"
    finally:
        registry.unregister("PharmaCheckoutGate")


def test_otc_over_quantity_rejected_at_checkout(db, client, monkeypatch):
    registry = _register_gate(db)
    try:
        user = User(
            id=uuid4(),
            email=f"buyer-{uuid4().hex[:6]}@example.com",
            password_hash="x",
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
        )
        db.session.add(user)
        db.session.commit()
        _auth_as_user(monkeypatch, user)

        otc = _make_product(
            db,
            slug=f"para-{uuid4().hex[:6]}",
            product_class="OTC",
            profile={"max_quantity_per_order": 2},
        )

        resp = client.post(
            "/api/v1/shop/cart/checkout",
            json={"items": [{"product_id": str(otc.id), "quantity": 5}]},
            headers={"Authorization": "Bearer valid"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "max_quantity_exceeded"
    finally:
        registry.unregister("PharmaCheckoutGate")
