"""Поиск публичных групп и каналов Telegram через Telethon (MTProto)."""
from __future__ import annotations

import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import Channel

from ..models import Group

log = logging.getLogger(__name__)


class TelegramSource:
    def __init__(self, api_id: int, api_hash: str, session: str = "relocation",
                 check_activity: bool = True, pause: float = 1.0):
        self.client = TelegramClient(session, api_id, api_hash)
        self.check_activity = check_activity
        self.pause = pause

    async def __aenter__(self):
        await self.client.start()  # при первом запуске запросит телефон и код
        return self

    async def __aexit__(self, *exc):
        await self.client.disconnect()

    async def _safe(self, coro_factory):
        for _ in range(3):
            try:
                await asyncio.sleep(self.pause)
                return await coro_factory()
            except FloodWaitError as e:
                log.warning("FloodWait: ждём %s с", e.seconds)
                await asyncio.sleep(e.seconds + 1)
        return None

    async def search(self, query: str, limit: int = 50) -> list[Group]:
        res = await self._safe(lambda: self.client(SearchRequest(q=query, limit=limit)))
        if res is None:
            return []
        groups = []
        for chat in res.chats:
            if not isinstance(chat, Channel) or not chat.username:
                continue  # только публичные группы/каналы
            g = Group(
                platform="telegram",
                ext_id=str(chat.id),
                title=chat.title or "",
                url=f"https://t.me/{chat.username}",
                members=getattr(chat, "participants_count", None),
                found_by={query},
            )
            await self._details(chat, g)
            groups.append(g)
        return groups

    async def _details(self, chat: Channel, g: Group) -> None:
        full = await self._safe(lambda: self.client(GetFullChannelRequest(chat)))
        if full is not None:
            g.description = full.full_chat.about or ""
            g.members = full.full_chat.participants_count or g.members
        if self.check_activity:
            msgs = await self._safe(lambda: self.client.get_messages(chat, limit=1))
            if msgs:
                g.last_activity = msgs[0].date
