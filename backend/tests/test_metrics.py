import pytest
from sklearn.metrics import precision_recall_fscore_support

from app.services.evaluation_service import compute_metrics, counted, finding_matches, reviewer_agreement


def fnd(sel, cat, status="suspected", sev="medium", html=""):
    return {"selector": sel, "category": cat, "status": status, "severity": sev, "title": "t", "evidence": {"html_excerpt": html}}


A1 = {"annotation_id": "a1", "category": "images", "target_selector": "#img1"}
A2 = {"annotation_id": "a2", "category": "forms", "target_selector": "#f1"}
A3 = {"annotation_id": "a3", "category": "contrast", "target_selector": "#p1"}


def test_matching_rules():
    assert finding_matches(A1, fnd("#img1", "images"))
    assert finding_matches(A1, fnd("#wrap > #img1", "images"))
    assert finding_matches({**A1, "target_selector": "#card"}, fnd("#card > img", "images"))  # descendant of target
    assert not finding_matches(A1, fnd("#img1", "forms"))          # category must agree
    assert not finding_matches(A1, fnd("#img10", "images"))        # no prefix confusion
    assert finding_matches(A1, fnd("main > img", "images", html='<img id="img1">'))


def test_counting_excludes_manual_review_info_and_dedupes():
    fs = [fnd("#a", "images"), fnd("#a", "images"), fnd("#b", "images", status="needs_manual_review"), fnd("#c", "images", sev="info"),
          fnd("#a", "forms")]
    assert len(counted(fs)) == 2


def case(anns, conv, ai, pid="p"):
    return {"page_id": pid, "annotations": anns, "findings": {"conventional": conv, "ai": ai}}


def test_known_example_by_hand():
    cases = [case([A1, A2], [fnd("#img1", "images"), fnd("#zzz", "images")], [fnd("#f1", "forms")], "p1"),
             case([A3], [], [fnd("#p1", "contrast"), fnd("#q", "contrast")], "p2"),
             case([], [fnd("#x", "images")], [], "p3")]
    m = compute_metrics(cases)
    conv = m["methods"]["conventional"]["finding"]
    assert (conv["tp"], conv["fp"], conv["fn"]) == (1, 2, 2)
    assert conv["precision"] == pytest.approx(1 / 3) and conv["recall"] == pytest.approx(1 / 3) and conv["f1"] == pytest.approx(1 / 3)
    ai = m["methods"]["ai"]["finding"]
    assert (ai["tp"], ai["fp"], ai["fn"]) == (2, 1, 1)
    comb = m["methods"]["combined"]["finding"]
    assert (comb["tp"], comb["fn"]) == (3, 0)
    assert m["overlap"] == {"conventional_only": 1, "ai_only": 2, "both": 0, "neither": 0}
    # page level: p1,p2 truth-positive; p3 truth-negative with a conventional false alarm
    pg = m["methods"]["conventional"]["page"]
    assert (pg["tp"], pg["fn"], pg["fp"], pg["tn"]) == (1, 1, 1, 0)
    assert m["methods"]["ai"]["page"]["tn"] == 1
    assert m["methods"]["conventional"]["per_category"]["images"]["tp"] == 1


def test_matches_sklearn_reference():
    cases = [case([A1, A2, A3], [fnd("#img1", "images"), fnd("#p1", "contrast"), fnd("#junk", "forms")], [])]
    c = compute_metrics(cases)["methods"]["conventional"]["finding"]
    # binary vectors over {annotations + unmatched predictions}: truth 1 for annotations, prediction 1 for matched / FP
    y_true = [1, 1, 1, 0]
    y_pred = [1, 0, 1, 1]
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average="binary")
    assert (c["precision"], c["recall"], c["f1"]) == pytest.approx((p, r, f))


def test_undefined_metrics_are_none_not_zero():
    m = compute_metrics([case([], [], [], "clean")])["methods"]["ai"]["finding"]
    assert m["precision"] is None and m["recall"] is None and m["f1"] is None
    m2 = compute_metrics([case([A1], [], [], "x")])["methods"]["ai"]["finding"]
    assert m2["recall"] == 0 and m2["precision"] is None


def test_reviewer_agreement():
    assert reviewer_agreement([{"annotation_id": "a"}])["available"] is False
    r = reviewer_agreement([{"second_reviewer_label": "issue"}, {"second_reviewer_label": "no_issue"}])
    assert r["available"] and r["percent_agreement"] == 0.5
    assert reviewer_agreement([{"second_reviewer_label": "issue"}])["cohen_kappa"] is None
