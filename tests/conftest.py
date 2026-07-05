"""Test fixtures for shop_pharma plugin tests.

Mirrors plugins/shop/tests/conftest.py — a session-scoped Flask app bound to a
``<dbname>_test`` database, and a function-scoped ``db`` fixture that isolates
each test in a rolled-back transaction. Enables email → shop → shop_pharma so
on_enable runs (S77 field-set seed + checkout-gate registration).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

os.environ["FLASK_ENV"] = "testing"
os.environ["TESTING"] = "true"


def _test_db_url() -> str:
    base = os.getenv("DATABASE_URL", "postgresql://vbwd:vbwd@postgres:5432/vbwd")
    prefix, _, dbname = base.rpartition("/")
    dbname = dbname.split("?")[0]
    return f"{prefix}/{dbname}_test"


def _ensure_test_db(url: str) -> None:
    from sqlalchemy import create_engine, text

    main_url = url.rsplit("/", 1)[0] + "/postgres"
    dbname = url.rsplit("/", 1)[1].split("?")[0]
    engine = create_engine(main_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": dbname}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    finally:
        engine.dispose()


def _ensure_pharma_enabled(flask_app) -> None:
    """Enable email → shop → shop_pharma so on_enable runs in a fresh clone."""
    from vbwd.plugins.base import PluginStatus

    manager = getattr(flask_app, "plugin_manager", None)
    if manager is None:
        return
    with flask_app.app_context():
        for name in ("email", "shop", "shop_pharma"):
            plugin = manager.get_plugin(name)
            if plugin is None or plugin.status == PluginStatus.ENABLED:
                continue
            try:
                manager.enable_plugin(name)
            except ValueError:
                if plugin.status == PluginStatus.INITIALIZED:
                    plugin.enable()


@pytest.fixture(scope="session")
def app():
    from vbwd.app import create_app

    url = _test_db_url()
    _ensure_test_db(url)
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "RATELIMIT_ENABLED": False,
        "RATELIMIT_STORAGE_URL": "memory://",
    }
    flask_app = create_app(test_config)

    with flask_app.app_context():
        from vbwd.extensions import db as _db
        from vbwd.testing.integration_db import ensure_schema_and_baseline

        import plugins.shop.shop.models  # noqa: F401

        ensure_schema_and_baseline(_db)

    _ensure_pharma_enabled(flask_app)

    yield flask_app

    with flask_app.app_context():
        from vbwd.extensions import db as _db

        _db.engine.dispose()


@pytest.fixture
def db(app):
    from vbwd.extensions import db as _db

    with app.app_context():
        from vbwd.testing.integration_db import rollback_isolation

        with rollback_isolation(_db):
            _seed_default_currency(_db)
            _ensure_shop_product_entity_type()
            yield _db


def _ensure_shop_product_entity_type() -> None:
    """Register ``shop_product`` so the S77 port resolves in DB-backed tests.

    shop's on_enable normally registers it, but the rolled-back per-test
    transaction + per-process registry can leave it unset; registering here is
    idempotent (register replaces by key).
    """
    from vbwd.services.entity_type_registry import (
        EntityTypeRegistration,
        register_entity_type,
    )

    register_entity_type(
        EntityTypeRegistration("shop_product", "Product", "shop.products.manage")
    )


def _seed_default_currency(_db) -> None:
    from decimal import Decimal
    from uuid import uuid4

    from vbwd.models.currency import Currency

    if not _db.session.query(Currency).filter_by(code="EUR").first():
        _db.session.add(
            Currency(
                id=uuid4(),
                code="EUR",
                name="Euro",
                symbol="€",
                exchange_rate=Decimal("1.0"),
                decimal_places=2,
            )
        )
        _db.session.commit()
