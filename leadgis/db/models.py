"""SQLAlchemy 2.0 ORM models. See AGENT.md §5 for the authoritative schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    COLLECTING = "collecting"
    READY = "ready"
    FAILED = "failed"


class WebsiteStatus(StrEnum):
    NONE = "none"
    DEAD = "dead"
    ALIVE = "alive"
    UNKNOWN = "unknown"


class LeadStatus(StrEnum):
    NEW = "new"
    MESSAGE_READY = "message_ready"
    SENT = "sent"
    REPLIED = "replied"
    CLIENT = "client"
    REJECTED = "rejected"


class JobKind(StrEnum):
    COLLECT = "collect"
    GENERATE = "generate"
    ENRICH = "enrich"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    niche: Mapped[str]
    city: Mapped[str]
    source: Mapped[str]
    status: Mapped[str] = mapped_column(default=CampaignStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    leads: Mapped[list[Lead]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("campaign_id", "external_id", name="uq_lead_campaign_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    external_id: Mapped[str | None]
    name: Mapped[str]
    category: Mapped[str | None]
    address: Mapped[str | None]
    phone_e164: Mapped[str | None]
    phones_raw: Mapped[str | None]
    website: Mapped[str | None]
    website_status: Mapped[str] = mapped_column(default=WebsiteStatus.UNKNOWN)
    whatsapp_url: Mapped[str | None]
    telegram_url: Mapped[str | None]
    instagram_url: Mapped[str | None]
    rating: Mapped[float | None]
    reviews_count: Mapped[int | None]
    status: Mapped[str] = mapped_column(default=LeadStatus.NEW)
    raw_json: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped[Campaign] = relationship(back_populates="leads")
    messages: Mapped[list[Message]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    text: Mapped[str]
    provider: Mapped[str]
    model: Mapped[str]
    prompt_template: Mapped[str]
    tokens_in: Mapped[int | None]
    tokens_out: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_current: Mapped[bool] = mapped_column(default=True)

    lead: Mapped[Lead] = relationship(back_populates="messages")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: uuid.uuid4().hex)
    kind: Mapped[str]
    campaign_id: Mapped[int | None]
    status: Mapped[str] = mapped_column(default=JobStatus.QUEUED)
    progress: Mapped[int] = mapped_column(default=0)
    detail: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None]


class KV(Base):
    """Small persisted key/value cache (e.g. resolved 2GIS city ids)."""

    __tablename__ = "kv"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]
