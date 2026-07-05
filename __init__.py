"""shop_pharma plugin (S101.1) — the pharmacy domain MODULE on top of shop.

Owns the 5-way product classification (a seeded S77 custom-field SET on
``shop_product`` — NO new table, D3), the class-based purchase gates (registered
into shop's checkout-validation seam), the pharmacy catalogue/admin APIs, and
the regional registry. It REUSES shop's commerce engine and NEVER edits core or
the shop module. ``dependencies=["shop"]``.
"""
import logging

from vbwd.plugins.base import BasePlugin, PluginMetadata, PublicRouteDeclaration

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "debug_mode": False,
    # The single active jurisdiction for this instance (D9); the region pack is
    # data under ${VBWD_VAR_DIR}/shop_pharma/regions/<cc>.json (bundled de.json
    # is the reference fallback).
    "active_region": "DE",
    # Class-gating defaults (regions may tighten via the pack).
    "rx_blocked_online": True,
}

# Module-level so routes can read the configured active region without holding a
# plugin reference.
_active_region_code = DEFAULT_CONFIG["active_region"]


def get_active_region_code() -> str:
    return _active_region_code


def _build_custom_field_service():
    """A core ``CustomFieldService`` bound to the live session (for def seeding).

    The narrow S77 port exposes only value access; def CRUD (seeding) needs the
    service, built here from core repos (used, not edited).
    """
    from vbwd.extensions import db
    from vbwd.repositories.custom_field_def_repository import (
        CustomFieldDefRepository,
    )
    from vbwd.repositories.custom_field_value_repository import (
        CustomFieldValueRepository,
    )
    from vbwd.services.custom_field_service import CustomFieldService

    return CustomFieldService(
        def_repo=CustomFieldDefRepository(db.session),
        value_repo=CustomFieldValueRepository(db.session),
    )


class ShopPharmaPlugin(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="shop_pharma",
            version="26.6",
            author="VBWD",
            description="Pharmacy module — classification, compliance, gates "
            "over the shop commerce engine",
            dependencies=["shop"],
        )

    def initialize(self, config=None):
        merged = {**DEFAULT_CONFIG}
        if config:
            merged.update(config)
        super().initialize(merged)
        global _active_region_code
        _active_region_code = merged.get("active_region", "DE")

    def declare_public_routes(self) -> PublicRouteDeclaration:
        """Public pharma-shop storefront catalogue + region reads."""
        return PublicRouteDeclaration(
            read={
                "/api/v1/pharma/catalogue": "Public pharma-shop catalogue listing for the storefront.",
                "/api/v1/pharma/products/<slug>": "Public single pharma-shop product for the storefront.",
                "/api/v1/pharma/region": "Public pharma-shop region/availability info for the storefront.",
            },
        )

    def get_blueprint(self):
        from plugins.shop_pharma.shop_pharma.routes import pharma_bp

        return pharma_bp

    def get_url_prefix(self) -> str:
        return ""

    @property
    def admin_permissions(self):
        return [
            {
                "key": "pharma.manage",
                "label": "Manage pharmacy catalogue",
                "group": "Pharmacy",
            }
        ]

    def on_enable(self):
        from flask import current_app

        # 1) Seed the S77 field set (idempotent; no migration — D3).
        self._seed_field_set()

        # 1b) Register the shop-axis MARKER product type (S116.4 coexistence).
        #     Empty cluster; pharma data stays in the S77 store. Orthogonal to
        #     ``product_class``.
        self._register_medical_product_type()

        # 2) Seed the class -> category tree so the storefront segments by
        #    category (indexed FK), never by an EAV value (D5).
        self._seed_class_categories()

        # 3) Register the class-based checkout gate into shop's validation seam
        #    (server-authoritative, fail-closed — D2/D6).
        self._register_checkout_gate()

        # 4) Register DI providers (none unique to pharma today; the module's
        #    services are built per-request in routes from shop repos + the S77
        #    port). Documented here so the seam is explicit.
        _ = getattr(current_app, "container", None)

    def on_disable(self):
        try:
            from plugins.shop.shop.checkout_validation_registry import (
                get_checkout_validation_registry,
            )

            get_checkout_validation_registry().unregister("PharmaCheckoutGate")
        except Exception as error:  # pragma: no cover - defensive on teardown
            logger.warning("[shop_pharma] gate unregister failed: %s", error)

    # --- enable helpers ---
    def _seed_field_set(self) -> None:
        from plugins.shop_pharma.shop_pharma.services.field_set_seeder import (
            seed_pharma_field_set,
        )

        try:
            created = seed_pharma_field_set(_build_custom_field_service())
            logger.info("[shop_pharma] field set seeded (%s new defs)", created)
        except Exception as error:
            logger.warning("[shop_pharma] field-set seeding failed: %s", error)

    def _register_medical_product_type(self) -> None:
        """S116.4 — register the ``medical`` MARKER type via shop's seam and
        reconcile it into ``shop_product_type``.

        shop reconciles on its OWN enable, which runs before this dependent
        plugin's enable; so shop_pharma must reconcile again to materialise its
        late-registered descriptor. Guarded soft import so pharma still enables
        if shop is somehow absent (a plugin-with-declared-dependency import, NOT
        a core import). Commits its own session (a plugin writing DB from
        ``on_enable`` must commit — the test teardown otherwise rolls it back).
        """
        try:
            from vbwd.extensions import db
            from plugins.shop.shop.services.product_type_registry import (
                reconcile_product_types,
                register_product_type,
            )
            from plugins.shop_pharma.shop_pharma.domain import (
                MEDICAL_PRODUCT_TYPE_DESCRIPTOR,
            )

            register_product_type(MEDICAL_PRODUCT_TYPE_DESCRIPTOR)
            reconcile_product_types(db.session)
            logger.info("[shop_pharma] medical product type registered")
        except Exception as error:
            logger.warning(
                "[shop_pharma] medical product-type registration failed: %s",
                error,
            )

    def _seed_class_categories(self) -> None:
        from vbwd.extensions import db
        from plugins.shop.shop.models.product_category import ProductCategory
        from plugins.shop.shop.repositories.product_category_repository import (
            ProductCategoryRepository,
        )
        from plugins.shop_pharma.shop_pharma.domain import CLASS_CATEGORY

        try:
            repository = ProductCategoryRepository(db.session)
            for mapping in CLASS_CATEGORY.values():
                if repository.find_by_slug(mapping["slug"]) is None:
                    category = ProductCategory(
                        name=mapping["name"], slug=mapping["slug"]
                    )
                    db.session.add(category)
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            logger.warning("[shop_pharma] category seeding failed: %s", error)

    def _register_checkout_gate(self) -> None:
        from plugins.shop.shop.checkout_validation_registry import (
            get_checkout_validation_registry,
        )
        from plugins.shop_pharma.shop_pharma.services.checkout_gate import (
            PharmaCheckoutGate,
        )
        from plugins.shop_pharma.shop_pharma.services.region_service import (
            RegionService,
            UnknownRegionError,
        )
        from vbwd.services.tags_and_custom_fields import (
            resolve_tags_and_custom_fields,
        )

        try:
            region_service = RegionService(get_active_region_code())
            region = region_service.get_active_region()
        except UnknownRegionError:
            region = {}

        gate = PharmaCheckoutGate(resolve_tags_and_custom_fields(), region)
        get_checkout_validation_registry().register(gate)
        logger.info("[shop_pharma] checkout gate registered")
