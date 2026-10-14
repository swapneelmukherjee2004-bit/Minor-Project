import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler  # noqa: F401
from slowapi.middleware import SlowAPIMiddleware

from app.api import errors
from app.api.deps import limiter
from app.api.routes import audits, evaluations, misc
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_engine, get_sessionmaker
from app.services.audit_runner import AuditRunner
from app.services.browser_service import BrowserService
from app.services.evaluation_service import seed_dataset
from app.services.storage import LocalStorage

log = logging.getLogger(__name__)


def create_app(create_tables: bool = False) -> FastAPI:
    s = get_settings()
    configure_logging(s.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if create_tables:  # tests only; production uses `alembic upgrade head`
            from app.db.base import Base
            import app.models  # noqa: F401
            Base.metadata.create_all(get_engine())
        sm = get_sessionmaker()
        browser = BrowserService(s)
        app.state.storage = LocalStorage(s.storage_dir)
        app.state.runner = AuditRunner(s, sm, browser, app.state.storage)
        app.state.runner.recover_interrupted()
        try:
            with sm() as db:
                seed_dataset(db, s.dataset_dir)
        except Exception:  # noqa: BLE001 - the app should still start without a dataset
            log.exception("could not seed evaluation dataset")
        yield
        await browser.stop()

    app = FastAPI(title=f"{s.app_name} API", version="1.0.0", lifespan=lifespan,
                  description="Compares rule-based (axe-core) and multimodal-AI website accessibility auditing. "
                              "Audit aid only: not a WCAG conformance certification.")
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_methods=["GET", "POST", "DELETE"],
                       allow_headers=["Content-Type"], allow_credentials=False)
    errors.install(app)
    for r in (audits.router, evaluations.router, misc.router):
        app.include_router(r, prefix="/api/v1")
    fixtures = s.dataset_dir / "fixtures"
    if fixtures.is_dir():  # controlled test pages, usable as audit targets only via LOCAL_FIXTURE_ORIGINS
        app.mount("/fixtures", StaticFiles(directory=fixtures), name="fixtures")
    return app


app = create_app()
