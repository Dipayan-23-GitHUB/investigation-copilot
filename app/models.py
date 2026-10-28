from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from .db import Base

def now_utc():
    return datetime.now(timezone.utc)

class Ingestion(Base):
    __tablename__ = "ingestions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="demo", index=True)
    module_key: Mapped[str] = mapped_column(String(80), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default="completed")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    sheet_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    sheets: Mapped[list["SourceSheet"]] = relationship(back_populates="ingestion", cascade="all, delete-orphan")

class SourceSheet(Base):
    __tablename__ = "source_sheets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("ingestions.id", ondelete="CASCADE"), index=True)
    sheet_name: Mapped[str] = mapped_column(String(160))
    source_object: Mapped[str] = mapped_column(String(200), default="Unmapped source")
    headers: Mapped[list] = mapped_column(JSON, default=list)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ingestion: Mapped[Ingestion] = relationship(back_populates="sheets")
    rows: Mapped[list["SourceRow"]] = relationship(back_populates="sheet", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_source_sheet_ingestion_name", "ingestion_id", "sheet_name"),)

class SourceRow(Base):
    __tablename__ = "source_rows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sheet_id: Mapped[str] = mapped_column(ForeignKey("source_sheets.id", ondelete="CASCADE"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSON)
    sheet: Mapped[SourceSheet] = relationship(back_populates="rows")
    __table_args__ = (Index("ix_source_row_sheet_row", "sheet_id", "row_number"),)

class ExceptionRecord(Base):
    __tablename__ = "exceptions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="demo", index=True)
    title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text, default="")
    material_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    impact_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    direction: Mapped[str] = mapped_column(String(20), default="unfavorable")
    priority: Mapped[str] = mapped_column(String(20), default="review", index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    root_cause_found: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    investigation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class ActionRecord(Base):
    __tablename__ = "actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="demo", index=True)
    exception_id: Mapped[str | None] = mapped_column(ForeignKey("exceptions.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(400))
    owner: Mapped[str] = mapped_column(String(160), default="Unassigned")
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    action_type: Mapped[str] = mapped_column(String(30), default="corrective")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

class ControlRecord(Base):
    __tablename__ = "controls"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    process_area: Mapped[str] = mapped_column(String(120))
    owner: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="proposed")
    recurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    exposure_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
