"""Pydantic schemas: API contracts and the strict AI output schema."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Category = Literal["images", "navigation", "forms", "contrast", "semantics", "readability", "other"]
Severity = Literal["critical", "high", "medium", "low", "info"]
FindingStatus = Literal["confirmed", "suspected", "needs_manual_review"]
Verification = Literal["automated", "AI_inference", "manual_review"]
Method = Literal["axe", "custom", "ai"]
AuditMode = Literal["conventional", "ai", "combined"]
AuditStatus = Literal["queued", "running", "completed", "failed"]

Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=600)]
Long = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


# ---------- AI output (strict) ----------
class AIFinding(BaseModel):
    """One finding as returned by the model. The server — not the model — supplies selector/HTML evidence
    by resolving `element_ref` against the extracted DOM context."""
    model_config = ConfigDict(extra="ignore")

    title: Short = Field(min_length=3)
    description: Long = Field(min_length=3)
    category: Category
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    status: FindingStatus
    wcag_criteria: list[str] = Field(default_factory=list, max_length=6)
    element_ref: str | None = Field(default=None, max_length=16)
    screenshot_observation: Long = ""
    dom_observation: Long = ""
    user_impact: Long = ""
    recommendation: Long = ""
    verification_method: Verification = "AI_inference"

    @field_validator("wcag_criteria", mode="before")
    @classmethod
    def _coerce_wcag(cls, v):
        return [str(x).strip() for x in v] if isinstance(v, list) else []


class AIResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    findings: list[dict] = Field(default_factory=list, max_length=60)


# ---------- API ----------
class AuditCreate(BaseModel):
    url: str = Field(min_length=4, max_length=2048)
    mode: AuditMode = "combined"
    capture_screenshot: bool = True

    @field_validator("url")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class Evidence(BaseModel):
    screenshot_observation: str = ""
    dom_observation: str = ""
    html_excerpt: str = ""
    selector: str = ""
    extra: dict = Field(default_factory=dict)


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    audit_id: str
    method: Method
    rule_id: str
    title: str
    description: str
    category: Category
    severity: Severity
    confidence: float | None
    status: FindingStatus
    verification_method: Verification
    wcag_criteria: list[str]
    selector: str | None
    evidence: dict
    user_impact: str
    recommendation: str
    help_url: str | None
    group_id: int | None


class AuditSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    url: str
    host: str
    mode: AuditMode
    status: AuditStatus
    stage: str | None
    demo_mode: bool
    page_title: str | None
    created_at: datetime
    completed_at: datetime | None
    finding_count: int = 0


class AuditDetail(AuditSummary):
    final_url: str | None
    error: str | None
    ai_error: str | None
    capture_screenshot: bool
    has_screenshot: bool
    screenshot_width: int | None
    screenshot_height: int | None
    ai_provider: str | None
    ai_model: str | None
    prompt_version: str | None
    http_status: int | None
    tool_versions: dict | None
    config: dict | None
    ai_rejected_count: int
    started_at: datetime | None


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


class ErrorBody(BaseModel):
    error: dict
