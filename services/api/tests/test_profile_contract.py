"""Onboarding values are declarations, not verified website or model facts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.profile_contract import ProfileAnswers


def test_draft_allows_skips_but_confirmation_requires_minimum_context() -> None:
    assert not ProfileAnswers().confirmable()
    assert not ProfileAnswers(stage="idea", name="Idea").confirmable()
    assert ProfileAnswers(
        stage="idea",
        name="Tool",
        problem="Missing offline access",
        audience="Students",
        capabilities="Proposed offline notes",
    ).confirmable()
    assert ProfileAnswers(
        stage="live",
        name="Product",
        problem="People lose notes",
        audience="Students",
        capabilities="Existing search feature",
    ).confirmable()


@pytest.mark.parametrize(
    "payload",
    [
        {"stage": "invented"},
        {"name": 23},
        {"website_url": "file:///etc/passwd"},
        {"website_url": "javascript:alert(1)"},
        {"unapproved_field": "unexpected"},
        {"problem": "x" * 2001},
        {"capabilities": "x" * 2001},
    ],
)
def test_unexpected_values_or_unsafe_url_schemes_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProfileAnswers.model_validate(payload)


def test_unconfirmed_website_url_is_stored_not_classified_as_verified() -> None:
    answers = ProfileAnswers(website_url="https://example.org/about", stage="idea")
    assert not answers.confirmable()
    assert answers.model_dump()["website_url"] == "https://example.org/about"


def test_all_individually_allowed_answer_lengths_do_not_hit_hidden_limit() -> None:
    answers = {
        "name": "n" * 120,
        "problem": "p" * 2000,
        "audience": "a" * 1000,
        "industry": "i" * 300,
        "geography": "g" * 300,
        "alternatives": "a" * 1000,
        "capabilities": "c" * 2000,
        "missing_capabilities": "m" * 1000,
        "differentiators": "d" * 1000,
        "pricing_hypothesis": "p" * 500,
        "website_url": "https://" + ("e" * 2040),
        "competitors": "c" * 1000,
        "desired_signals": "s" * 1000,
        "restrictions": "r" * 1000,
        "stage": "idea",
    }
    profile = ProfileAnswers.model_validate(answers)
    assert sum(len(value) for value in answers.values()) > 11000
    assert profile.confirmable()


def test_nul_character_rejected_before_postgresql_jsonb_insert() -> None:
    with pytest.raises(ValidationError, match="NUL"):
        ProfileAnswers.model_validate({"name": "Test\\u0000".replace("\\u0000", "\x00")})
    with pytest.raises(ValidationError, match="NUL"):
        ProfileAnswers.model_validate({"problem": "A" + chr(0) + "B"})
