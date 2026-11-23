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
