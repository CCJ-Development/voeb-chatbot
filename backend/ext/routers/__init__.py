"""Extension router registration.

Registers all enabled extension routers with the FastAPI application.
Uses the same include_router_with_global_prefix_prepended() pattern as Onyx.
"""

import logging

from fastapi import FastAPI

from onyx.utils.logger import setup_logger

# Explizit INFO: ext-Logs (insb. [EXT-AUDIT]) muessen sichtbar sein,
# auch wenn globaler LOG_LEVEL=WARNING (PROD).
logger = setup_logger("ext", log_level=logging.INFO)


def register_ext_routers(application: FastAPI) -> None:
    """Register all enabled extension routers."""
    # Import inside function to avoid circular import with onyx.main
    from ext.config import EXT_ENABLED
    from onyx.main import include_router_with_global_prefix_prepended

    if not EXT_ENABLED:
        return

    # Health check is always available when EXT_ENABLED
    from ext.routers.health import router as ext_health_router

    include_router_with_global_prefix_prepended(application, ext_health_router)

    # /ext/health/deep ist PUBLIC (kein Auth) — genutzt von Kubernetes Readiness,
    # Blackbox Monitoring, UptimeRobot. Muss vor check_router_auth registriert sein.
    from onyx.server.auth_check import PUBLIC_ENDPOINT_SPECS

    PUBLIC_ENDPOINT_SPECS.append(("/ext/health/deep", {"GET"}))

    logger.info("Extension health router registered (incl. /ext/health/deep public)")

    # ext-branding: Whitelabel/Branding
    from ext.config import EXT_BRANDING_ENABLED

    if EXT_BRANDING_ENABLED:
        from ext.routers.branding import admin_router as branding_admin_router
        from ext.routers.branding import public_router as branding_public_router

        # Mark public branding endpoints as unauthenticated so login page
        # can display custom branding before any user is logged in.
        # Runtime list mutation — no Onyx source file changes needed.
        from onyx.server.auth_check import PUBLIC_ENDPOINT_SPECS

        PUBLIC_ENDPOINT_SPECS.extend(
            [
                ("/enterprise-settings", {"GET"}),
                ("/enterprise-settings/logo", {"GET"}),
            ]
        )

        include_router_with_global_prefix_prepended(
            application, branding_public_router
        )
        include_router_with_global_prefix_prepended(
            application, branding_admin_router
        )
        logger.info("Extension branding routers registered")

    # ext-token: LLM Usage Tracking + Token Limits
    from ext.config import EXT_TOKEN_LIMITS_ENABLED

    if EXT_TOKEN_LIMITS_ENABLED:
        from ext.routers.token import router as token_router

        include_router_with_global_prefix_prepended(application, token_router)
        logger.info("Extension token router registered")

    # ext-prompts: Custom System Prompts
    from ext.config import EXT_CUSTOM_PROMPTS_ENABLED

    if EXT_CUSTOM_PROMPTS_ENABLED:
        from ext.routers.prompts import router as prompts_router

        include_router_with_global_prefix_prepended(application, prompts_router)
        logger.info("Extension prompts router registered")

    # ext-rbac: Group Management
    from ext.config import EXT_RBAC_ENABLED

    if EXT_RBAC_ENABLED:
        from ext.routers.rbac import admin_router as rbac_admin_router
        from ext.routers.rbac import minimal_router as rbac_minimal_router

        include_router_with_global_prefix_prepended(application, rbac_admin_router)
        include_router_with_global_prefix_prepended(
            application, rbac_minimal_router
        )
        logger.info("Extension RBAC routers registered")

    # ext-access: Document Access Control
    from ext.config import EXT_DOC_ACCESS_ENABLED

    if EXT_DOC_ACCESS_ENABLED:
        from ext.routers.doc_access import router as doc_access_router

        include_router_with_global_prefix_prepended(
            application, doc_access_router
        )
        # Import Celery-Task damit er vom Worker entdeckt wird
        import ext.tasks.doc_access_sync  # noqa: F401

        logger.info("Extension doc-access router + sync task registered")

    # ext-analytics: Platform Usage Analytics
    from ext.config import EXT_ANALYTICS_ENABLED

    if EXT_ANALYTICS_ENABLED:
        from ext.routers.analytics import router as analytics_router

        include_router_with_global_prefix_prepended(application, analytics_router)
        logger.info("Extension analytics router registered")

    # ext-audit: Audit-Logging
    from ext.config import EXT_AUDIT_ENABLED

    if EXT_AUDIT_ENABLED:
        from ext.routers.audit import router as audit_router

        include_router_with_global_prefix_prepended(application, audit_router)

        # IP-Anonymisierung: Task importieren + ersten Lauf schedulen (nach 60s)
        from ext.tasks.audit_ip_anonymize import ext_audit_ip_anonymize_task

        ext_audit_ip_anonymize_task.apply_async(countdown=60)
        logger.info("Extension audit router + IP anonymize task registered")
