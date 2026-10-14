"""Ground-truth evaluation: dataset loading, finding->annotation matching, metrics, evaluation runs.

Matching rule (finding-level)
  A prediction (finding) matches an annotation iff
    (a) same page, (b) finding.category == annotation.category, and
    (c) the annotation's target selector is one of the finding's canonical selector segments
        (so a finding on the target or any descendant of it matches), or the finding's HTML excerpt
        carries the target's id attribute.
Counting rules
  * Only findings with status confirmed|suspected and severity != info are counted as predictions;
    `needs_manual_review` findings are reported separately and excluded from precision/recall.
  * Prediction unit = (selector, category): several rules firing on one element+category count once.
  * TP = annotations matched by >=1 prediction; FN = annotations with none; FP = predictions matching no annotation.
  * Annotation completeness caveat: a correct finding the annotators did not label counts as FP.
Page-level: truth-positive = page has >=1 annotation; predicted-positive = method emitted >=1 prediction.
"""
import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sklearn.metrics import cohen_kappa_score
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.security import UrlPolicy
from app.models import Audit, EvalCase, EvalDataset, EvalResult, EvalRun, Finding, GroundTruth
from app.services.audit_runner import AuditRunner
from app.services.browser_service import host_of
from app.services.finding_normalizer import conventional

log = logging.getLogger(__name__)
CATEGORIES = ["images", "navigation", "forms", "contrast", "semantics", "readability", "other"]
METHODS = ("conventional", "ai", "combined")


def _now():
    return datetime.now(timezone.utc)


# ---------------- dataset ----------------
def load_dataset_file(dataset_dir: Path) -> dict:
    return json.loads((Path(dataset_dir) / "dataset.json").read_text())


def seed_dataset(db: Session, dataset_dir: Path) -> EvalDataset | None:
    path = Path(dataset_dir) / "dataset.json"
    if not path.exists():
        return None
    d = load_dataset_file(dataset_dir)
    existing = db.scalar(select(EvalDataset).where(EvalDataset.name == d["name"], EvalDataset.version == d["version"]))
    if existing:
        return existing
    ds = EvalDataset(name=d["name"], version=d["version"], description=d.get("description", ""),
                     annotation_protocol=d.get("annotation_protocol", ""))
    for c in d["cases"]:
        case = EvalCase(page_id=c["page_id"], condition=c["condition"], fixture_file=c["fixture_file"],
                        description=c.get("description", ""))
        for a in c.get("annotations", []):
            case.annotations.append(GroundTruth(
                annotation_id=a["annotation_id"], category=a["category"], target_selector=a["target_selector"],
                issue_type=a["issue_type"], criterion=a.get("criterion"), rationale=a.get("rationale", ""),
                provenance=a.get("provenance", ""), second_reviewer_label=a.get("second_reviewer_label")))
        ds.cases.append(case)
    db.add(ds)
    db.commit()
    return ds


# ---------------- pure metric functions ----------------
def _prf(tp: int, fp: int, fn: int) -> tuple[float | None, float | None, float | None]:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p is not None and r is not None and (p + r) > 0 else (0.0 if p is not None and r is not None else None)
    return p, r, f


def finding_matches(annotation: dict, finding: dict) -> bool:
    if finding["category"] != annotation["category"]:
        return False
    target = annotation["target_selector"]
    sel = finding.get("selector") or ""
    if target in [seg.strip() for seg in sel.split(" > ")]:
        return True
    if target.startswith("#"):
        return f'id="{target[1:]}"' in ((finding.get("evidence") or {}).get("html_excerpt") or "")
    return False


def counted(findings: list[dict]) -> list[dict]:
    """Predictions entering the metrics: status filter + (selector, category) dedupe."""
    seen, out = set(), []
    for f in findings:
        if f["status"] == "needs_manual_review" or f["severity"] == "info":
            continue
        key = (f.get("selector") or f"__{id(f)}", f["category"])
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def evaluate_case(annotations: list[dict], findings: list[dict]) -> dict:
    """Per-case matching for one method's findings."""
    preds = counted(findings)
    matched_ann = [a["annotation_id"] for a in annotations if any(finding_matches(a, p) for p in preds)]
    unmatched_preds = [p for p in preds if not any(finding_matches(a, p) for a in annotations)]
    return {"matched": matched_ann,
            "missed": [a["annotation_id"] for a in annotations if a["annotation_id"] not in matched_ann],
            "fp": [{"selector": p.get("selector"), "category": p["category"], "title": p["title"]} for p in unmatched_preds],
            "n_predictions": len(preds),
            "n_manual_review": sum(1 for f in findings if f["status"] == "needs_manual_review")}


