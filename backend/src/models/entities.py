from datetime import datetime
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(16))


class Segment(Base):
    __tablename__ = 'segments'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(100))
    bank: Mapped[str] = mapped_column(String(40))
    stable: Mapped[bool]


class Capture(Base):
    __tablename__ = 'survey_captures'
    __table_args__ = (UniqueConstraint('segment_code', 'campaign', 'round_code', 'asset_code', name='uq_capture_natural'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    segment_code: Mapped[str] = mapped_column(ForeignKey('segments.code'))
    campaign: Mapped[str] = mapped_column(String(32), index=True)
    round_code: Mapped[str] = mapped_column(String(1))
    asset_code: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(12))


class Analysis(Base):
    __tablename__ = 'coverage_plans'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(16), index=True)
    parameters: Mapped[dict] = mapped_column(JSON)
    snapshot: Mapped[list] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Audit(Base):
    __tablename__ = 'audits'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(40))
    subject: Mapped[str] = mapped_column(String(100))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SamplingPlan(Base):
    __tablename__ = 'audit_sampling_plans'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    campaign: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    seed: Mapped[int]
    confidence: Mapped[float]
    locked_snapshot: Mapped[dict] = mapped_column(JSON)
    strata: Mapped[list] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RecountReturn(Base):
    __tablename__ = 'audit_recount_returns'
    __table_args__ = (UniqueConstraint('plan_id', 'segment_code', name='uq_recount_segment'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey('audit_sampling_plans.id'), index=True)
    segment_code: Mapped[str] = mapped_column(ForeignKey('segments.code'))
    state: Mapped[str] = mapped_column(String(12), index=True)
    total_found: Mapped[int | None]
    asset_codes: Mapped[list] = mapped_column(JSON)
    missing_locked: Mapped[list] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text, default='')
    reporter: Mapped[str] = mapped_column(String(120), default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
