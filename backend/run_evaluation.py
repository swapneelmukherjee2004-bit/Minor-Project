"""Run the ground-truth evaluation from the command line.

    python run_evaluation.py [--json out.json]

Starts a loopback fixture server, audits every dataset page with the configured conventional + AI pipeline,
matches findings to annotations and stores the run in the database (visible on the Evaluation page).
"""
import argparse
import asyncio
import json

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_sessionmaker
from app.models import EvalDataset, EvalRun
from app.services.ai_providers import MockProvider
from app.services.audit_runner import AuditRunner
from app.services.browser_service import BrowserService
from app.services.evaluation_service import run_evaluation, seed_dataset
from app.services.storage import LocalStorage


async def main(out: str | None) -> None:
    s = get_settings()
    configure_logging("WARNING")
    sm = get_sessionmaker()
    browser = BrowserService(s)
    runner = AuditRunner(s, sm, browser, LocalStorage(s.storage_dir))
    with sm() as db:
        ds = seed_dataset(db, s.dataset_dir)
        if ds is None:
            raise SystemExit(f"No dataset.json in {s.dataset_dir}")
        run = EvalRun(dataset_id=ds.id, ai_provider=s.ai_provider, ai_model=MockProvider.model if s.demo_mode else s.ai_model,
                      prompt_version=s.prompt_version, is_demo=s.demo_mode, config={"wcag": f"{s.wcag_version} {s.wcag_levels}",
                      "dataset_version": ds.version})
        db.add(run)
        db.commit()
        run_id = run.id
    try:
        await run_evaluation(s, sm, runner, run_id)
    finally:
        await browser.stop()
    with sm() as db:
        r = db.get(EvalRun, run_id)
        if r.status != "completed":
            raise SystemExit(f"Evaluation failed: {r.error}")
        print(f"Run {run_id} completed. provider={r.ai_provider} model={r.ai_model} demo={r.is_demo}")
        if r.is_demo:
            print("NOTE: demo/mock provider - these numbers verify the pipeline only and are NOT research results.")
        for x in r.results:
            if x.category == "all":
                f = lambda v: "n/a" if v is None else f"{v:.2f}"  # noqa: E731
                print(f"{x.method:12s} {x.scope:8s} TP={x.tp} FP={x.fp} FN={x.fn} P={f(x.precision)} R={f(x.recall)} F1={f(x.f1)}")
        print("overlap (annotation level):", r.details["overlap"])
        if out:
            json.dump({"run_id": run_id, "details": r.details, "agreement": r.reviewer_agreement}, open(out, "w"), indent=2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    asyncio.run(main(ap.parse_args().json))
