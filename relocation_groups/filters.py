"""Фильтрация и ранжирование найденных групп."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .models import Group
from .queries import RELOCATION_WORDS, detect_country


def relevance(g: Group) -> float:
    low = g.text.lower()
    return float(sum(1 for w in RELOCATION_WORDS if w in low))


def enrich(g: Group) -> Group:
    g.country = detect_country(g.text)
    return g


def score(g: Group, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    s = relevance(g) * 2
    s += math.log10(g.members + 1) if g.members else 0
    s += min(len(g.found_by), 5) * 0.5  # нашли по нескольким запросам
    if g.last_activity:
        days = (now - g.last_activity).days
        s += 3 if days <= 7 else 1.5 if days <= 30 else -2
    return round(s, 2)


def apply_filters(
    groups: list[Group],
    min_members: int = 0,
    max_inactive_days: int | None = None,
    country: str | None = None,
    min_relevance: float = 1,
) -> list[Group]:
    now = datetime.now(timezone.utc)
    out = []
    for g in groups:
        enrich(g)
        if relevance(g) < min_relevance:
            continue
        if g.members is not None and g.members < min_members:
            continue
        if country and g.country != country:
            continue
        if max_inactive_days is not None and g.last_activity is not None:
            if now - g.last_activity > timedelta(days=max_inactive_days):
                continue
        g.score = score(g, now)
        out.append(g)
    return sorted(out, key=lambda g: g.score, reverse=True)


def merge(groups: list[Group]) -> list[Group]:
    """Склеивает дубликаты (одна группа найдена по разным запросам)."""
    seen: dict[tuple[str, str], Group] = {}
    for g in groups:
        if g.key in seen:
            seen[g.key].found_by |= g.found_by
        else:
            seen[g.key] = g
    return list(seen.values())
