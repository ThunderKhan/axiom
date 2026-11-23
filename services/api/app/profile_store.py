"""Server-authorized immutable profile versions and resumable workspace drafts."""

from __future__ import annotations

from datetime import UTC
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth import VerifiedPrincipal
from app.database import Database
from app.models import ProductProfile, ProfileVersion, Workspace
from app.profile_contract import ProfileAnswers
from app.workspace_store import VersionConflict, WorkspaceNotFound, WorkspaceStore


class ProfileIncomplete(Exception):
    """A draft cannot be confirmed without its minimum usable founder context."""


class ProfileStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _owned(session: Session, principal: VerifiedPrincipal, workspace_id: UUID) -> None:
        WorkspaceStore._active(session, principal)
        owned = session.scalar(
            select(Workspace.id).where(
                Workspace.id == workspace_id,
                Workspace.owner_user_id == principal.user_id,
            )
        )
        if owned is None:
            # Missing and foreign workspace IDs must be externally indistinguishable.
            raise WorkspaceNotFound()

    @staticmethod
    def _state(session: Session, workspace_id: UUID, profile: ProductProfile | None) -> dict[str, object]:
        if profile is None:
            return {
                "draft_revision": 0,
                "answers": None,
                "confirmed_revision": 0,
                "confirmed": None,
            }
        latest: ProfileVersion | None = None
        if profile.confirmed_revision:
            latest = session.scalar(
                select(ProfileVersion).where(
                    ProfileVersion.workspace_id == workspace_id,
                    ProfileVersion.revision == profile.confirmed_revision,
                )
            )
            if latest is None:
                raise RuntimeError("A confirmed profile revision is missing")
        return {
            "draft_revision": profile.draft_revision,
            "answers": profile.draft_answers,
            "confirmed_revision": profile.confirmed_revision,
            "confirmed": (
                {
                    "id": latest.id,
                    "revision": latest.revision,
                    "answers": latest.answers,
                    "confirmed_at": latest.confirmed_at.astimezone(UTC),
                }
                if latest is not None
                else None
            ),
        }

    def read(self, principal: VerifiedPrincipal, workspace_id: UUID) -> dict[str, object]:
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            profile = session.get(ProductProfile, workspace_id)
            return self._state(session, workspace_id, profile)

    def save(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        *,
        answers: ProfileAnswers,
        expected_revision: int,
    ) -> dict[str, object]:
        if type(expected_revision) is not int or not 0 <= expected_revision < 9223372036854775807:
            raise VersionConflict()
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            # Serialize concurrent first drafts at the unique workspace PK, then row-lock.
            session.execute(
                insert(ProductProfile)
                .values(workspace_id=workspace_id)
                .on_conflict_do_nothing(index_elements=[ProductProfile.workspace_id])
            )
            profile = session.scalar(
                select(ProductProfile)
                .where(ProductProfile.workspace_id == workspace_id)
                .with_for_update()
            )
            assert profile is not None
            if profile.draft_revision != expected_revision:
                raise VersionConflict()
            profile.draft_answers = answers.model_dump(mode="json")
            profile.draft_revision += 1
            profile.updated_at = session.scalar(select(func.clock_timestamp()))
            session.flush()
            return self._state(session, workspace_id, profile)

    def confirm(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        *,
        expected_revision: int,
    ) -> dict[str, object]:
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            profile = session.scalar(
                select(ProductProfile)
                .where(ProductProfile.workspace_id == workspace_id)
                .with_for_update()
            )
            if profile is None:
                raise ProfileIncomplete()
            if profile.draft_revision != expected_revision:
                raise VersionConflict()
            answers = ProfileAnswers.model_validate(profile.draft_answers)
            if not answers.confirmable():
                raise ProfileIncomplete()
            version = ProfileVersion(
                id=uuid4(),
                workspace_id=workspace_id,
                revision=profile.confirmed_revision + 1,
                answers=answers.model_dump(mode="json"),
            )
            session.add(version)
            profile.confirmed_revision += 1
            # Prevent re-confirming after a lost POST response using the old revision.
            profile.draft_revision += 1
            profile.updated_at = session.scalar(select(func.clock_timestamp()))
            session.flush()
            return self._state(session, workspace_id, profile)
