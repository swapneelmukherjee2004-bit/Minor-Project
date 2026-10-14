"""WCAG 2.2 Level A/AA success criteria (reference list supplied to the AI and used to validate output).

Source: W3C Recommendation "Web Content Accessibility Guidelines (WCAG) 2.2" https://www.w3.org/TR/WCAG22/
(4.1.1 Parsing was removed in 2.2.)
"""
WCAG22_AA: dict[str, tuple[str, str]] = {
    "1.1.1": ("Non-text Content", "A"), "1.2.1": ("Audio-only and Video-only (Prerecorded)", "A"),
    "1.2.2": ("Captions (Prerecorded)", "A"), "1.2.3": ("Audio Description or Media Alternative (Prerecorded)", "A"),
    "1.2.4": ("Captions (Live)", "AA"), "1.2.5": ("Audio Description (Prerecorded)", "AA"),
    "1.3.1": ("Info and Relationships", "A"), "1.3.2": ("Meaningful Sequence", "A"),
    "1.3.3": ("Sensory Characteristics", "A"), "1.3.4": ("Orientation", "AA"),
    "1.3.5": ("Identify Input Purpose", "AA"), "1.4.1": ("Use of Color", "A"),
    "1.4.2": ("Audio Control", "A"), "1.4.3": ("Contrast (Minimum)", "AA"),
    "1.4.4": ("Resize Text", "AA"), "1.4.5": ("Images of Text", "AA"),
    "1.4.10": ("Reflow", "AA"), "1.4.11": ("Non-text Contrast", "AA"),
    "1.4.12": ("Text Spacing", "AA"), "1.4.13": ("Content on Hover or Focus", "AA"),
    "2.1.1": ("Keyboard", "A"), "2.1.2": ("No Keyboard Trap", "A"), "2.1.4": ("Character Key Shortcuts", "A"),
    "2.2.1": ("Timing Adjustable", "A"), "2.2.2": ("Pause, Stop, Hide", "A"),
    "2.3.1": ("Three Flashes or Below Threshold", "A"), "2.4.1": ("Bypass Blocks", "A"),
    "2.4.2": ("Page Titled", "A"), "2.4.3": ("Focus Order", "A"), "2.4.4": ("Link Purpose (In Context)", "A"),
    "2.4.5": ("Multiple Ways", "AA"), "2.4.6": ("Headings and Labels", "AA"), "2.4.7": ("Focus Visible", "AA"),
    "2.4.11": ("Focus Not Obscured (Minimum)", "AA"), "2.5.1": ("Pointer Gestures", "A"),
    "2.5.2": ("Pointer Cancellation", "A"), "2.5.3": ("Label in Name", "A"), "2.5.4": ("Motion Actuation", "A"),
    "2.5.7": ("Dragging Movements", "AA"), "2.5.8": ("Target Size (Minimum)", "AA"),
    "3.1.1": ("Language of Page", "A"), "3.1.2": ("Language of Parts", "AA"), "3.2.1": ("On Focus", "A"),
    "3.2.2": ("On Input", "A"), "3.2.3": ("Consistent Navigation", "AA"), "3.2.4": ("Consistent Identification", "AA"),
    "3.2.6": ("Consistent Help", "A"), "3.3.1": ("Error Identification", "A"), "3.3.2": ("Labels or Instructions", "A"),
    "3.3.3": ("Error Suggestion", "AA"), "3.3.4": ("Error Prevention (Legal, Financial, Data)", "AA"),
    "3.3.7": ("Redundant Entry", "A"), "3.3.8": ("Accessible Authentication (Minimum)", "AA"),
    "4.1.2": ("Name, Role, Value", "A"), "4.1.3": ("Status Messages", "AA"),
}

AXE_RUN_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


def is_valid_criterion(sc: str) -> bool:
    return sc in WCAG22_AA


def axe_tag_to_criterion(tag: str) -> str | None:
    """'wcag143' -> '1.4.3', 'wcag2411' -> '2.4.11'. Returns None for level tags like 'wcag2aa'."""
    if not tag.startswith("wcag") or not tag[4:].isdigit() or len(tag) < 7:
        return None
    digits = tag[4:]
    sc = f"{digits[0]}.{digits[1]}.{digits[2:]}"
    return sc if sc in WCAG22_AA else None


def reference_text() -> str:
    return "\n".join(f"{k} {v[0]} (Level {v[1]})" for k, v in WCAG22_AA.items())
