"""Workspace-authorized manual-source CRM records and atomic metadata history."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth import VerifiedPrincipal
from app.database import Database
from app.leads_contract import CreateLead, PatchLead, validate_idempotency_key
from app.models import Lead, LeadEvent
from app.profile_store import ProfileStore
from app.workspace_store import IdempotencyConflict, VersionConflict, WorkspaceNotFound

MAX_VERSION = 9223372036854775807


class InvalidLeadInput(ValueError):
    """Reject inconsistent follow-up transitions or invalid request parameters."""


def _payload(lead: Lead) -> dict[str, object]:
    return {
        "id": lead.id,
        "workspace_id": lead.workspace_id,
        "title": lead.title,
        "source_url": lead.source_url,
        "source_excerpt": lead.source_excerpt,
        "source_origin": lead.source_origin,
        "stage": lead.stage,
        "note": lead.note,
        "follow_up_at": lead.follow_up_at.astimezone(UTC) if lead.follow_up_at else None,
        "follow_up_done": lead.follow_up_done,
        "unsent_draft": lead.unsent_draft,
        "version": lead.version,
        "created_at": lead.created_at.astimezone(UTC),
        "updated_at": lead.updated_at.astimezone(UTC),
    }


class LeadStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _owned(session: Session, principal: VerifiedPrincipal, workspace_id: UUID) -> None:
        ProfileStore._owned(session, principal, workspace_id)

    @staticmethod
    def _lead(session: Session, workspace_id: UUID, lead_id: UUID) -> Lead:
        # The explicit workspace predicate is mandatory even with RLS enabled.
        lead = session.scalar(
            select(Lead).where(
                Lead.id == lead_id,
                Lead.workspace_id == workspace_id,
                Lead.archived_at.is_(None),
            )
        )
        if lead is None:
            raise WorkspaceNotFound()
        return lead

    @staticmethod
    def _event(
        session: Session,
        principal: VerifiedPrincipal,
        lead: Lead,
        event_type: str,
        changed_fields: list[str],
    ) -> None:
        session.add(
            LeadEvent(
                id=uuid4(),
                workspace_id=lead.workspace_id,
                lead_id=lead.id,
                actor_id=principal.user_id,
                event_type=event_type,
                changed_fields=changed_fields,
            )
        )

    def create(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        *,
        payload: CreateLead,
        key: str,
    ) -> dict[str, object]:
        try:
            validate_idempotency_key(key)
        except ValueError as exc:
            raise InvalidLeadInput("Invalid idempotency key") from exc
        canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            lead_id = uuid4()
            inserted = session.execute(
                insert(Lead)
                .values(
                    id=lead_id,
                    workspace_id=workspace_id,
                    title=payload.title,
                    source_url=payload.source_url,
                    source_excerpt=payload.source_excerpt,
                    stage=payload.stage,
                    note=payload.note,
                    follow_up_at=payload.follow_up_at,
                    follow_up_done=payload.follow_up_done,
                    unsent_draft=payload.unsent_draft,
                    create_key=key,
                    create_fingerprint=fingerprint,
                )
                .on_conflict_do_nothing()
                .returning(Lead.id)
            ).scalar_one_or_none()
            if inserted is None:
                existing = session.scalar(
                    select(Lead).where(
                        Lead.workspace_id == workspace_id,
                        Lead.create_key == key,
                    )
                )
                if existing is not None:
                    if existing.create_fingerprint != fingerprint:
                        raise IdempotencyConflict()
                else:
                    existing = session.scalar(
                        select(Lead).where(
                            Lead.workspace_id == workspace_id,
                            Lead.source_url == payload.source_url,
                        )
                    )
                if existing is None:
                    raise RuntimeError("Conflicting lead is not visible to verified owner")
                if existing.archived_at is not None:
                    raise IdempotencyConflict()
                result = _payload(existing)
                result["already_exists"] = True
                return result
            lead = session.get(Lead, inserted)
            assert lead is not None
            self._event(session, principal, lead, "created", ["created"])
            session.flush()
            result = _payload(lead)
            result["already_exists"] = False
            return result

    def list(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        *,
        stage: str | None = None,
        query: str | None = None,
        limit: int = 20,
    ) -> dict[str, object]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise InvalidLeadInput("Invalid page limit")
        if stage is not None and stage not in {
            "spotted",
            "qualified",
            "contacted",
            "closed_lost",
        }:
            raise InvalidLeadInput("Unknown lead stage")
        if query is not None and (len(query) > 100 or "\x00" in query):
            raise InvalidLeadInput("Invalid search query")
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            statement = select(Lead).where(
                Lead.workspace_id == workspace_id,
                Lead.archived_at.is_(None),
            )
            if stage is not None:
                statement = statement.where(Lead.stage == stage)
            if query:
                escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                statement = statement.where(Lead.title.ilike(f"%{escaped}%", escape="\\"))
            leads = session.scalars(
                statement.order_by(Lead.created_at.desc(), Lead.id.desc()).limit(limit)
            ).all()
            return {"items": [_payload(lead) for lead in leads]}

    def read(self, principal: VerifiedPrincipal, workspace_id: UUID, lead_id: UUID) -> dict[str, object]:
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            return _payload(self._lead(session, workspace_id, lead_id))

    def patch(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        lead_id: UUID,
        *,
        payload: PatchLead,
    ) -> dict[str, object]:
        values = payload.model_dump(exclude_unset=True)
        values.pop("expected_version")
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            lead = session.scalar(
                select(Lead)
                .where(
                    Lead.id == lead_id,
                    Lead.workspace_id == workspace_id,
                    Lead.archived_at.is_(None),
                )
                .with_for_update()
            )
            if lead is None:
                raise WorkspaceNotFound()
            if lead.version != payload.expected_version or lead.version >= MAX_VERSION:
                raise VersionConflict()
            due_at = values.get("follow_up_at", lead.follow_up_at)
            completed = values.get("follow_up_done", lead.follow_up_done)
            if completed and due_at is None:
                raise InvalidLeadInput("Cannot complete an absent follow-up")
            for field, value in values.items():
                setattr(lead, field, value)
            lead.version += 1
            lead.updated_at = session.scalar(select(func.clock_timestamp()))
            self._event(session, principal, lead, "updated", sorted(values))
            session.flush()
            return _payload(lead)

    def archive(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        lead_id: UUID,
        *,
        expected_version: int,
    ) -> None:
        if type(expected_version) is not int or not 1 <= expected_version < MAX_VERSION:
            raise InvalidLeadInput("Invalid expected version")
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            lead = session.scalar(
                select(Lead)
                .where(
                    Lead.id == lead_id,
                    Lead.workspace_id == workspace_id,
                    Lead.archived_at.is_(None),
                )
                .with_for_update()
            )
            if lead is None:
                raise WorkspaceNotFound()
            if lead.version != expected_version:
                raise VersionConflict()
            now = session.scalar(select(func.clock_timestamp()))
            assert now is not None
            lead.archived_at = now
            lead.updated_at = now
            lead.version += 1
            self._event(session, principal, lead, "archived", ["archived_at"])
            session.flush()

    def history(
        self, principal: VerifiedPrincipal, workspace_id: UUID, lead_id: UUID
    ) -> list[dict[str, object]]:
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            self._lead(session, workspace_id, lead_id)
            events = session.scalars(
                select(LeadEvent)
                .where(LeadEvent.workspace_id == workspace_id, LeadEvent.lead_id == lead_id)
                .order_by(LeadEvent.created_at.desc(), LeadEvent.id.desc())
                .limit(100)
            ).all()
            return [
                {
                    "id": event.id,
                    "actor_id": event.actor_id,
                    "event_type": event.event_type,
                    "changed_fields": event.changed_fields,
                    "created_at": event.created_at.astimezone(UTC),
                }
                for event in events
            ]
