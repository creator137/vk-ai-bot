from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class VkCallbackPayload(BaseModel):
    type: str = Field(min_length=1, max_length=128)
    group_id: int = Field(gt=0)
    event_id: str | None = Field(default=None, min_length=1)
    secret: str | None = Field(default=None, min_length=1)
    object: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class NormalizedVkEvent(BaseModel):
    source: Literal["vk"] = "vk"
    event_type: str
    group_id: int
    event_id: str | None = None
    actor_id: int | None = None
    peer_id: int | None = None
    occurred_at: int | None = None
    payload: dict[str, Any]