def compute_metrics(cases: list[dict]) -> dict:
    """cases: [{page_id, annotations:[...], findings: {conventional:[...], ai:[...]}}] -> metrics for all methods."""
    out: dict = {"methods": {}, "overlap": {}, "per_case": []}
    for c in cases:
        by = {"conventional": c["findings"]["conventional"], "ai": c["findings"]["ai"],
              "combined": c["findings"]["conventional"] + c["findings"]["ai"]}
        ev = {m: evaluate_case(c["annotations"], by[m]) for m in METHODS}
        out["per_case"].append({"page_id": c["page_id"], "n_annotations": len(c["annotations"]), **{m: ev[m] for m in METHODS}})
    for m in METHODS:
        tp = sum(len(pc[m]["matched"]) for pc in out["per_case"])
        fn = sum(len(pc[m]["missed"]) for pc in out["per_case"])
        fp = sum(len(pc[m]["fp"]) for pc in out["per_case"])
        p, r, f = _prf(tp, fp, fn)
        cats = {}
        for cat in CATEGORIES:
            ctp = cfn = cfp = 0
            for c, pc in zip(cases, out["per_case"]):
                ann_by_id = {a["annotation_id"]: a for a in c["annotations"]}
                ctp += sum(1 for i in pc[m]["matched"] if ann_by_id[i]["category"] == cat)
                cfn += sum(1 for i in pc[m]["missed"] if ann_by_id[i]["category"] == cat)
                cfp += sum(1 for x in pc[m]["fp"] if x["category"] == cat)
            if ctp + cfn + cfp:
                cp, cr, cf = _prf(ctp, cfp, cfn)
                cats[cat] = {"tp": ctp, "fp": cfp, "fn": cfn, "precision": cp, "recall": cr, "f1": cf}
        # page-level confusion matrix
        ptp = pfp = pfn = ptn = 0
        for pc in out["per_case"]:
            truth, pred = pc["n_annotations"] > 0, pc[m]["n_predictions"] > 0
            ptp += truth and pred
            pfn += truth and not pred
            pfp += (not truth) and pred
            ptn += (not truth) and not pred
        pp, pr, pf = _prf(ptp, pfp, pfn)
        out["methods"][m] = {"finding": {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f},
                             "per_category": cats,
                             "page": {"tp": ptp, "fp": pfp, "fn": pfn, "tn": ptn, "precision": pp, "recall": pr, "f1": pf}}
    # annotation-level overlap between the two method families
    ov = {"conventional_only": 0, "ai_only": 0, "both": 0, "neither": 0}
    for pc in out["per_case"]:
        c_set, a_set = set(pc["conventional"]["matched"]), set(pc["ai"]["matched"])
        n = pc["n_annotations"]
        both = len(c_set & a_set)
        ov["both"] += both
        ov["conventional_only"] += len(c_set - a_set)
        ov["ai_only"] += len(a_set - c_set)
        ov["neither"] += n - len(c_set | a_set)
    out["overlap"] = ov
    out["n_pages"] = len(cases)
    out["n_annotations"] = sum(len(c["annotations"]) for c in cases)
    return out


def reviewer_agreement(annotations: list[dict]) -> dict:
    """First reviewer's label is always 'issue' for stored annotations; compare to the second reviewer where present."""
    rev = [a for a in annotations if a.get("second_reviewer_label")]
    if not rev:
        return {"available": False, "n_reviewed": 0, "percent_agreement": None, "cohen_kappa": None,
                "note": "No second-reviewer labels have been recorded."}
    first = ["issue"] * len(rev)
    second = [a["second_reviewer_label"] for a in rev]
    pa = sum(1 for x, y in zip(first, second) if x == y) / len(rev)
    kappa = cohen_kappa_score(first, second) if len(set(first + second)) > 1 else None
    return {"available": True, "n_reviewed": len(rev), "percent_agreement": pa, "cohen_kappa": kappa,
            "note": "Kappa is undefined when one reviewer assigns a single label to every item." if kappa is None else ""}


