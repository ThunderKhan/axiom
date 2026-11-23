"""Validated, provider-independent onboarding contract (MVP-03 / UF-03)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Stage = Literal["idea", "live"]


class ProfileAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    stage: Stage | None = None
    name: str = Field(default="", max_length=120)
    problem: str = Field(default="", max_length=2000)
    audience: str = Field(default="", max_length=1000)
    industry: str = Field(default="", max_length=300)
    geography: str = Field(default="", max_length=300)
    alternatives: str = Field(default="", max_length=1000)
    capabilities: str = Field(default="", max_length=2000)
    missing_capabilities: str = Field(default="", max_length=1000)
    differentiators: str = Field(default="", max_length=1000)
    pricing_hypothesis: str = Field(default="", max_length=500)
    website_url: str = Field(default="", max_length=2048)
    competitors: str = Field(default="", max_length=1000)
    desired_signals: str = Field(default="", max_length=1000)
    restrictions: str = Field(default="", max_length=1000)

    @field_validator("website_url")
    @classmethod
    def valid_unfetched_site(cls, value: str) -> str:
        # Stored only as an unverified user declaration; never fetched by onboarding.
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Only HTTP(S) websites are accepted")
        return value

    def confirmable(self) -> bool:
        return bool(
            self.stage is not None
            and self.name.strip()
            and self.problem.strip()
            and self.audience.strip()
            and self.capabilities.strip()
        )
