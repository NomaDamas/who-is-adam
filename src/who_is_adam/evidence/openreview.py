"""OpenReview public-evidence lookup.

This module only returns public metadata/text explicitly provided by OpenReview. It never infers
review content, strengths, weaknesses, or prior-work judgments when public evidence is absent.
"""

from __future__ import annotations

import httpx
from rapidfuzz import fuzz

from who_is_adam.config import ReviewConfig
from who_is_adam.models import (
    OpenReviewReviewAssessment,
    ProviderEvidence,
    ProviderStatus,
    ReferenceEntry,
)

from .citations import ProviderResult, make_provider_http_client


class OpenReviewClient:
    def __init__(self, config: ReviewConfig, *, client: httpx.Client | None = None) -> None:
        self.http = make_provider_http_client(
            "openreview", config.openreview, offline=config.offline, client=client
        )

    def public_evidence_for_reference(self, reference: ReferenceEntry) -> ProviderEvidence:
        if not reference.title:
            return ProviderResult("openreview", ProviderStatus.UNAVAILABLE, "reference has no parsed title").evidence()
        data, error = self.http.get_json("notes", params={"content.title": reference.title, "limit": 5})
        if error:
            return error.evidence()
        notes = (data or {}).get("notes")
        if not isinstance(notes, list) or not notes:
            return ProviderResult("openreview", ProviderStatus.UNAVAILABLE, "no public OpenReview note found").evidence()
        best = self._best_note(reference.title, notes)
        if best is None:
            return ProviderResult("openreview", ProviderStatus.UNAVAILABLE, "OpenReview response had no usable public title").evidence()
        note, score = best
        if score < 75:
            return ProviderResult(
                "openreview",
                ProviderStatus.UNAVAILABLE,
                "public OpenReview note did not match reference title",
                metadata={"title_score": float(score)},
            ).evidence()
        metadata = self._public_metadata(note)
        metadata["title_score"] = float(score)
        url = self._note_url(note)
        status = ProviderStatus.VERIFIED if score >= 92 else ProviderStatus.WEAK_MATCH
        diagnostic = None if status is ProviderStatus.VERIFIED else "public OpenReview title weakly matched"
        return ProviderResult("openreview", status, diagnostic, url, metadata).evidence()

    def public_review_assessment_for_evidence(
        self,
        evidence: ProviderEvidence,
    ) -> OpenReviewReviewAssessment | None:
        forum = evidence.metadata.get("forum") or evidence.metadata.get("id")
        if not isinstance(forum, str) or not forum:
            return None
        data, error = self.http.get_json("notes", params={"forum": forum, "limit": 50})
        if error:
            return None
        notes = (data or {}).get("notes")
        if not isinstance(notes, list) or not notes:
            return None
        return _review_assessment_from_notes(notes)

    @staticmethod
    def _best_note(title: str, notes: list[object]) -> tuple[dict[str, object], float] | None:
        best: tuple[dict[str, object], float] | None = None
        for note in notes:
            if not isinstance(note, dict):
                continue
            note_title = _content_value(note, "title")
            if not isinstance(note_title, str):
                continue
            score = float(fuzz.token_set_ratio(title.casefold(), note_title.casefold()))
            if best is None or score > best[1]:
                best = (note, score)
        return best

    @staticmethod
    def _public_metadata(note: dict[str, object]) -> dict[str, str | int | float | bool | None]:
        metadata: dict[str, str | int | float | bool | None] = {}
        for key in ("id", "forum", "venue", "venueid", "invitation", "cdate", "mdate"):
            value = note.get(key)
            if isinstance(value, str | int | float | bool) or value is None:
                metadata[key] = value
        title = _content_value(note, "title")
        if isinstance(title, str):
            metadata["title"] = title
        abstract = _content_value(note, "abstract")
        if isinstance(abstract, str):
            metadata["abstract_available"] = bool(abstract.strip())
        return metadata

    @staticmethod
    def _note_url(note: dict[str, object]) -> str | None:
        forum = note.get("forum") or note.get("id")
        return f"https://openreview.net/forum?id={forum}" if isinstance(forum, str) and forum else None


def public_openreview_evidence(
    reference: ReferenceEntry, config: ReviewConfig, *, client: httpx.Client | None = None
) -> ProviderEvidence:
    return OpenReviewClient(config, client=client).public_evidence_for_reference(reference)


def _review_assessment_from_notes(notes: list[object]) -> OpenReviewReviewAssessment | None:
    strengths: list[str] = []
    weaknesses: list[str] = []
    review_count = 0
    for note in notes:
        if not isinstance(note, dict) or not _is_public_review_note(note):
            continue
        review_count += 1
        strengths.extend(_content_texts(note, ("strengths", "strength", "summary_of_strengths")))
        weaknesses.extend(_content_texts(note, ("weaknesses", "weakness", "summary_of_weaknesses")))
    if review_count == 0:
        return None
    return OpenReviewReviewAssessment(
        strengths=_dedupe_nonempty(strengths),
        weaknesses=_dedupe_nonempty(weaknesses),
        review_count=review_count,
    )


def _is_public_review_note(note: object) -> bool:
    if not isinstance(note, dict):
        return False
    content = note.get("content")
    if not isinstance(content, dict):
        return False
    invitation = note.get("invitation")
    has_review_invitation = isinstance(invitation, str) and "review" in invitation.casefold()
    has_review_fields = any(key in content for key in ("strengths", "weaknesses", "strength", "weakness"))
    return has_review_invitation or has_review_fields


def _content_texts(note: dict[str, object], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for key in keys:
        value = _content_value(note, key)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
    return values


def _dedupe_nonempty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = " ".join(value.split())
        folded = cleaned.casefold()
        if cleaned and folded not in seen:
            seen.add(folded)
            deduped.append(cleaned)
    return deduped


def _content_value(note: dict[str, object], key: str) -> object:
    content = note.get("content")
    if not isinstance(content, dict):
        return None
    value = content.get(key)
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


__all__ = ["OpenReviewClient", "public_openreview_evidence"]
