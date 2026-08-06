"""Automated Pine Script version migration (v4 -> v5 -> v6)."""

from __future__ import annotations

import re

from pydantic import BaseModel

from pinesprout.core.version_rules import (
    MIGRATIONS_V4_TO_V5,
    MIGRATIONS_V5_TO_V6,
    Migration,
)

_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)")


class AppliedMigration(BaseModel):
    description: str
    from_version: int
    to_version: int
    occurrences: int


class UpgradeResult(BaseModel):
    file: str
    original_version: int | None
    target_version: int
    final_version: int
    upgraded_source: str
    applied_migrations: list[AppliedMigration]
    manual_review_needed: list[str]


def detect_version(source: str) -> int | None:
    m = _VERSION_RE.search(source)
    return int(m.group(1)) if m else None


def _apply_migrations(source: str, migrations: list[Migration]) -> tuple[str, list[AppliedMigration]]:
    applied: list[AppliedMigration] = []
    for mig in migrations:
        pattern = re.compile(mig.pattern)
        count = len(pattern.findall(source))
        if count:
            source = pattern.sub(mig.replacement, source)
            applied.append(
                AppliedMigration(
                    description=mig.description,
                    from_version=mig.from_version,
                    to_version=mig.to_version,
                    occurrences=count,
                )
            )
    return source, applied


def upgrade_source(source: str, target_version: int = 6, file: str = "<memory>") -> UpgradeResult:
    """Upgrade Pine Script source toward ``target_version`` (5 or 6)."""
    original_version = detect_version(source)
    current_version = original_version or 4
    current_source = source
    all_applied: list[AppliedMigration] = []
    manual_review: list[str] = []

    if current_version <= 4 and target_version >= 5:
        current_source, applied = _apply_migrations(current_source, MIGRATIONS_V4_TO_V5)
        all_applied.extend(applied)
        current_version = 5
        manual_review.append(
            "v4->v5: `study()` alertcondition/security signatures changed subtly; "
            "verify `request.security()` arguments (esp. `lookahead`) after migration."
        )
        manual_review.append(
            "v4->v5: variable declarations now require explicit type qualification in some "
            "contexts (e.g. `plotchar`); review compiler warnings after migration."
        )

    if current_version <= 5 and target_version >= 6:
        current_source, applied = _apply_migrations(current_source, MIGRATIONS_V5_TO_V6)
        all_applied.extend(applied)
        current_version = 6
        manual_review.append(
            "v5->v6: review new `strategy.closedtrades.*` accessors if you rely on "
            "`strategy.performance`-style aggregate stats."
        )

    if detect_version(current_source) is None:
        current_source = f"//@version={current_version}\n" + current_source

    return UpgradeResult(
        file=file,
        original_version=original_version,
        target_version=target_version,
        final_version=current_version,
        upgraded_source=current_source,
        applied_migrations=all_applied,
        manual_review_needed=manual_review,
    )
