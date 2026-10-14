from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.api.routes.audits import _get, _summary, _count_map, ground_truth_for
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Audit, EvalDataset, EvalResult, EvalRun, Finding
from app.services import report_service as rep
from app.services.finding_normalizer import comparison as build_comparison

router = APIRouter()


@router.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        dbs = "ok"
    except Exception:  # noqa: BLE001
        dbs = "unavailable"
    return {"status": "ok" if dbs == "ok" else "degraded", "database": dbs}


@router.get("/settings/status", tags=["system"])
def settings_status():
    s = get_settings()
    return {"app_name": s.app_name, "demo_mode": s.demo_mode, "ai_provider": s.ai_provider, "ai_model": "demo-heuristic-v1" if s.demo_mode else s.ai_model,
            "ai_configured": s.ai_configured, "prompt_version": s.prompt_version,
            "wcag": {"version": s.wcag_version, "levels": s.wcag_levels.split(",")},
            "limits": {"navigation_timeout_ms": s.nav_timeout_ms, "max_requests_per_page": s.max_requests_per_page,
                       "max_screenshot_height_px": s.max_screenshot_height, "max_concurrent_audits": s.max_concurrent_audits,
                       "audit_rate_limit": s.rate_limit_audits},
            "local_fixtures_enabled": bool(s.fixture_origin_set),
            "fixture_origin": sorted(s.fixture_origin_set)[0] if s.fixture_origin_set else None}


@router.get("/dashboard/summary", tags=["dashboard"])
def dashboard(db: Session = Depends(get_db)):
    user = Audit.source == "user"
    total = db.scalar(select(func.count()).select_from(Audit).where(user)) or 0
    done = db.scalar(select(func.count()).select_from(Audit).where(user, Audit.status == "completed")) or 0
    hosts = db.scalar(select(func.count(func.distinct(Audit.host))).where(user)) or 0
    ids = select(Audit.id).where(user, Audit.status == "completed")
    sev = dict(db.execute(select(Finding.severity, func.count()).where(Finding.audit_id.in_(ids)).group_by(Finding.severity)).all())
    meth = dict(db.execute(select(Finding.method, func.count()).where(Finding.audit_id.in_(ids)).group_by(Finding.method)).all())
    cat = dict(db.execute(select(Finding.category, func.count()).where(Finding.audit_id.in_(ids)).group_by(Finding.category)).all())
    # provenance across completed audits
    prov = {"conventional_only": 0, "ai_only": 0, "both": 0}
    for aid in db.scalars(ids):
        c = build_comparison(list(db.scalars(select(Finding).where(Finding.audit_id == aid))))["counts"]
        for k in prov:
            prov[k] += c[k]
    recent = db.scalars(select(Audit).where(user).order_by(Audit.created_at.desc()).limit(8)).all()
    counts = _count_map(db, [a.id for a in recent])
    return {"total_audits": total, "completed_audits": done, "websites_analyzed": hosts,
            "total_findings": sum(sev.values()), "by_severity": sev, "by_method": meth, "by_category": cat,
            "provenance": prov, "demo_audits": db.scalar(select(func.count()).select_from(Audit).where(user, Audit.demo_mode)) or 0,
            "recent_audits": [_summary(a, counts.get(a.id, 0)) for a in recent]}


@router.get("/reports/{audit_id}", tags=["reports"])
def report(audit_id: str, format: str = Query("json", pattern="^(json|csv|pdf)$"), db: Session = Depends(get_db)):
    a = _get(db, audit_id)
    if a.status != "completed":
        raise ApiError(409, "audit_not_complete", "Reports are available once the audit has completed.")
    rows = list(db.scalars(select(Finding).where(Finding.audit_id == audit_id)))
    r = rep.build_report(a, rows, build_comparison(rows), (ground_truth_for(db, a, rows) or None))
    name = f"audit-{a.id}.{format}"
    hdr = {"Content-Disposition": f'attachment; filename="{name}"', "X-Content-Type-Options": "nosniff"}
    if format == "json":
        return Response(rep.to_json(r), media_type="application/json", headers=hdr)
    if format == "csv":
        return Response(rep.to_csv(r), media_type="text/csv; charset=utf-8", headers=hdr)
    return Response(rep.to_pdf(r), media_type="application/pdf", headers=hdr)
