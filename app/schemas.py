from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

class ActionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=400)
    owner: str = Field(default="Unassigned", max_length=160)
    status: Literal["open", "in_progress", "blocked", "completed", "planned"] = "open"
    due_date: str | None = None
    action_type: Literal["corrective", "preventive", "investigation"] = "corrective"
    exception_id: str | None = None

class ActionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=400)
    owner: str | None = Field(default=None, max_length=160)
    status: Literal["open", "in_progress", "blocked", "completed", "planned"] | None = None
    due_date: str | None = None
    action_type: Literal["corrective", "preventive", "investigation"] | None = None

class ChatRequest(BaseModel):
    exception_id: str
    message: str = Field(min_length=1, max_length=4000)
    conversation_history: list[dict[str, str]] = Field(default_factory=list, max_length=20)

class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    environment: str

class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    exception_id: str | None
    title: str
    owner: str
    status: str
    due_date: str | None
    action_type: str
    created_at: datetime
    updated_at: datetime
