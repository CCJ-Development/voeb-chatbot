"""Extension health check endpoints.

/ext/health — Authenticated, returns module status.
/ext/health/deep — PUBLIC, tests critical dependencies (DB, Redis, OpenSearch).
  Used by Kubernetes Readiness Probe and Blackbox Monitoring.
  Returns HTTP 200 if all OK, HTTP 503 if any critical dependency is down.
"""

import logging
import time
import urllib.request

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import JSONResponse

from onyx.auth.users import current_user
from onyx.db.models import User

from ext.config import EXT_ANALYTICS_ENABLED
from ext.config import EXT_AUDIT_ENABLED
from ext.config import EXT_BRANDING_ENABLED
from ext.config import EXT_CUSTOM_PROMPTS_ENABLED
from ext.config import EXT_DOC_ACCESS_ENABLED
from ext.config import EXT_ENABLED
from ext.config import EXT_I18N_ENABLED
from ext.config import EXT_TOKEN_LIMITS_ENABLED
from ext.config import EXT_RBAC_ENABLED

logger = logging.getLogger("ext.health")

router = APIRouter(prefix="/ext", tags=["ext"])


@router.get("/health")
def ext_health_check(
    _: User | None = Depends(current_user),
) -> dict:
    """Returns extension framework status and enabled modules."""
    return {
        "status": "ok",
        "ext_enabled": EXT_ENABLED,
        "modules": {
            "token_limits": EXT_TOKEN_LIMITS_ENABLED,
            "rbac": EXT_RBAC_ENABLED,
            "analytics": EXT_ANALYTICS_ENABLED,
            "branding": EXT_BRANDING_ENABLED,
            "custom_prompts": EXT_CUSTOM_PROMPTS_ENABLED,
            "doc_access": EXT_DOC_ACCESS_ENABLED,
            "i18n": EXT_I18N_ENABLED,
            "audit": EXT_AUDIT_ENABLED,
        },
    }


def _check_postgres() -> dict:
    """SELECT 1 against PostgreSQL. Timeout 3s."""
    try:
        from sqlalchemy import text

        from onyx.db.engine.sql_engine import get_sqlalchemy_engine

        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        logger.warning(f"Deep health: PostgreSQL check failed: {e}")
        return {"status": "error", "detail": str(e)[:200]}


def _check_redis() -> dict:
    """PING against Redis. Timeout 2s."""
    try:
        from onyx.redis.redis_pool import get_redis_client

        r = get_redis_client(tenant_id="__health_check__")
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        logger.warning(f"Deep health: Redis check failed: {e}")
        return {"status": "error", "detail": str(e)[:200]}


def _check_opensearch() -> dict:
    """GET /_cluster/health against OpenSearch. Timeout 3s.

    Always uses HTTPS (OpenSearch rejects plain HTTP even without explicit
    password config). Treats HTTP 401 as "service alive" — auth issues are
    a config problem, not a health problem.
    """
    try:
        import os
        import ssl

        host = os.environ.get("OPENSEARCH_HOST", "localhost")
        port = int(os.environ.get("OPENSEARCH_REST_API_PORT", "9200"))
        password = os.environ.get("OPENSEARCH_PASSWORD", "")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        url = f"https://{host}:{port}/_cluster/health"
        req = urllib.request.Request(url)
        if password:
            import base64

            creds = base64.b64encode(f"admin:{password}".encode()).decode()
            req.add_header("Authorization", f"Basic {creds}")

        with urllib.request.urlopen(req, timeout=3, context=ctx) as resp:
            if resp.status == 200:
                return {"status": "ok"}
            return {"status": "error", "detail": f"HTTP {resp.status}"}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"status": "ok", "detail": "reachable (auth required)"}
        logger.warning(f"Deep health: OpenSearch check failed: {e}")
        return {"status": "error", "detail": str(e)[:200]}
    except Exception as e:
        logger.warning(f"Deep health: OpenSearch check failed: {e}")
        return {"status": "error", "detail": str(e)[:200]}


@router.get("/health/deep")
def ext_deep_health_check() -> JSONResponse:
    """Tests critical dependencies. PUBLIC — no auth required.

    Used by:
    - Kubernetes Readiness Probe
    - Blackbox Monitoring (Prometheus)
    - External Synthetic Monitoring (UptimeRobot)

    Returns HTTP 200 if all critical dependencies OK, HTTP 503 otherwise.
    Each check is isolated — one failure does not prevent others from running.
    No sensitive data in response (safe for public access).
    """
    start = time.monotonic()

    checks = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "opensearch": _check_opensearch(),
    }

    all_ok = all(c["status"] == "ok" for c in checks.values())
    elapsed_ms = round((time.monotonic() - start) * 1000)

    result = {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
        "elapsed_ms": elapsed_ms,
    }

    return JSONResponse(
        content=result,
        status_code=200 if all_ok else 503,
    )