# ---------------- fixture server + run ----------------
class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass


def serve_fixtures(dataset_dir: Path) -> tuple[str, ThreadingHTTPServer]:
    """Serve <dataset>/fixtures at /fixtures/ on an ephemeral loopback port."""
    root = Path(dataset_dir).resolve()
    handler = partial(_QuietHandler, directory=str(root))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}", srv


def finding_dict(f: Finding) -> dict:
    return {"id": f.id, "method": f.method, "category": f.category, "severity": f.severity, "status": f.status,
            "selector": f.selector, "title": f.title, "evidence": f.evidence or {}}


async def run_evaluation(settings: Settings, sm: sessionmaker[Session], runner: AuditRunner, run_id: str) -> None:
    def fail(msg: str):
        with sm() as db:
            r = db.get(EvalRun, run_id)
            r.status, r.error, r.completed_at = "failed", msg, _now()
            db.commit()

    origin, srv = serve_fixtures(settings.dataset_dir)
    try:
        policy = UrlPolicy(fixture_origins={origin})
        with sm() as db:
            run = db.get(EvalRun, run_id)
            run.status = "running"
            db.commit()
            cases = [(c.id, c.page_id, c.fixture_file, [
                {"annotation_id": a.annotation_id, "category": a.category, "target_selector": a.target_selector,
                 "second_reviewer_label": a.second_reviewer_label} for a in c.annotations])
                for c in db.get(EvalDataset, run.dataset_id).cases]
        data = []
        for _cid, page_id, fixture, anns in cases:
            url = f"{origin}/fixtures/{fixture}"
            with sm() as db:
                a = Audit(url=url, host=host_of(url), mode="combined", status="queued", source="evaluation",
                          capture_screenshot=True, config={"evaluation_run": run_id, "page_id": page_id})
                db.add(a)
                db.commit()
                audit_id = a.id
            await runner.run(audit_id, policy)
            with sm() as db:
                au = db.get(Audit, audit_id)
                if au.status != "completed" or au.ai_error:
                    return fail(f"Audit of fixture '{page_id}' did not complete cleanly: {au.error or au.ai_error}")
                fs = [finding_dict(f) for f in db.scalars(select(Finding).where(Finding.audit_id == audit_id))]
            data.append({"page_id": page_id, "annotations": anns, "audit_id": audit_id,
                         "findings": {"conventional": [f for f in fs if conventional(f["method"])],
                                      "ai": [f for f in fs if not conventional(f["method"])]}})
        metrics = compute_metrics(data)
        agreement = reviewer_agreement([a for d in data for a in d["annotations"]])
        for pc, d in zip(metrics["per_case"], data):
            pc["audit_id"] = d["audit_id"]
        with sm() as db:
            run = db.get(EvalRun, run_id)
            for m in METHODS:
                mm = metrics["methods"][m]
                for scope, vals in (("finding", mm["finding"]), ("page", mm["page"])):
                    db.add(EvalResult(run_id=run_id, method=m, scope=scope, category="all", tp=vals["tp"], fp=vals["fp"],
                                      fn=vals["fn"], tn=vals.get("tn"), precision=vals["precision"], recall=vals["recall"], f1=vals["f1"]))
                for cat, v in mm["per_category"].items():
                    db.add(EvalResult(run_id=run_id, method=m, scope="finding", category=cat, tp=v["tp"], fp=v["fp"], fn=v["fn"],
                                      precision=v["precision"], recall=v["recall"], f1=v["f1"]))
            run.details = {"overlap": metrics["overlap"], "per_case": metrics["per_case"], "n_pages": metrics["n_pages"],
                           "n_annotations": metrics["n_annotations"]}
            run.reviewer_agreement = agreement
            run.status, run.completed_at = "completed", _now()
            db.commit()
    except Exception:  # noqa: BLE001
        log.exception("evaluation crashed")
        fail("Unexpected error while running the evaluation.")
    finally:
        srv.shutdown()
