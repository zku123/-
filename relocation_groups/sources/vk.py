"""Поиск групп ВКонтакте через официальный API (groups.search)."""
from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

from ..models import Group

API = "https://api.vk.com/method/"
VERSION = "5.199"


class VKError(RuntimeError):
    pass


class VKSource:
    def __init__(self, token: str, check_activity: bool = False, pause: float = 0.4):
        self.token = token
        self.check_activity = check_activity
        self.pause = pause  # лимит VK ~3 запроса/сек

    def _call(self, method: str, **params) -> dict:
        params.update(access_token=self.token, v=VERSION)
        time.sleep(self.pause)
        data = requests.get(API + method, params=params, timeout=30).json()
        if "error" in data:
            raise VKError(f"{method}: {data['error'].get('error_msg')}")
        return data["response"]

    def search(self, query: str, limit: int = 50) -> list[Group]:
        found = self._call("groups.search", q=query, count=limit, sort=6)  # 6 = по числу участников
        items = found.get("items", [])
        if not items:
            return []
        ids = ",".join(str(i["id"]) for i in items)
        info = self._call(
            "groups.getById", group_ids=ids, fields="members_count,description"
        )
        info = info["groups"] if isinstance(info, dict) else info
        groups = []
        for it in info:
            g = Group(
                platform="vk",
                ext_id=str(it["id"]),
                title=it.get("name", ""),
                url=f"https://vk.com/{it.get('screen_name') or 'club' + str(it['id'])}",
                description=it.get("description", ""),
                members=it.get("members_count"),
                found_by={query},
            )
            if self.check_activity:
                g.last_activity = self._last_post(it["id"])
            groups.append(g)
        return groups

    def _last_post(self, group_id: int) -> datetime | None:
        try:
            wall = self._call("wall.get", owner_id=-group_id, count=2)
        except VKError:  # закрытая стена и т.п.
            return None
        # первый пост может быть закреплённым — берём самый свежий
        dates = [p["date"] for p in wall.get("items", [])]
        return datetime.fromtimestamp(max(dates), tz=timezone.utc) if dates else None
