from app.services.finding_normalizer import assign_groups, comparison, normalize, selectors_related


def F(method, sel, cat, wcag=(), id=None):
    return normalize({"method": method, "category": cat, "wcag_criteria": list(wcag), "evidence": {}, "id": id or f"{method}-{sel}-{cat}"}, sel)


def test_selector_relations():
    assert selectors_related("#a", "#a")
    assert selectors_related("#a", "#a > img")
    assert selectors_related("main > div > img", "main > div")
    assert not selectors_related("#a", "#ab")
    assert not selectors_related(None, "#a")


def test_same_element_same_category_merges():
    fs = assign_groups([F("axe", "#i", "images"), F("ai", "#i", "images")])
    assert fs[0]["group_id"] == fs[1]["group_id"]
    assert comparison(fs)["counts"] == {"conventional_only": 0, "ai_only": 0, "both": 1}


def test_category_alone_never_merges():
    fs = assign_groups([F("axe", "#a", "images"), F("ai", "#b", "images")])
    assert fs[0]["group_id"] != fs[1]["group_id"]
    c = comparison(fs)["counts"]
    assert c == {"conventional_only": 1, "ai_only": 1, "both": 0}


def test_same_element_different_category_without_shared_wcag_does_not_merge():
    fs = assign_groups([F("axe", "#a", "contrast", ["1.4.3"]), F("ai", "#a", "semantics", ["1.3.1"])])
    assert fs[0]["group_id"] != fs[1]["group_id"]


def test_shared_wcag_criterion_merges_across_categories():
    fs = assign_groups([F("axe", "#a", "forms", ["3.3.2", "4.1.2"]), F("ai", "#a", "semantics", ["3.3.2"])])
    assert fs[0]["group_id"] == fs[1]["group_id"]


def test_selectorless_ai_finding_is_ai_only():
    fs = assign_groups([F("axe", "#a", "images"), F("ai", None, "images")])
    assert comparison(fs)["counts"]["ai_only"] == 1


def test_ancestor_match_and_custom_counts_as_conventional():
    fs = assign_groups([F("custom", "#card", "navigation", ["2.4.4"]), F("ai", "#card > a", "navigation", ["2.4.4"])])
    assert fs[0]["group_id"] == fs[1]["group_id"]


def test_originals_preserved_and_wcag_sorted():
    f = F("axe", "#x", "images", ["1.4.10", "1.1.1", "1.4.3"])
    assert f["wcag_criteria"] == ["1.1.1", "1.4.3", "1.4.10"]
    assert f["method"] == "axe"
