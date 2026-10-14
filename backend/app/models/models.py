"""SQLAlchemy 2.x models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    url: Mapped[str] = mapped_column(String(2048))
    host: Mapped[str] = mapped_column(String(255), index=True)
    final_url: Mapped[str | None] = mapped_column(String(2048))
    mode: Mapped[str] = mapped_column(String(16))  # conventional | ai | combined
    source: Mapped[str] = mapped_column(String(16), default="user", index=True)  # user | evaluation
    status: Mapped[str] = mapped_column(String(16), index=True, default="queued")
    stage: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    ai_error: Mapped[str | None] = mapped_column(Text)
    capture_screenshot: Mapped[bool] = mapped_column(Boolean, default=True)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_provider: Mapped[str | None] = mapped_column(String(32))
    ai_model: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    page_title: Mapped[str | None] = mapped_column(String(512))
    http_status: Mapped[int | None] = mapped_column(Integer)
    screenshot_key: Mapped[str | None] = mapped_column(String(128))
    screenshot_width: Mapped[int | None] = mapped_column(Integer)
    screenshot_height: Mapped[int | None] = mapped_column(Integer)
    tool_versions: Mapped[dict | None] = mapped_column(JSON)
    config: Mapped[dict | None] = mapped_column(JSON)
    dom_context: Mapped[dict | None] = mapped_column(JSON)  # bounded evidence used for AI
    ai_rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    findings: Mapped[list["Finding"]] = relationship(back_populates="audit", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (Index("ix_findings_audit_method", "audit_id", "method"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(16))  # axe | custom | ai
    rule_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24))  # confirmed | suspected | needs_manual_review
    verification_method: Mapped[str] = mapped_column(String(24))
    wcag_criteria: Mapped[list] = mapped_column(JSON, default=list)
    selector: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    user_impact: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    help_url: Mapped[str | None] = mapped_column(String(512))
    group_id: Mapped[int | None] = mapped_column(Integer)  # normalization/match group within the audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    audit: Mapped[Audit] = relationship(back_populates="findings")


class EvalDataset(Base):
    __tablename__ = "eval_datasets"
    __table_args__ = (UniqueConstraint("name", "version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="")
    annotation_protocol: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    cases: Mapped[list["EvalCase"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class EvalCase(Base):
    __tablename__ = "eval_cases"
    __table_args__ = (UniqueConstraint("dataset_id", "page_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("eval_datasets.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[str] = mapped_column(String(64))
    condition: Mapped[str] = mapped_column(String(32))  # baseline | injected | naturalistic
    fixture_file: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")

    dataset: Mapped[EvalDataset] = relationship(back_populates="cases")
    annotations: Mapped[list["GroundTruth"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class GroundTruth(Base):
    __tablename__ = "ground_truth"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("eval_cases.id", ondelete="CASCADE"), index=True)
    annotation_id: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))
    target_selector: Mapped[str] = mapped_column(String(256))  # canonical selector of the affected component, e.g. "#hero-img"
    issue_type: Mapped[str] = mapped_column(String(64))
    criterion: Mapped[str | None] = mapped_column(String(16))
    rationale: Mapped[str] = mapped_column(Text, default="")
    provenance: Mapped[str] = mapped_column(Text, default="")
    # Whether a rule-based tool is expected to be able to detect it (annotator judgement, informational)
    second_reviewer_label: Mapped[str | None] = mapped_column(String(16))  # "issue" | "no_issue" | None

    case: Mapped[EvalCase] = relationship(back_populates="annotations")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("eval_datasets.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    error: Mapped[str | None] = mapped_column(Text)
    ai_provider: Mapped[str] = mapped_column(String(32))
    ai_model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(32))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict | None] = mapped_column(JSON)
    details: Mapped[dict | None] = mapped_column(JSON)  # per-case matching details, overlap, confusion matrix
    reviewer_agreement: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    results: Mapped[list["EvalResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(16))  # conventional | ai | combined
    scope: Mapped[str] = mapped_column(String(16))  # finding | page
    category: Mapped[str] = mapped_column(String(32), default="all")
    tp: Mapped[int] = mapped_column(Integer, default=0)
    fp: Mapped[int] = mapped_column(Integer, default=0)
    fn: Mapped[int] = mapped_column(Integer, default=0)
    tn: Mapped[int | None] = mapped_column(Integer)
    precision: Mapped[float | None] = mapped_column(Float)
    recall: Mapped[float | None] = mapped_column(Float)
    f1: Mapped[float | None] = mapped_column(Float)

    run: Mapped[EvalRun] = relationship(back_populates="results")
