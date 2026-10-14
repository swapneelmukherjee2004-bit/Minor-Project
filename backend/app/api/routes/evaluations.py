import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import runner
from app.api.errors import ApiError
from app.core.config import get_settings
from app.db.session import get_db, get_sessionmaker
from app.models import EvalDataset, EvalResult, EvalRun
from app.services import evaluation_service as ev
from app.services.ai_providers import MockProvider

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class EvalCreate(BaseModel):
    dataset_name: str | None = None
    dataset_version: str | None = None


def _run_out(r: EvalRun, db: Session) -> dict:
    results = db.scalars(select(EvalResult).where(EvalResult.run_id == r.id)).all()
    ds = db.get(EvalDataset, r.dataset_id)
    return {"id": r.id, "status": r.status, "error": r.error, "ai_provider": r.ai_provider, "ai_model": r.ai_model,
            "prompt_version": r.prompt_version, "is_demo": r.is_demo, "config": r.config, "details": r.details,
            "reviewer_agreement": r.reviewer_agreement, "created_at": r.created_at, "completed_at": r.completed_at,
            "dataset": {"name": ds.name, "version": ds.version},
            "results": [{"method": x.method, "scope": x.scope, "category": x.category, "tp": x.tp, "fp": x.fp, "fn": x.fn,
                         "tn": x.tn, "precision": x.precision, "recall": x.recall, "f1": x.f1} for x in results]}


def _dataset_info(db: Session, ds: EvalDataset) -> dict:
    anns = [a for c in ds.cases for a in c.annotations]
    by_cond: dict[str, int] = {}
    for c in ds.cases:
        by_cond[c.condition] = by_cond.get(c.condition, 0) + 1
    by_cat: dict[str, int] = {}
    for a in anns:
        by_cat[a.category] = by_cat.get(a.category, 0) + 1
    return {"name": ds.name, "version": ds.version, "description": ds.description, "annotation_protocol": ds.annotation_protocol,
            "n_pages": len(ds.cases), "n_annotations": len(anns), "pages_by_condition": by_cond, "annotations_by_category": by_cat,
            "pages": [{"page_id": c.page_id, "condition": c.condition, "description": c.description, "n_annotations": len(c.annotations)}
                      for c in ds.cases]}


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    ds = db.scalars(select(EvalDataset).order_by(EvalDataset.created_at.desc()).limit(1)).first()
    latest = db.scalars(select(EvalRun).where(EvalRun.status == "completed").order_by(EvalRun.created_at.desc()).limit(1)).first()
    running = db.scalars(select(EvalRun).where(EvalRun.status.in_(("queued", "running")))).first()
    return {"state": "completed" if latest else "pending", "dataset": _dataset_info(db, ds) if ds else None,
            "latest_run": _run_out(latest, db) if latest else None, "running_run_id": running.id if running else None,
            "note": None if latest else "Evaluation pending: no evaluation run has been completed yet. Ground-truth metrics are not available."}


@router.get("")
def list_runs(db: Session = Depends(get_db)):
    runs = db.scalars(select(EvalRun).order_by(EvalRun.created_at.desc()).limit(50)).all()
    return {"items": [{"id": r.id, "status": r.status, "created_at": r.created_at, "is_demo": r.is_demo, "ai_model": r.ai_model} for r in runs]}


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    r = db.get(EvalRun, run_id) if len(run_id) == 36 else None
    if not r:
        raise ApiError(404, "not_found", "Evaluation run not found.")
    return _run_out(r, db)


@router.post("", status_code=202)
async def start_run(request: Request, body: EvalCreate | None = None, db: Session = Depends(get_db)):
    s = get_settings()
    q = select(EvalDataset).order_by(EvalDataset.created_at.desc())
    if body and body.dataset_name:
        q = q.where(EvalDataset.name == body.dataset_name)
    if body and body.dataset_version:
        q = q.where(EvalDataset.version == body.dataset_version)
    ds = db.scalars(q.limit(1)).first()
    if not ds:
        raise ApiError(404, "no_dataset", "No evaluation dataset has been loaded.")
    if db.scalars(select(EvalRun).where(EvalRun.status.in_(("queued", "running")))).first():
        raise ApiError(409, "evaluation_in_progress", "An evaluation run is already in progress.")
    model = MockProvider.model if s.demo_mode else s.ai_model
    run = EvalRun(dataset_id=ds.id, ai_provider=s.ai_provider, ai_model=model, prompt_version=s.prompt_version, is_demo=s.demo_mode,
                  config={"wcag": f"{s.wcag_version} {s.wcag_levels}", "viewport": [s.viewport_width, s.viewport_height],
                          "dataset_version": ds.version})
    db.add(run)
    db.commit()
    task = asyncio.create_task(ev.run_evaluation(s, get_sessionmaker(), runner(request), run.id))
    request.app.state.runner.tasks.add(task)
    task.add_done_callback(request.app.state.runner.tasks.discard)
    return {"id": run.id, "status": run.status}
