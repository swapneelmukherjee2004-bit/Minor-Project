from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import limiter, runner, storage
from app.api.errors import ApiError
from app.core.config import get_settings
from app.core.security import UrlNotAllowed, UrlPolicy
from app.db.session import get_db
from app.models import Audit, EvalCase, Finding
from app.schemas.schemas import AuditCreate, AuditDetail, AuditSummary, FindingOut
from app.services import evaluation_service as ev
from app.services.browser_service import host_of
from app.services.finding_normalizer import comparison as build_comparison

router = APIRouter(prefix="/audits", tags=["audits"])


def _count_map(db: Session, ids: list[str]) -> dict[str, int]:
    if not ids:
        return {}
    rows = db.execute(select(Finding.audit_id, func.count()).where(Finding.audit_id.in_(ids)).group_by(Finding.audit_id)).all()
    return dict(rows)


def _summary(a: Audit, n: int) -> AuditSummary:
    s = AuditSummary.model_validate(a)
    s.finding_count = n
    return s


def _get(db: Session, audit_id: str) -> Audit:
    a = db.get(Audit, audit_id) if len(audit_id) == 36 else None
    if not a:
        raise ApiError(404, "not_found", "Audit not found.")
    return a


@router.post("", response_model=AuditSummary, status_code=202)
@limiter.limit(get_settings().rate_limit_audits)
async def create_audit(request: Request, body: AuditCreate, db: Session = Depends(get_db)):
    s = get_settings()
    policy = UrlPolicy(fixture_origins=s.fixture_origin_set)
    try:
        await policy.assert_allowed(body.url)  # fail fast with a clear message; re-validated again in the browser
    except UrlNotAllowed as e:
        raise ApiError(400, "url_not_allowed", str(e)) from None
    r = runner(request)
    if r.pending_count() >= s.max_pending_audits:
        raise ApiError(429, "queue_full", "Too many audits are queued. Try again in a few minutes.")
    a = Audit(url=body.url, host=host_of(body.url), mode=body.mode, status="queued",
              capture_screenshot=body.capture_screenshot, config={"viewport": [s.viewport_width, s.viewport_height],
                                                                  "wcag": f"{s.wcag_version} {s.wcag_levels}"})
    db.add(a)
    db.commit()
    r.submit(a.id)
    return _summary(a, 0)


@router.get("")
def list_audits(db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
                q: str | None = Query(None, max_length=200), status: str | None = None, mode: str | None = None):
    stmt = select(Audit).where(Audit.source == "user")
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Audit.url.ilike(like), Audit.page_title.ilike(like)))
    if status:
        stmt = stmt.where(Audit.status == status)
    if mode:
        stmt = stmt.where(Audit.mode == mode)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Audit.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    counts = _count_map(db, [a.id for a in rows])
    return {"items": [_summary(a, counts.get(a.id, 0)) for a in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/{audit_id}", response_model=AuditDetail)
def get_audit(audit_id: str, db: Session = Depends(get_db)):
    a = _get(db, audit_id)
    d = AuditDetail.model_validate({**{c.name: getattr(a, c.name) for c in Audit.__table__.columns},
                                    "has_screenshot": bool(a.screenshot_key),
                                    "finding_count": _count_map(db, [a.id]).get(a.id, 0)})
    return d


@router.delete("/{audit_id}", status_code=204)
def delete_audit(audit_id: str, request: Request, db: Session = Depends(get_db)):
    a = _get(db, audit_id)
    if a.status in ("queued", "running"):
        raise ApiError(409, "audit_in_progress", "Wait for the audit to finish before deleting it.")
    if a.screenshot_key:
        storage(request).delete(a.screenshot_key)
    db.delete(a)
    db.commit()
    return Response(status_code=204)


@router.get("/{audit_id}/findings")
def list_findings(audit_id: str, db: Session = Depends(get_db), severity: str | None = None, category: str | None = None,
                  method: str | None = None, status: str | None = None, detected_by: str | None = None):
    _get(db, audit_id)
    rows = list(db.scalars(select(Finding).where(Finding.audit_id == audit_id)))
    cmp = build_comparison(rows)
    det = {i: g["detected_by"] for g in cmp["groups"] for i in g["conventional_ids"] + g["ai_ids"]}
    out = []
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    for f in sorted(rows, key=lambda f: (order[f.severity], f.method)):
        if severity and f.severity != severity or category and f.category != category or status and f.status != status:
            continue
        if method and (f.method != method and not (method == "conventional" and f.method in ("axe", "custom"))):
            continue
        if detected_by and det.get(f.id) != detected_by:
            continue
        o = FindingOut.model_validate(f).model_dump()
        o["detected_by"] = det.get(f.id)
        out.append(o)
    return {"items": out, "total": len(out)}


def ground_truth_for(db: Session, a: Audit, rows: list[Finding]) -> dict | None:
    """Per-page metrics iff the audited URL is an annotated evaluation fixture."""
    path = urlsplit(a.url).path
    if not path.startswith("/fixtures/"):
        return None
    case = db.scalars(select(EvalCase).where(EvalCase.fixture_file == path[len("/fixtures/"):]).limit(1)).first()
    if not case:
        return None
    anns = [{"annotation_id": g.annotation_id, "category": g.category, "target_selector": g.target_selector} for g in case.annotations]
    fs = [ev.finding_dict(f) for f in rows]
    m = ev.compute_metrics([{"page_id": case.page_id, "annotations": anns,
                             "findings": {"conventional": [f for f in fs if f["method"] != "ai"], "ai": [f for f in fs if f["method"] == "ai"]}}])
    return {"available": True, "page_id": case.page_id, "condition": case.condition, "n_annotations": len(anns),
            "methods": m["methods"], "overlap": m["overlap"], "case": m["per_case"][0]}


@router.get("/{audit_id}/comparison")
def get_comparison(audit_id: str, db: Session = Depends(get_db)):
    a = _get(db, audit_id)
    rows = list(db.scalars(select(Finding).where(Finding.audit_id == audit_id)))
    cmp = build_comparison(rows)
    cmp["by_method"] = {"axe": sum(f.method == "axe" for f in rows), "custom": sum(f.method == "custom" for f in rows),
                        "ai": sum(f.method == "ai" for f in rows)}
    cmp["ground_truth"] = ground_truth_for(db, a, rows) or {"available": False,
                                                            "reason": "No ground-truth annotations exist for this URL."}
    cmp["demo_mode"] = a.demo_mode
    return cmp


@router.get("/{audit_id}/screenshot")
def get_screenshot(audit_id: str, request: Request, db: Session = Depends(get_db)):
    a = _get(db, audit_id)
    data = storage(request).read(a.screenshot_key) if a.screenshot_key else None
    if data is None:
        raise ApiError(404, "no_screenshot", "No screenshot was captured for this audit.")
    return Response(data, media_type="image/png", headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})
