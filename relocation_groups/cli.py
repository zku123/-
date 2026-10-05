"""CLI: python -m relocation_groups search --country Грузия"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
import sys

from .filters import apply_filters, merge
from .models import Group
from .queries import COUNTRIES, build_queries
from .storage import Storage


def _env(name: str) -> str | None:
    return os.environ.get(name) or None


async def collect(args, queries: list[str]) -> list[Group]:
    found: list[Group] = []
    platforms = set(args.platform)

    if "vk" in platforms:
        token = _env("VK_TOKEN")
        if not token:
            print("VK пропущен: не задан VK_TOKEN", file=sys.stderr)
        else:
            from .sources.vk import VKError, VKSource
            vk = VKSource(token, check_activity=args.check_activity)
            for q in queries:
                try:
                    found += await asyncio.to_thread(vk.search, q, args.limit)
                    print(f"[vk] {q}", file=sys.stderr)
                except VKError as e:
                    print(f"[vk] ошибка: {e}", file=sys.stderr)

    if "telegram" in platforms:
        api_id, api_hash = _env("TG_API_ID"), _env("TG_API_HASH")
        if not (api_id and api_hash):
            print("Telegram пропущен: не заданы TG_API_ID/TG_API_HASH", file=sys.stderr)
        else:
            from .sources.telegram import TelegramSource
            async with TelegramSource(int(api_id), api_hash,
                                      check_activity=True) as tg:
                for q in queries:
                    found += await tg.search(q, args.limit)
                    print(f"[tg] {q}", file=sys.stderr)
    return found


def cmd_search(args) -> None:
    queries = [args.query] if args.query else build_queries(args.country)
    groups = merge(asyncio.run(collect(args, queries)))
    groups = apply_filters(
        groups, min_members=args.min_members,
        max_inactive_days=args.max_inactive_days,
        country=args.only_country, min_relevance=args.min_relevance,
    )
    new = Storage(args.db).save(groups)
    print(f"Найдено: {len(groups)}, новых: {new}. Сохранено в {args.db}", file=sys.stderr)
    print_groups(groups[: args.top])


def cmd_show(args) -> None:
    rows = Storage(args.db).top(args.top, args.only_country)
    print_groups(rows, rows_mode=True)


def cmd_export(args) -> None:
    rows = Storage(args.db).top(10**6, args.only_country)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["platform", "title", "url", "members", "country",
                    "last_activity", "score"])
        for r in rows:
            w.writerow([r["platform"], r["title"], r["url"], r["members"],
                        r["country"], r["last_activity"], r["score"]])
    print(f"Экспортировано {len(rows)} → {args.out}")


def print_groups(items, rows_mode: bool = False) -> None:
    for it in items:
        get = (lambda k: it[k]) if rows_mode else (lambda k: getattr(it, k))
        members = get("members")
        print(f"{get('score'):>6}  {get('platform'):<8} "
              f"{(str(members) if members is not None else '?'):>8}  "
              f"{(get('country') or '-'):<11} {get('title')[:45]:<45} {get('url')}")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    p = argparse.ArgumentParser(prog="relocation_groups", description=__doc__)
    p.add_argument("--db", default="groups.db")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="найти группы и сохранить в БД")
    s.add_argument("--platform", nargs="+", choices=["telegram", "vk"],
                   default=["telegram", "vk"])
    s.add_argument("--country", nargs="+", choices=list(COUNTRIES),
                   help="страны для генерации запросов (по умолчанию все)")
    s.add_argument("--query", help="один произвольный запрос вместо генерации")
    s.add_argument("--limit", type=int, default=30, help="результатов на запрос")
    s.add_argument("--min-members", type=int, default=100)
    s.add_argument("--max-inactive-days", type=int, default=60)
    s.add_argument("--min-relevance", type=float, default=1)
    s.add_argument("--only-country", choices=list(COUNTRIES))
    s.add_argument("--check-activity", action="store_true",
                   help="VK: проверять дату последнего поста (медленнее)")
    s.add_argument("--top", type=int, default=50)
    s.set_defaults(func=cmd_search)

    sh = sub.add_parser("show", help="показать лучшие группы из БД")
    sh.add_argument("--top", type=int, default=50)
    sh.add_argument("--only-country", choices=list(COUNTRIES))
    sh.set_defaults(func=cmd_show)

    ex = sub.add_parser("export", help="выгрузить БД в CSV")
    ex.add_argument("--out", default="groups.csv")
    ex.add_argument("--only-country", choices=list(COUNTRIES))
    ex.set_defaults(func=cmd_export)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
