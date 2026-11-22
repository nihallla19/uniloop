import logging

from fastapi import Depends, FastAPI

from app import errors, middleware
from app.config import get_settings
from app.modules.catalog.router import router as catalog_router
from app.modules.identity.router import router as identity_router
from app.modules.system.router import router as system_router
from app.security.csrf import require_same_origin

logging.basicConfig(level=logging.INFO, format="%(message)s")

_settings = get_settings()  # fails start-up on bad production config
_docs = _settings.app_env != "production"

app = FastAPI(
    title="Baton API",
    docs_url="/api/v1/docs" if _docs else None,
    redoc_url=None,
    openapi_url="/api/v1/openapi.json" if _docs else None,
    dependencies=[Depends(require_same_origin)],
)
errors.install(app)
middleware.install(app)

app.include_router(system_router, prefix="/api/v1")
app.include_router(identity_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
