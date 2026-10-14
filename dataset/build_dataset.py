"""Generates fixtures/*.html and dataset.json (ground truth) from one spec, so labels and pages cannot drift apart.

Ground truth is established BY CONSTRUCTION: each defect is injected by the dataset author on a stated element
before any tool is run. Labels never come from axe-core or an AI model. Run: python dataset/build_dataset.py
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
PROV = "Injected by the dataset author (single annotator) before any tool was run; established by construction."

# 1x1 transparent-safe inline images (data URIs) so fixtures are self-contained and need no network.
def svg(color: str, label: str = "") -> str:
    s = f"<svg xmlns='http://www.w3.org/2000/svg' width='320' height='180'><rect width='320' height='180' fill='{color}'/><text x='20' y='95' font-size='22' fill='white'>{label}</text></svg>"
    return "data:image/svg+xml;utf8," + s.replace("<", "%3C").replace(">", "%3E").replace("#", "%23").replace("'", "%27").replace(" ", "%20")


def page(title, body, lang='lang="en"', head_title=True, extra_css=""):
    t = f"<title>{title}</title>" if head_title else ""
    return f"""<!doctype html>
<html {lang}>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">{t}
<style>body{{font-family:Arial,sans-serif;color:#1a1a1a;background:#fff;margin:0;line-height:1.5}}
header,main,footer{{max-width:760px;margin:0 auto;padding:16px}}nav a{{margin-right:16px;color:#0b3d91}}
a{{color:#0b3d91}}figure{{margin:16px 0}}img{{max-width:100%}}label{{display:block;margin-top:12px}}
button{{margin-top:12px;padding:8px 16px;font-size:16px}}input,textarea{{font-size:16px;padding:6px;width:280px}}{extra_css}</style></head>
<body>
<header><nav aria-label="Main"><a href="#top">Home</a><a href="#about">About</a><a href="#contact">Contact</a></nav></header>
<main id="top">
{body}
</main>
<footer><p>&copy; 2025 Example fixture site.</p></footer>
</body></html>
"""


def ann(aid, cat, target, issue, crit, why):
    return {"annotation_id": aid, "category": cat, "target_selector": target, "issue_type": issue, "criterion": crit,
            "rationale": why, "provenance": PROV, "second_reviewer_label": None}


CASES = []


def case(pid, cond, desc, body, anns=(), **kw):
    CASES.append({"page_id": pid, "condition": cond, "fixture_file": f"{pid}.html", "description": desc, "annotations": list(anns)})
    (HERE / "fixtures" / f"{pid}.html").write_text(page(kw.pop("title", pid.replace("-", " ").title()), body, **kw))


A, B, C = svg("#2a6f97", "Team"), svg("#bc4749", "Chart"), svg("#386641", "Product")

# ---- accessible baselines ----
case("baseline-article", "baseline", "Accessible article with described figure and descriptive links.", f"""
<h1>Composting at home</h1><p>Composting turns kitchen scraps into soil.</p>
<figure><img id="compost-bin" src="{A}" alt="Wooden compost bin filled with leaves and vegetable scraps" width="320" height="180">
<figcaption>A two-chamber wooden compost bin.</figcaption></figure>
<h2>Getting started</h2><p>Read the <a href="#guide">beginner's composting guide</a> for more.</p>""")
case("baseline-form", "baseline", "Accessible contact form with labels, hint and a descriptive button.", """
<h1>Contact us</h1><form action="#" onsubmit="return false"><label for="name">Full name</label><input id="name" name="name" autocomplete="name">
<label for="mail">Email address</label><input id="mail" type="email" name="mail" autocomplete="email" aria-describedby="mail-hint" required>
<p id="mail-hint">We will only use this to reply to you.</p><button type="submit">Send message</button></form>""")
case("baseline-landing", "baseline", "Accessible landing page with described images and a descriptive call to action.", f"""
<h1>Greenhouse supplies</h1><p>Everything you need to grow food year-round.</p>
<h2>Popular products</h2><img id="seed-tray" src="{C}" alt="Black seed-starting tray with twelve cells holding seedlings" width="320" height="180">
<p><a href="#plans">View pricing plans</a></p>""")

# ---- injected defects ----
case("img-missing-alt", "injected", "Informative image without any alt attribute.", f"""
<h1>Our team</h1><img id="team-photo" src="{A}" width="320" height="180"><p>Meet the people behind the project.</p>""",
     [ann("img-missing-alt-1", "images", "#team-photo", "missing_alt", "1.1.1", "img has no alt attribute and conveys information about the team.")])
case("img-vague-alt", "injected", "Alt text exists but is a placeholder / non-descriptive.", f"""
<h1>Annual report</h1>
<figure><img id="revenue-chart" src="{B}" alt="graphic" width="320" height="180"><figcaption>Quarterly revenue by region, 2024</figcaption></figure>
<img id="hero-photo" src="{A}" alt="IMG_2043.jpg" width="320" height="180"><p>Our offices.</p>""",
     [ann("img-vague-alt-1", "images", "#revenue-chart", "vague_alt", "1.1.1", "alt 'graphic' does not convey the chart's content, which the caption shows is revenue by region."),
      ann("img-vague-alt-2", "images", "#hero-photo", "filename_alt", "1.1.1", "alt is a camera file name, not a description.")])
case("img-context-mismatch", "injected", "Alt text is fluent but contradicts the caption.", f"""
<h1>Results</h1>
<figure><img id="results-chart" src="{B}" alt="A smiling person at a desk" width="320" height="180"><figcaption>Figure 2: Quarterly revenue by region</figcaption></figure>""",
     [ann("img-context-mismatch-1", "images", "#results-chart", "alt_contradicts_context", "1.1.1", "alt describes a person; the figure is a revenue chart per its caption.")])
case("nav-generic-links", "injected", "Links whose text is meaningless out of context.", """
<h1>News</h1><p>Our new pricing is live. <a id="pricing-link" href="#pricing">Click here</a></p>
<p>Spring campaign results are in. <a id="news-link" href="#results">Read more</a></p>""",
     [ann("nav-generic-links-1", "navigation", "#pricing-link", "generic_link_text", "2.4.4", "'Click here' gives no destination information when read out of context."),
      ann("nav-generic-links-2", "navigation", "#news-link", "generic_link_text", "2.4.4", "'Read more' is not distinguishable from other 'Read more' links.")])
case("form-no-label", "injected", "Text field with no label, placeholder or name.", """
<h1>Newsletter</h1><form action="#" onsubmit="return false"><input id="email" type="email" name="email"><button type="submit">Subscribe</button></form>""",
     [ann("form-no-label-1", "forms", "#email", "missing_label", "3.3.2", "The field has no programmatic or visible label.")])
case("form-placeholder-only", "injected", "Field labelled only by placeholder text.", """
<h1>Shop</h1><form action="#" role="search" onsubmit="return false"><input id="search-q" type="search" name="q" placeholder="Search products"><button type="submit">Go</button></form>""",
     [ann("form-placeholder-only-1", "forms", "#search-q", "placeholder_as_label", "3.3.2", "The only label is a placeholder, which disappears on input and is unreliable as a name.")])
case("contrast-low", "injected", "Light grey text on white.", """
<h1>Terms</h1><p>Please read the terms before continuing.</p><p id="fine-print" style="color:#b5b5b5">Fine print: fees may apply to some transactions.</p>""",
     [ann("contrast-low-1", "contrast", "#fine-print", "low_contrast_text", "1.4.3", "#b5b5b5 on #ffffff is about 2.1:1, below the 4.5:1 minimum.")])
case("semantics-fake-heading", "injected", "A section title is a styled div, not a heading.", """
<h1>Services</h1><div id="section-title" style="font-size:28px;font-weight:700">Our Services</div><p>We build, maintain and host websites.</p>""",
     [ann("semantics-fake-heading-1", "semantics", "#section-title", "visual_heading_without_semantics", "1.3.1", "Large bold text acts as a heading visually but exposes no heading semantics.")])
case("button-label-mismatch", "injected", "Visible button label differs from its accessible name.", """
<h1>Catalogue</h1><button id="search-btn" type="button" aria-label="Submit form">Search</button>""",
     [ann("button-label-mismatch-1", "semantics", "#search-btn", "label_in_name", "2.5.3", "Visible text 'Search' is not part of the accessible name 'Submit form'.")])
case("heading-skip", "injected", "Heading levels jump from h1 to h4.", """
<h1>Handbook</h1><p>Intro.</p><h4 id="skipped">Safety procedures</h4><p>Details.</p>""",
     [ann("heading-skip-1", "semantics", "#skipped", "heading_level_skip", "1.3.1", "h4 follows h1 with no intermediate levels.")])
case("lang-missing", "injected", "Document has no lang attribute.", "<h1>Welcome</h1><p>Hello.</p>", lang="",
     anns=[ann("lang-missing-1", "semantics", "html", "missing_lang", "3.1.1", "<html> has no lang attribute.")])
case("title-missing", "injected", "Document has no <title>.", "<h1>Welcome</h1><p>Hello.</p>", head_title=False,
     anns=[ann("title-missing-1", "semantics", "html", "missing_title", "2.4.2", "The document has no <title>.")])

# ---- naturalistic-STYLE (hand-written, not scraped; labelled honestly) ----
case("mixed-blog", "naturalistic_style", "Hand-written blog post imitating real-world mixed defects (NOT a scraped real page).", f"""
<h1>Spring garden diary</h1><p id="post-meta" style="color:#aaa">Posted by Sam on 3 April</p>
<img id="blog-hero" src="{C}" alt="photo" width="320" height="180"><p>The beds are finally ready. Sources are listed <a id="src-link" href="#sources">here</a>.</p>
<h2>Comments</h2><form action="#" onsubmit="return false"><textarea id="comment-box" name="comment" rows="3"></textarea><button type="submit">Post comment</button></form>""",
     [ann("mixed-blog-1", "contrast", "#post-meta", "low_contrast_text", "1.4.3", "#aaa on white is about 2.3:1."),
      ann("mixed-blog-2", "images", "#blog-hero", "vague_alt", "1.1.1", "alt 'photo' says nothing about the image."),
      ann("mixed-blog-3", "navigation", "#src-link", "generic_link_text", "2.4.4", "'here' is meaningless out of context."),
      ann("mixed-blog-4", "forms", "#comment-box", "missing_label", "3.3.2", "textarea has no label.")])

dataset = {
    "name": "accessaudit-fixtures", "version": "1.0",
    "description": "Controlled, locally hosted HTML fixtures: accessible baselines, deliberately injected single-defect pages and one hand-written naturalistic-style page. EXPLORATORY: small and synthetic; results do not generalise to real websites.",
    "annotation_protocol": "Each annotation names the affected element (canonical selector), a category, an optional WCAG 2.2 criterion and a rationale. Defects were injected by the author, so labels exist before any tool is run. Only intended defects are annotated; baseline pages have no annotations. Annotators: 1 (the author). No second reviewer yet, so inter-annotator agreement is NOT available.",
    "cases": CASES,
}
(HERE / "dataset.json").write_text(json.dumps(dataset, indent=2) + "\n")
print(f"{len(CASES)} pages, {sum(len(c['annotations']) for c in CASES)} annotations")
