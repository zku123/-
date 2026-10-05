"""Поиск Telegram-групп без API: поисковик по site:t.me + публичные страницы t.me.

Ключи не нужны. Данные берутся только с открытых страниц; между запросами
выдерживаются паузы. Поисковики могут блокировать автоматические запросы —
тогда источник сообщит об этом и вернёт пустой результат.
"""
from __future__ import annotations

import html as htmllib
import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus, unquote

import requests

from ..models import Group

log = logging.getLogger(__name__)

SEARCH_URL = "https://html.duckduckgo.com/html/?q={q}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ru,en;q=0.8",
}
RESERVED = {"joinchat", "share", "s", "addstickers", "proxy", "login", "iv",
            "c", "socks", "setlanguage", "addemoji", "addtheme", "boost"}
LINK_RE = re.compile(r"t\.me/(?:s/)?([A-Za-z][A-Za-z0-9_]{4,31})(?![A-Za-z0-9_])")
META_RE = r'<meta property="og:{}" content="([^"]*)"'
EXTRA_RE = re.compile(r'class="tgme_page_extra">(.*?)</div>', re.S)
COUNT_RE = re.compile(r"([\d][\d\s ,.]*)\s*(members|subscribers|участник|подписчик)", re.I)
TIME_RE = re.compile(r'<time[^>]*datetime="([^"]+)"')


def extract_usernames(page: str) -> list[str]:
    """Имена t.me/<username> из выдачи поисковика (порядок сохраняется)."""
    found = LINK_RE.findall(unquote(htmllib.unescape(page)))
    names = [n for n in found if n.lower() not in RESERVED]
    return list(dict.fromkeys(n.lower() for n in names))


def parse_channel_page(page: str, username: str) -> Group | None:
    """Разбор публичной страницы t.me/<username>. None — не группа/канал."""
    extra = EXTRA_RE.search(page)
    m = COUNT_RE.search(
        htmllib.unescape(re.sub(r"<[^>]+>", " ", extra.group(1)))) if extra else None
    if not m:  # пользователь, бот или несуществующий адрес
        return None
    members = int(re.sub(r"\D", "", m.group(1)))

    def meta(name: str) -> str:
        found = re.search(META_RE.format(name), page)
        return htmllib.unescape(found.group(1)).strip() if found else ""

    return Group(
        platform="telegram",
        ext_id=username.lower(),
        title=meta("title"),
        url=f"https://t.me/{username}",
        description=meta("description"),
        members=members,
    )


def parse_last_post(page: str) -> datetime | None:
    """Дата последнего поста из превью t.me/s/<username>."""
    dates = TIME_RE.findall(page)
    if not dates:
        return None
    try:
        return datetime.fromisoformat(dates[-1]).astimezone(timezone.utc)
    except ValueError:
        return None


class WebTelegramSource:
    def __init__(self, check_activity: bool = True, pause: float = 2.0):
        self.check_activity = check_activity
        self.pause = pause
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._cache: dict[str, Group | None] = {}

    def _get(self, url: str) -> str | None:
        time.sleep(self.pause)
        try:
            r = self.session.get(url, timeout=30)
        except requests.RequestException as e:
            log.warning("%s: %s", url, e)
            return None
        if r.status_code != 200:
            log.warning("%s -> HTTP %s", url, r.status_code)
            return None
        return r.text

    def search(self, query: str, limit: int = 30) -> list[Group]:
        page = self._get(SEARCH_URL.format(q=quote_plus(f"site:t.me {query}")))
        if page is None:
            print("[web] поисковик не ответил (возможна блокировка), запрос пропущен",
                  flush=True)
            return []
        groups = []
        for name in extract_usernames(page)[:limit]:
            g = self._group(name)
            if g:
                groups.append(Group(**{**g.__dict__, "found_by": {query}}))
        return groups

    def _group(self, username: str) -> Group | None:
        if username in self._cache:
            return self._cache[username]
        page = self._get(f"https://t.me/{username}")
        g = parse_channel_page(page, username) if page else None
        if g and self.check_activity:
            preview = self._get(f"https://t.me/s/{username}")  # только у каналов/открытых групп
            g.last_activity = parse_last_post(preview) if preview else None
        self._cache[username] = g
        return g
